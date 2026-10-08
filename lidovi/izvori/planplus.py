"""Plan Plus (planplus.rs): kategorije po gradu, telefoni su javno na stranici."""

import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from lidovi.common import get, ocisti_sajt, slicnost, slug, sredi_mailove, sredi_telefone

BAZA = "https://www.planplus.rs"
# kategorije dobavljača i slično, nisu "radnje" iz tražene delatnosti
SPOREDNE = {"oprema", "distribucija", "veleprodaja", "proizvodnja", "udruzenja", "skole", "delovi"}


def nadji_kategorije(delatnost, grad_slug, max_kategorija=2):
    """Poredi delatnost sa listom kategorija grada i vraća najbliže [(slug, naziv)]."""
    r = get(f"{BAZA}/{grad_slug}/kategorije")
    if not r:
        return []
    s = BeautifulSoup(r.text, "html.parser")
    kandidati = {}
    for a in s.find_all("a", href=re.compile(rf"^/{re.escape(grad_slug)}/[a-z0-9-]+$")):
        kat = a["href"].rsplit("/", 1)[1]
        if kat in ("kategorije", "ulice"):
            continue
        poklapanje = slicnost(delatnost, kat)
        if poklapanje and not (set(kat.split("-")) & SPOREDNE - set(slug(delatnost).split("-"))):
            naziv = a.get_text(" ", strip=True) or kat.replace("-", " ")
            kandidati[kat] = max(kandidati.get(kat, (0, ""))[0], poklapanje), naziv
    najbolji = sorted(kandidati.items(), key=lambda kv: (-kv[1][0], kv[0].count("-"), len(kv[0])))
    if not najbolji:
        return []
    vrh = najbolji[0][1][0]  # samo kategorije koje se poklapaju podjednako dobro kao najbolja
    return [(kat, naziv) for kat, (poeni, naziv) in najbolji[:max_kategorija] if poeni == vrh]


def _detalji(url):
    """Sa stranice firme vadi sajt i mejl (telefon već imamo sa liste)."""
    r = get(url)
    if not r:
        return "", []
    s = BeautifulSoup(r.text, "html.parser")
    sajt = ""
    for a in s.find_all("a", onclick=re.compile("objectWebSiteClick")):
        sajt = ocisti_sajt(a.get("href"))
        if sajt:
            break
    mailovi = [a["href"] for a in s.find_all("a", href=re.compile(r"^mailto:", re.I))]
    # mejl je često samo u JSON-LD podacima, ponekad kao "malito:..."
    for m in re.findall(r'"email"\s*:\s*"([^"]+)"', r.text):
        mailovi.append(re.sub(r"^(mailto|malito):", "", m.strip(), flags=re.I))
    return sajt, sredi_mailove(mailovi)


def lidovi(delatnost, grad, max_stranica=6):
    grad_slug = slug(grad)
    kategorije = nadji_kategorije(delatnost, grad_slug)
    if not kategorije:
        print(f"  [Plan Plus] nema kategorije za '{delatnost}' u '{grad}'")
        return
    print("  [Plan Plus] kategorije: " + ", ".join(k for k, _ in kategorije))
    for kat, naziv_kat in kategorije:
        for strana in range(1, max_stranica + 1):
            url = f"{BAZA}/{grad_slug}/{kat}" + (f"/{strana}" if strana > 1 else "")
            r = get(url)
            if not r:
                break
            s = BeautifulSoup(r.text, "html.parser")
            kutije = s.select("div.box.box-item")
            if not kutije:
                break
            osnovni = []
            for b in kutije:
                if b.find(string=re.compile("privremeno zatvoren|trajno zatvoren", re.I)):
                    continue
                a = b.select_one("h2 a")
                if not a:
                    continue
                telefoni = [t["href"][4:] for t in b.find_all("a", href=re.compile(r"^tel:"))]
                adresa = b.get("data-address") or ""
                osnovni.append({
                    "naziv": b.get("data-name") or a.get_text(strip=True),
                    "zanimanje": naziv_kat if naziv_kat and naziv_kat != kat else kat.replace("-", " ").capitalize(),
                    "mesto": grad.strip().title() + (f" ({adresa})" if adresa else ""),
                    "telefoni": sredi_telefone(telefoni),
                    "link": urljoin(BAZA, a["href"]),
                    "izvor": "Plan Plus",
                })
            with ThreadPoolExecutor(max_workers=4) as ex:
                detalji = list(ex.map(lambda x: _detalji(x["link"]), osnovni))
            for lid, (sajt, mailovi) in zip(osnovni, detalji):
                lid["sajt"] = sajt
                lid["mailovi"] = mailovi
                yield lid
