"""Komande: sakupi, status, kontakt, dodaj, izaberi, google, zavrsi.

Pokretanje:  python -m lidovi <komanda> [opcije]   (na Windows-u može i: py -m lidovi ...)
"""

import argparse
import sys
from datetime import datetime

from lidovi import baza
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

    a = p.parse_args(argv)
    a.f(a)
