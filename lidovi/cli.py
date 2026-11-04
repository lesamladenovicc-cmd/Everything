"""Komande: sakupi, status, kontakt, dodaj, izaberi, google, zavrsi
(+ mejl kampanja: repo, podesi, firme, mejlovi, draftovano, odjava).

Pokretanje:  python -m lidovi <komanda> [opcije]   (na Windows-u može i: py -m lidovi ...)
"""

import argparse
import json
import sys
from datetime import datetime

from lidovi import baza, firme
from lidovi.baza import Istorija, Rad, ima_kontakt
from lidovi.common import ocisti_sajt, slug, sredi_mailove, sredi_telefone
from lidovi.izvori import info011, kosnica, planplus
from lidovi.ocena import google_ocena, poeni_pre_google, prioritet

KOLONE = [
    "Naziv", "Zanimanje", "Mesto", "Telefon", "Mail", "Sajt", "Link oglasa",
    "Google profil", "Google ocena (0-100)", "Google recenzije", "Prioritet",
]

IZVORI_BRZI = [("Plan Plus", planplus.lidovi), ("011info", info011.lidovi)]


def _kratko(lid):
    kontakt = ", ".join(lid.get("telefoni", []) + lid.get("mailovi", [])) or "NEMA KONTAKT"
    sajt = "sajt: da" if lid.get("sajt") else "sajt: ne"
    g = lid.get("google")
    google = "google: ?" if not g else (f"google: {g['ocena']}" if g.get("profil") else "google: ne")
    znak = "*" if lid.get("izabran") else " "
    return f"{znak}[{lid['id']:>3}] {lid['naziv'][:40]:<40} | {lid['izvor']:<10} | {kontakt[:45]:<45} | {sajt} | {google}"


def _ubaci(rad, istorija, lid):
    """Dodaje lid ako nije duplikat i nije već uzet ranije. Vraća (lid, razlog)."""
    lid["telefoni"] = sredi_telefone(lid.get("telefoni", []))
    lid["mailovi"] = sredi_mailove(lid.get("mailovi", []))
    lid["sajt"] = ocisti_sajt(lid.get("sajt", ""))
    if not lid.get("naziv"):
        return None, "nema naziv"
    if istorija.sadrzi(lid):
        return None, "već uzet u ranijem pokretanju"
    postojeci = rad.duplikat(lid)
    if postojeci:
        # spoji podatke u postojeći lid (npr. isti biznis na dva sajta)
        for polje in ("telefoni", "mailovi"):
            postojeci[polje] = list(dict.fromkeys(postojeci.get(polje, []) + lid[polje]))
        if not postojeci.get("sajt") and lid["sajt"]:
            postojeci["sajt"] = lid["sajt"]
        if ima_kontakt(postojeci):
            postojeci.pop("treba_kontakt", None)
        return None, f"duplikat lida {postojeci['id']} (podaci spojeni)"
    return rad.dodaj(lid), "ok"


def cmd_sakupi(a):
    rad = Rad.novi(a.delatnost, a.grad, a.cilj)
    istorija = Istorija()
    bazen = int(a.cilj * 1.6)  # skupi više pa izaberi najbolje (bez sajta prvo)
    print(f"Tražim '{a.delatnost}' u '{a.grad}', cilj {a.cilj} lidova (skupljam do {bazen} za izbor)...")

    pojmovi = [a.delatnost] + _lista(a.sinonimi)
    if len(pojmovi) > 1:
        print("Pojmovi: " + ", ".join(pojmovi))

    # u Beogradu delimo bazen između Plan Plus-a i 011info-a (011info češće ima mejl)
    po_izvoru = int(bazen * 0.6) if info011.je_beograd(a.grad) else bazen
    for ime, izvor in IZVORI_BRZI:
        pre = len(rad.kompletni())
        granica = min(bazen, pre + po_izvoru)
        for pojam in pojmovi:
            if len(rad.kompletni()) >= granica:
                break
            try:
                for lid in izvor(pojam, a.grad):
                    if ima_kontakt(lid):
                        _ubaci(rad, istorija, lid)
                    if len(rad.kompletni()) >= granica:
                        break
            except Exception as e:  # jedan sajt ne sme da obori ceo rad
                print(f"  [{ime}] greška: {e}")
        print(f"  [{ime}] +{len(rad.kompletni()) - pre} lidova sa kontaktom")
        rad.sacuvaj()

    fali = a.cilj - len(rad.kompletni())
    if fali > 0:
        dodato = 0
        for pojam in pojmovi:
            if dodato >= fali + 10:
                break
            try:
                for lid in kosnica.lidovi(pojam, a.grad):
                    novi, _ = _ubaci(rad, istorija, lid)
                    if novi:
                        dodato += 1
                    if dodato >= fali + 10:
                        break
            except Exception as e:
                print(f"  [Košnica] greška: {e}")
        print(f"  [Košnica] {dodato} kandidata (kontakt se uzima preko Chrome-a)")
    rad.sacuvaj()
    cmd_status(a)


def cmd_status(a):
    rad = Rad.ucitaj()
    komp = rad.kompletni()
    ceka = [l for l in rad.lidovi if l.get("treba_kontakt") and not ima_kontakt(l)]
    izabrani = [l for l in rad.lidovi if l.get("izabran")]
    bez_google = [l for l in izabrani if not l.get("google")]
    print()
    print(f"Delatnost: {rad.podaci['delatnost']} | Grad: {rad.podaci['grad']} | Cilj: {rad.podaci['cilj']}")
    print(f"Sa kontaktom: {len(komp)} | Košnica čeka kontakt: {len(ceka)} | Izabrano: {len(izabrani)} | Izabrano bez Google provere: {len(bez_google)}")
    if getattr(a, "sve", False):
        for lid in rad.lidovi:
            print(_kratko(lid))
    fali = rad.podaci["cilj"] - len(komp)
    print()
    if fali > 0:
        print(f"SLEDEĆE: fali još {fali} lidova sa kontaktom.")
        if ceka:
            print("  1) Uzmi kontakte sa Košnice preko Chrome-a za ove id-jeve:")
            for lid in ceka[: fali + 5]:
                print(f"     id {lid['id']}: {lid['naziv']} -> {lid['link']}")
        print("  2) Ako i dalje fali: KupujemProdajem, pa Halo Oglasi (komanda 'dodaj').")
    elif len(izabrani) < min(rad.podaci["cilj"], len(komp)):
        print("SLEDEĆE: py -m lidovi izaberi")
    elif bez_google:
        print("SLEDEĆE: Google provera za ove id-jeve (komanda 'google'):")
        for lid in bez_google:
            print(f"     id {lid['id']}: {lid['naziv']} | {lid['mesto']}")
    else:
        print("SLEDEĆE: py -m lidovi zavrsi")


def cmd_kontakt(a):
    rad = Rad.ucitaj()
    lid = rad.nadji(a.id)
    if a.nema:
        lid["treba_kontakt"] = False
        lid["nema_kontakt"] = True
        rad.sacuvaj()
        print(f"id {a.id}: označeno da nema kontakt (preskače se)")
        return
    lid["telefoni"] = sredi_telefone(lid.get("telefoni", []) + _lista(a.telefon))
    lid["mailovi"] = sredi_mailove(lid.get("mailovi", []) + _lista(a.mail))
    if a.sajt:
        lid["sajt"] = ocisti_sajt(a.sajt)
    if not ima_kontakt(lid):
        print(f"id {a.id}: telefon/mejl nisu ispravni, ništa nije sačuvano")
        return
    lid.pop("treba_kontakt", None)
    dup = rad.duplikat(lid, osim_id=lid["id"])
    if dup:
        rad.lidovi.remove(lid)
        print(f"id {a.id}: isti biznis kao id {dup['id']}, uklonjen")
    elif Istorija().sadrzi(lid):
        rad.lidovi.remove(lid)
        print(f"id {a.id}: već uzet u ranijem pokretanju, uklonjen")
    else:
        print(f"id {a.id}: sačuvano -> {', '.join(lid['telefoni'] + lid['mailovi'])}")
    rad.sacuvaj()
    print(f"Sa kontaktom: {len(rad.kompletni())}/{rad.podaci['cilj']}")


def _lista(vrednosti):
    izlaz = []
    for v in vrednosti or []:
        izlaz += [x.strip() for x in v.split(",") if x.strip()]
    return izlaz


def cmd_dodaj(a):
    rad = Rad.ucitaj()
    lid = {
        "naziv": a.naziv.strip(),
        "zanimanje": (a.zanimanje or rad.podaci["delatnost"]).strip().capitalize(),
        "mesto": a.mesto or rad.podaci["grad"],
        "telefoni": _lista(a.telefon),
        "mailovi": _lista(a.mail),
        "sajt": a.sajt or "",
        "link": a.link or "",
        "izvor": a.izvor,
    }
    novi, razlog = _ubaci(rad, Istorija(), lid)
    if novi and not ima_kontakt(novi):
        rad.lidovi.remove(novi)
        novi, razlog = None, "nema ni telefon ni mejl (preskočeno)"
    rad.sacuvaj()
    print(f"{'DODAT id ' + str(novi['id']) if novi else 'NIJE DODAT'}: {razlog}")
    print(f"Sa kontaktom: {len(rad.kompletni())}/{rad.podaci['cilj']}")


def cmd_izaberi(a):
    rad = Rad.ucitaj()
    komp = sorted(rad.kompletni(), key=lambda l: (-poeni_pre_google(l), l["id"]))
    cilj = rad.podaci["cilj"]
    for lid in rad.lidovi:
        lid["izabran"] = False
    for lid in komp[:cilj]:
        lid["izabran"] = True
    rad.sacuvaj()
    bez_sajta = sum(1 for l in komp[:cilj] if not l.get("sajt"))
    print(f"Izabrano {min(cilj, len(komp))} od {len(komp)} (bez sajta: {bez_sajta}).")
    cmd_status(a)


def cmd_google(a):
    rad = Rad.ucitaj()
    lid = rad.nadji(a.id)
    profil = a.profil == "da"
    lid["google"] = {
        "profil": profil,
        "zvezdice": a.zvezdice if profil else None,
        "broj": a.broj if profil else 0,
        "link": a.link or "",
        "ocena": google_ocena(profil, a.zvezdice, a.broj),
    }
    if profil and a.sajt and not lid.get("sajt"):
        lid["sajt"] = ocisti_sajt(a.sajt)
    rad.sacuvaj()
    ostalo = sum(1 for l in rad.lidovi if l.get("izabran") and not l.get("google"))
    print(f"id {a.id}: Google ocena {lid['google']['ocena']}/100. Ostalo za proveru: {ostalo}")


def _red(lid):
    g = lid.get("google")
    sajt = lid.get("sajt")
    if g is None:
        profil, ocena, recenzije = "nije provereno", "nije provereno", "nije provereno"
    elif g["profil"]:
        profil, ocena = "da", str(g["ocena"])
        recenzije = f"{g['zvezdice']}★ ({g['broj']})" if g.get("broj") else "nema recenzija"
    else:
        profil, ocena, recenzije = "ne", "0", "ne"
    nivo, _ = prioritet(lid)
    vrednosti = [
        lid["naziv"], lid.get("zanimanje") or "ne", lid.get("mesto") or "ne",
        ", ".join(lid.get("telefoni", [])) or "ne",
        ", ".join(lid.get("mailovi", [])) or "ne",
        f"da: {sajt}" if sajt else "ne",
        lid.get("link") or "ne", profil, ocena, recenzije, nivo,
    ]
    return [str(v).replace("\t", " ").replace("\n", " ").strip() for v in vrednosti]


def cmd_zavrsi(a):
    rad = Rad.ucitaj()
    izabrani = [l for l in rad.lidovi if l.get("izabran") and ima_kontakt(l)]
    if not izabrani:
        raise SystemExit("Nema izabranih lidova. Pokreni prvo: py -m lidovi izaberi")
    bez_google = [l for l in izabrani if not l.get("google")]
    if bez_google and not a.bez_google:
        raise SystemExit(f"{len(bez_google)} lidova nema Google proveru. Završi proveru ili dodaj --bez-google.")
    izabrani.sort(key=lambda l: -prioritet(l)[1])
    baza.REZULTATI.mkdir(exist_ok=True)
    ime = f"lidovi_{slug(rad.podaci['delatnost'])}_{slug(rad.podaci['grad'])}_{datetime.now():%Y-%m-%d_%H%M}.txt"
    putanja = baza.REZULTATI / ime
    with open(putanja, "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write("\t".join(KOLONE) + "\n")
        for lid in izabrani:
            f.write("\t".join(_red(lid)) + "\n")
    Istorija().dodaj(izabrani)
    visok = sum(1 for l in izabrani if prioritet(l)[0] == "VISOK")
    print(f"GOTOVO: {len(izabrani)} lidova ({visok} visok prioritet) -> {putanja}")
    print("Istorija ažurirana: ovi lidovi se neće ponoviti u sledećim pokretanjima.")


# ---------- mejl kampanja (kafići, restorani...) ----------

def cmd_repo(a):
    ok, poruka = firme.proveri_repo()
    print(("OK: " if ok else "STOP: ") + poruka)
    if not ok:
        raise SystemExit(1)


def cmd_podesi(a):
    p = firme.podesavanja()
    for polje in ("potpis", "kontakt", "agencija", "posiljalac"):
        if getattr(a, polje) is not None:
            p[polje] = getattr(a, polje).strip()
    firme.sacuvaj_podesavanja(p)
    for polje in ("posiljalac", "agencija", "potpis", "kontakt"):
        print(f"{polje:<11} {p[polje] or '(prazno)'}")
    if not p["potpis"]:
        print("SLEDEĆE: pitaj korisnika kojim imenom se potpisuje, pa: py -m lidovi podesi --potpis \"<ime>\" [--kontakt \"<telefon>\"]")


def cmd_firme(a):
    p = firme.podesavanja()
    if not p["potpis"]:
        raise SystemExit("Nema potpisa za mejlove. Prvo: py -m lidovi podesi --potpis \"<ime>\" [--kontakt \"<telefon>\"]")
    datum = f"{datetime.now():%Y-%m-%d_%H%M}"
    nove = firme.sakupi(a.cilj, samo_beograd=a.samo_beograd, gradovi=_lista(a.gradovi) or None)
    if not nove:
        raise SystemExit("Nije nađena nijedna nova firma sa mejlom.")
    tabela = firme.sacuvaj_tabelu(nove, datum)
    kampanja = firme.napravi_kampanju(nove, datum)
    po_gradu = {}
    for l in nove:
        g = firme._grad_i_adresa(l["mesto"])[0]
        po_gradu[g] = po_gradu.get(g, 0) + 1
    bez_sajta = sum(1 for l in nove if not l["sajt"])
    print()
    print(f"GOTOVO: {len(nove)} novih firmi sa mejlom (bez sajta: {bez_sajta}) -> {tabela}")
    print("Po gradu: " + ", ".join(f"{g} {n}" for g, n in sorted(po_gradu.items(), key=lambda x: -x[1])))
    print(f"Mejlovi spremni: {kampanja}")
    if len(nove) < a.cilj:
        print(f"PAŽNJA: fali {a.cilj - len(nove)} do cilja (nema više novih firmi sa javnim mejlom u ovim gradovima).")
    print("SLEDEĆE: py -m lidovi mejlovi --broj 25  (pa napravi Gmail draftove)")


def cmd_mejlovi(a):
    putanja, k = firme.poslednja_kampanja()
    ostalo = [m for m in k["mejlovi"] if not m.get("draft")]
    gotovo = len(k["mejlovi"]) - len(ostalo)
    print(f"Kampanja {putanja.name}: draftova {gotovo}/{len(k['mejlovi'])} | pošiljalac {k['posiljalac']}")
    if a.pregled:
        for m in ostalo[: a.broj]:
            print(f"--- id {m['id']} -> {m['to']}\nNaslov: {m['naslov']}\n{m['telo']}\n")
        return
    if not ostalo:
        print("SLEDEĆE: svi draftovi su napravljeni. Commit + push firme/, pa proveri da li Apps Script šalje.")
        return
    odj = firme.odjave()
    for m in ostalo:
        if m["to"] in odj:
            m["draft"] = "preskocen-odjava"
    firme._upisi_kampanju(putanja, k)
    sledeci = [m for m in ostalo if not m.get("draft")][: a.broj]
    print("SLEDEĆE: za svaki red napravi Gmail draft (to, subject=naslov, body=telo), pa: py -m lidovi draftovano --id <id> <id> ...")
    print(json.dumps([{"id": m["id"], "to": m["to"], "naslov": m["naslov"], "telo": m["telo"]} for m in sledeci],
                     ensure_ascii=False, indent=1))


def cmd_draftovano(a):
    putanja, k = firme.poslednja_kampanja()
    ids = {int(x) for v in a.id for x in v.replace(",", " ").split()}
    for m in k["mejlovi"]:
        if m["id"] in ids:
            m["draft"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    firme._upisi_kampanju(putanja, k)
    gotovo = sum(1 for m in k["mejlovi"] if m.get("draft"))
    print(f"Označeno {len(ids)}. Draftova: {gotovo}/{len(k['mejlovi'])}")
    print("SLEDEĆE: " + ("py -m lidovi mejlovi --broj 25" if gotovo < len(k["mejlovi"]) else "commit + push firme/"))


def cmd_odjava(a):
    nove = firme.dodaj_odjave(_lista(a.mail), a.razlog)
    print(f"Dodato u odjave: {len(nove)} ({', '.join(nove) or 'već su bili tu'})")


def main(argv=None):
    for tok in (sys.stdout, sys.stderr):
        try:
            tok.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    p = argparse.ArgumentParser(prog="lidovi", description="Skupljanje lidova (Plan Plus, 011info, Košnica, KP, Halo Oglasi)")
    sub = p.add_subparsers(dest="komanda", required=True)

    s = sub.add_parser("sakupi", help="novo pokretanje: skupi lidove sa brzih sajtova")
    s.add_argument("--delatnost", required=True)
    s.add_argument("--grad", required=True)
    s.add_argument("--cilj", type=int, default=50)
    s.add_argument("--sinonimi", action="append", help='dodatni pojmovi, npr. --sinonimi "stomatolog, zubna ordinacija"')
    s.set_defaults(f=cmd_sakupi)

    s = sub.add_parser("status", help="stanje i sledeći korak")
    s.add_argument("--sve", action="store_true", help="prikaži sve lidove")
    s.set_defaults(f=cmd_status)

    s = sub.add_parser("kontakt", help="dopiši kontakt Košnica lidu")
    s.add_argument("--id", type=int, required=True)
    s.add_argument("--telefon", action="append")
    s.add_argument("--mail", action="append")
    s.add_argument("--sajt")
    s.add_argument("--nema", action="store_true", help="nema kontakta, preskoči")
    s.set_defaults(f=cmd_kontakt)

    s = sub.add_parser("dodaj", help="dodaj lid nađen preko Chrome-a (KP, Halo...)")
    s.add_argument("--naziv", required=True)
    s.add_argument("--zanimanje")
    s.add_argument("--mesto")
    s.add_argument("--telefon", action="append")
    s.add_argument("--mail", action="append")
    s.add_argument("--sajt")
    s.add_argument("--link")
    s.add_argument("--izvor", required=True, help="npr. KupujemProdajem, Halo Oglasi")
    s.set_defaults(f=cmd_dodaj)

    s = sub.add_parser("izaberi", help="izaberi najboljih N (bez sajta prvo)")
    s.set_defaults(f=cmd_izaberi)

    s = sub.add_parser("google", help="upiši rezultat Google provere")
    s.add_argument("--id", type=int, required=True)
    s.add_argument("--profil", choices=["da", "ne"], required=True)
    s.add_argument("--zvezdice", type=float, default=0)
    s.add_argument("--broj", type=int, default=0)
    s.add_argument("--link")
    s.add_argument("--sajt", help="sajt viđen na Google profilu")
    s.set_defaults(f=cmd_google)

    s = sub.add_parser("zavrsi", help="napravi .txt u rezultati/ i upiši u istoriju")
    s.add_argument("--bez-google", action="store_true")
    s.set_defaults(f=cmd_zavrsi)

    s = sub.add_parser("repo", help="proveri da je GitHub repo privatan (pre push-a tabela)")
    s.set_defaults(f=cmd_repo)

    s = sub.add_parser("podesi", help="potpis i kontakt za mejlove")
    s.add_argument("--potpis")
    s.add_argument("--kontakt")
    s.add_argument("--agencija")
    s.add_argument("--posiljalac")
    s.set_defaults(f=cmd_podesi)

    s = sub.add_parser("firme", help="nova tabela kafića/restorana sa mejlom (bez ranijih) + tekst mejlova")
    s.add_argument("--cilj", type=int, default=500)
    s.add_argument("--samo-beograd", action="store_true")
    s.add_argument("--gradovi", action="append", help='npr. --gradovi "Novi Sad, Niš"')
    s.set_defaults(f=cmd_firme)

    s = sub.add_parser("mejlovi", help="sledeći mejlovi za koje treba napraviti draft")
    s.add_argument("--broj", type=int, default=25)
    s.add_argument("--pregled", action="store_true", help="samo prikaži tekst")
    s.set_defaults(f=cmd_mejlovi)

    s = sub.add_parser("draftovano", help="označi da je draft napravljen")
    s.add_argument("--id", nargs="+", action="extend", required=True, help="npr. --id 1 2 3 ili --id 1,2,3")
    s.set_defaults(f=cmd_draftovano)

    s = sub.add_parser("odjava", help="mejl koji ne želi poruke ili ne postoji")
    s.add_argument("--mail", action="append", required=True)
    s.add_argument("--razlog", default="rekao NE")
    s.set_defaults(f=cmd_odjava)

    a = p.parse_args(argv)
    a.f(a)
