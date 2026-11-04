"""Masovna tabela ugostitelja (kafići, restorani...) za mejl kampanju.

Sve što se čuva ide u folder `firme/` (u privatnom repozitorijumu):
  firme/tabele/firme_<datum>.tsv     jedna tabela po pokretanju (Excel / Google Sheets)
  firme/kampanje/kampanja_<datum>.json  mejlovi za te firme + da li je draft napravljen
  firme/odjave.txt                   mejlovi koji su rekli NE ili ne postoje (nikad im ne pišemo)
  firme/podesavanja.json             potpis, kontakt, gradovi, kategorije

Nova tabela nikad ne sadrži firmu koja postoji u nekoj ranijoj tabeli, u istoriji
`/lidovi` alata ili u odjavama.
"""

import csv
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import requests

from lidovi import baza
from lidovi.baza import kljucevi
from lidovi.common import ocisti_sajt, slug, sredi_mailove, sredi_telefone
from lidovi.izvori import info011, planplus

FOLDER = Path(os.environ.get("FIRME_FOLDER") or baza.KOREN / "firme")
TABELE = FOLDER / "tabele"
KAMPANJE = FOLDER / "kampanje"
ODJAVE = FOLDER / "odjave.txt"
PODESAVANJA = FOLDER / "podesavanja.json"

KOLONE = ["Naziv", "Delatnost", "Grad", "Adresa", "Telefon", "Mail", "Sajt", "Link", "Izvor", "Datum"]

# kategorija na Plan Plus-u -> (jednina, množina u akuzativu) za tekst mejla
TIPOVI = {
    "restorani": ("restoran", "restorane"),
    "kafici-i-barovi": ("kafić", "kafiće"),
    "picerije": ("picerija", "picerije"),
    "poslasticarnice": ("poslastičarnica", "poslastičarnice"),
    "splavovi-i-kafane": ("kafana", "kafane"),
}

PODRAZUMEVANO = {
    "posiljalac": "prikazreklame@gmail.com",
    "potpis": "",            # npr. "Aleksa Mladenović" (popunjava se pri prvom pokretanju)
    "agencija": "Prikaz",
    "kontakt": "",           # npr. "064 123 4567 · instagram.com/prikaz.rs"
    "kategorije": list(TIPOVI),
    "javni_repo_ok": False,  # True = korisnik svesno dozvolio tabele na javnom repou
    "beograd_udeo": 0.6,     # koliki deo tabele ide na Beograd, ostatak ostali gradovi
    "gradovi": [
        "Novi Sad", "Niš", "Kragujevac", "Subotica", "Zrenjanin", "Pančevo", "Čačak",
        "Kraljevo", "Novi Pazar", "Smederevo", "Leskovac", "Valjevo", "Šabac", "Užice",
        "Vranje", "Sombor", "Kruševac", "Kikinda", "Jagodina", "Zlatibor",
    ],
}

BESPLATNI_MAIL = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "icloud.com", "mail.ru",
    "eunet.rs", "open.telekom.rs", "ptt.rs", "sbb.rs", "beotel.net", "orion.rs", "yandex.com",
    "gmx.com", "gmx.net", "msn.com", "yahoo.co.uk", "hotmail.rs", "neobee.net", "mts.rs", "verat.net",
}

# 011info (samo Beograd) traži po rečima, ne po kategorijama
POJMOVI_011 = {
    "restorani": "restoran", "kafici-i-barovi": "kafić", "picerije": "picerija",
    "poslasticarnice": "poslastičarnica", "splavovi-i-kafane": "kafana",
}


# ---------- podešavanja i odjave ----------

def podesavanja():
    p = dict(PODRAZUMEVANO)
    if PODESAVANJA.exists():
        p.update(json.loads(PODESAVANJA.read_text(encoding="utf-8")))
    return p


def sacuvaj_podesavanja(p):
    FOLDER.mkdir(parents=True, exist_ok=True)
    PODESAVANJA.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def odjave():
    if not ODJAVE.exists():
        return set()
    return {l.split("#")[0].strip().lower() for l in ODJAVE.read_text(encoding="utf-8").splitlines() if l.split("#")[0].strip()}


def dodaj_odjave(mailovi, razlog):
    postojece = odjave()
    nove = [m for m in sredi_mailove(mailovi) if m not in postojece]
    if nove:
        FOLDER.mkdir(parents=True, exist_ok=True)
        with open(ODJAVE, "a", encoding="utf-8") as f:
            for m in nove:
                f.write(f"{m}  # {razlog}, {datetime.now():%Y-%m-%d}\n")
    return nove


# ---------- ranije tabele ----------

def _red_u_lid(red):
    return {
        "naziv": red.get("Naziv", ""),
        "mesto": red.get("Grad", "") or red.get("Mesto", ""),
        "telefoni": sredi_telefone(re.split(r"[,;]", red.get("Telefon", ""))),
        "mailovi": sredi_mailove(re.split(r"[,;\s]", red.get("Mail", ""))),
        "link": "" if red.get("Link", red.get("Link oglasa", "ne")) == "ne" else red.get("Link", red.get("Link oglasa", "")),
    }


def poznati_kljucevi():
    """Ključevi svih firmi iz ranijih tabela (firme/tabele, rezultati/) i istorije /lidovi."""
    k = set(baza.Istorija().skup)
    fajlovi = list(TABELE.glob("*.tsv")) + list(baza.REZULTATI.glob("*.txt"))
    for fajl in fajlovi:
        with open(fajl, encoding="utf-8-sig", newline="") as f:
            for red in csv.DictReader(f, delimiter="\t"):
                k |= kljucevi(_red_u_lid(red))
    k |= {f"m:{m}" for m in odjave()}
    return k, len(fajlovi)


# ---------- skupljanje ----------

def _grad_kljuc(lid):
    """Ključevi bez mejla (mejl se zna tek posle otvaranja stranice)."""
    return kljucevi({**lid, "mailovi": []})


def sakupi(cilj, samo_beograd=False, gradovi=None):
    p = podesavanja()
    poznato, br_tabela = poznati_kljucevi()
    print(f"Ranije tabele: {br_tabela} | poznatih ključeva (telefon/mejl/naziv): {len(poznato)}")
    nove = []
    uzeto = set()

    def preskoci(lid):
        return bool(_grad_kljuc(lid) & (poznato | uzeto))

    def ubaci(lid, kat):
        lid["telefoni"] = sredi_telefone(lid.get("telefoni", []))
        lid["mailovi"] = sredi_mailove(lid.get("mailovi", []))
        lid["sajt"] = ocisti_sajt(lid.get("sajt", ""))
        if not lid["mailovi"] or not lid.get("naziv"):
            return False
        domen = lid["mailovi"][0].split("@")[1]
        if not lid["sajt"] and domen not in BESPLATNI_MAIL:  # info@restoran.rs -> ima sajt restoran.rs
            lid["sajt"] = ocisti_sajt(domen)
        k = kljucevi(lid)
        if k & (poznato | uzeto):
            return False
        uzeto.update(k)
        lid["kategorija"] = kat
        nove.append(lid)
        return True

    def iz_kategorije(grad, kat, granica):
        pre = len(nove)
        try:
            for lid in planplus.iz_kategorije(grad, kat, TIPOVI.get(kat, (kat,))[0].capitalize(),
                                              max_stranica=40, preskoci=preskoci, radnika=6):
                ubaci(lid, kat)
                if len(nove) >= granica:
                    break
        except Exception as e:  # jedan sajt/kategorija ne sme da obori ceo rad
            print(f"  [Plan Plus] {grad}/{kat} greška: {e}")
        if info011.je_beograd(grad) and kat in POJMOVI_011 and len(nove) < granica:
            try:
                for lid in info011.lidovi(POJMOVI_011[kat], grad, max_stranica=8):
                    ubaci(lid, kat)
                    if len(nove) >= granica:
                        break
            except Exception as e:
                print(f"  [011info] {kat} greška: {e}")
        print(f"  {grad:<12} {kat:<18} +{len(nove) - pre}  (ukupno {len(nove)}/{cilj})")

    def iz_grada(grad, granica):
        """Ravnomerno po kategorijama (da ne budu sve restorani), pa dopuna bez kvote."""
        kat = p["kategorije"]
        for i, k in enumerate(kat):
            ostalo = granica - len(nove)
            if ostalo <= 0:
                return
            iz_kategorije(grad, k, len(nove) + -(-ostalo // (len(kat) - i)))
        for k in kat:
            if len(nove) >= granica:
                return
            iz_kategorije(grad, k, granica)

    beograd_granica = cilj if samo_beograd else int(cilj * p["beograd_udeo"])
    iz_grada("Beograd", beograd_granica)
    if not samo_beograd:
        for grad in gradovi or p["gradovi"]:
            if len(nove) >= cilj:
                break
            iz_grada(grad, cilj)
        if len(nove) < cilj:  # ostali gradovi nisu dali dovoljno, dopuni iz Beograda
            iz_grada("Beograd", cilj)
    return nove[:cilj]


def _grad_i_adresa(mesto):
    m = re.match(r"^(.*?)\s*\((.*)\)\s*$", mesto or "")
    return (m.group(1), m.group(2)) if m else (mesto or "", "")


def sacuvaj_tabelu(firme, datum):
    TABELE.mkdir(parents=True, exist_ok=True)
    putanja = TABELE / f"firme_{datum}.tsv"
    with open(putanja, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\r\n")
        w.writerow(KOLONE)
        for l in firme:
            grad, adresa = _grad_i_adresa(l["mesto"])
            w.writerow([
                l["naziv"], l.get("zanimanje", ""), grad, adresa or "ne",
                ", ".join(l["telefoni"]) or "ne", l["mailovi"][0], l["sajt"] or "ne",
                l.get("link") or "ne", l["izvor"], datum[:10],
            ])
    return putanja


# ---------- mejlovi ----------

def _naziv_u_tekstu(naziv):
    n = re.sub(r"\s+", " ", naziv).strip()
    return n.title() if n.isupper() and len(n) > 4 else n


def napisi_mejl(lid, p, broj):
    """Kratak, lični, iskren mejl. Bez linkova i slika (bolja isporuka), sa odjavom."""
    jed, mn = TIPOVI.get(lid.get("kategorija"), ("lokal", "lokale"))
    naziv = _naziv_u_tekstu(lid["naziv"])
    grad, _ = _grad_i_adresa(lid["mesto"])
    agencija = p["agencija"]
    if lid.get("sajt"):
        naslovi = [f"{naziv} na Google-u", f"Više gostiju za {naziv}", f"Pitanje za {naziv}"]
        sredina = (
            f"Videli smo da {naziv} već ima sajt. Mi radimo da vas ljudi koji na Google-u i Instagramu traže "
            f"„{jed} {grad}“ nađu pre konkurencije: sređen Google profil, SEO i male, ciljane reklame za vaš kraj.\n\n"
            "Ne tražimo velike budžete. Krene se od malog, pa vidite po rezervacijama i pozivima da li se isplati."
        )
    else:
        naslovi = [f"Sajt za {naziv}", f"{naziv} i Google", f"Pitanje za {naziv}"]
        sredina = (
            f"U imeniku firmi nismo našli sajt za {naziv}. Ljudi koji na Google-u traže „{jed} {grad}“ "
            "najčešće odu tamo gde odmah vide meni, slike, radno vreme i broj.\n\n"
            f"Za {mn} pravimo jednostavan sajt sa menijem, lokacijom i dugmetom za poziv ili rezervaciju, "
            "i sredimo Google profil da se pojavljujete na mapi. Cena je fiksna i dogovorena unapred."
        )
    potpis = "\n".join(x for x in [p["potpis"], agencija, p["kontakt"]] if x)
    telo = (
        "Dobar dan,\n\n"
        f"pišemo vam iz agencije {agencija}. Radimo sajtove, Google profile i reklame za kafiće i restorane u Srbiji.\n\n"
        f"{sredina}\n\n"
        "Ako vas zanima, samo odgovorite na ovaj mejl i poslaćemo par primera i cenu. Ako ne, sve u redu.\n\n"
        f"Pozdrav,\n{potpis}\n\n"
        "--\n"
        "Ako ne želite poruke od nas, odgovorite sa NE i više vam nećemo pisati."
    )
    return naslovi[broj % len(naslovi)], telo


def napravi_kampanju(firme, datum):
    p = podesavanja()
    KAMPANJE.mkdir(parents=True, exist_ok=True)
    stavke = []
    for i, l in enumerate(firme, 1):
        naslov, telo = napisi_mejl(l, p, i)
        stavke.append({"id": i, "naziv": l["naziv"], "to": l["mailovi"][0], "naslov": naslov,
                       "telo": telo, "draft": None})
    putanja = KAMPANJE / f"kampanja_{datum}.json"
    _upisi_kampanju(putanja, {"posiljalac": p["posiljalac"], "napravljeno": datum, "mejlovi": stavke})
    return putanja


def _upisi_kampanju(putanja, podaci):
    privremeni = putanja.with_suffix(".tmp")
    privremeni.write_text(json.dumps(podaci, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(privremeni, putanja)


def poslednja_kampanja():
    fajlovi = sorted(KAMPANJE.glob("kampanja_*.json"))
    if not fajlovi:
        raise SystemExit("Nema kampanje. Prvo: py -m lidovi firme --cilj 500")
    return fajlovi[-1], json.loads(fajlovi[-1].read_text(encoding="utf-8"))


# ---------- provera repozitorijuma ----------

def proveri_repo():
    """Vraća (u_redu, poruka). Javni repo = NE SME da se pušuje (lični podaci)."""
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"], cwd=baza.KOREN,
                             capture_output=True, text=True, timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False, "git nije dostupan"
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        return False, f"origin nije GitHub repozitorijum ({url or 'nema origin'})"
    vlasnik, ime = m.groups()
    try:
        r = requests.get(f"https://api.github.com/repos/{vlasnik}/{ime}", timeout=20)
    except requests.RequestException as e:
        return False, f"ne mogu da proverim GitHub ({e})"
    if r.status_code == 200 and not r.json().get("private"):
        if podesavanja().get("javni_repo_ok"):
            return True, (f"{vlasnik}/{ime} je JAVAN, ali je korisnik dozvolio push (javni_repo_ok). "
                          "Svako može da vidi i preuzme tabele.")
        return False, (f"{vlasnik}/{ime} je JAVAN. Tabele sa mejlovima ne smeju na javni repo. "
                       f"Na GitHub-u: Settings → General → Danger Zone → Change visibility → Private.")
    if r.status_code in (200, 404):  # 404 bez prijave = privatan repo
        return True, f"{vlasnik}/{ime} je privatan"
    return False, f"GitHub je vratio {r.status_code}, pokušaj ponovo"
