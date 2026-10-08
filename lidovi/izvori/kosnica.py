"""Košnica (kosnica.net): lista biznisa je javna, ali kontakt se vidi tek kad se uloguješ.

Python ovde skuplja samo kandidate (naziv, zanimanje, mesto, link). Telefon i mejl
posle dopisuje Claude preko Chrome-a (gde si ulogovan na Košnicu).
"""

import json
import re

from bs4 import BeautifulSoup

from lidovi.common import get, slicnost, slug

BAZA = "https://kosnica.net"


def _kategorije(delatnost, grad_slug):
    """Slug-ovi kategorija za grad, najbolje poklapanje prvo."""
    direktno = f"{slug(delatnost)}-{grad_slug}"
    rezultat = [direktno]
    r = get(f"{BAZA}/gradovi/{grad_slug}")
    if r:
        for kat in sorted(set(re.findall(rf'href="/([a-z0-9-]+)-{re.escape(grad_slug)}"', r.text))):
            if slicnost(delatnost, kat) and f"{kat}-{grad_slug}" not in rezultat:
                rezultat.append(f"{kat}-{grad_slug}")
    return rezultat


def _stavke(html):
    for m in re.finditer(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            podaci = json.loads(m.group(1))
        except ValueError:
            continue
        for cvor in podaci.get("@graph", [podaci]):
            if cvor.get("@type") == "ItemList":
                for el in cvor.get("itemListElement", []):
                    yield el.get("item", {})


def lidovi(delatnost, grad, max_stranica=5):
    grad_slug = slug(grad)
    vidjeni = set()
    for kat in _kategorije(delatnost, grad_slug):
        nasao = False
        for strana in range(1, max_stranica + 1):
            r = get(f"{BAZA}/{kat}" + (f"/{strana}" if strana > 1 else ""))
            if not r:
                break
            stavke = [s for s in _stavke(r.text) if s.get("url") and s["url"] not in vidjeni]
            if not stavke:
                break
            nasao = True
            ime_kat = BeautifulSoup(r.text, "html.parser").find("h1")
            zanimanje = ime_kat.get_text(" ", strip=True) if ime_kat else kat.replace("-", " ")
            zanimanje = re.sub(rf"\s+(u\s+)?{re.escape(grad.strip())}\w*$", "", zanimanje, flags=re.I).strip()
            for s in stavke:
                vidjeni.add(s["url"])
                mesto = (s.get("address") or {}).get("addressLocality") or grad.title()
                yield {
                    "naziv": s.get("name", "").strip(),
                    "zanimanje": zanimanje,
                    "mesto": mesto,
                    "telefoni": [],
                    "mailovi": [],
                    "sajt": "",
                    "link": s["url"],
                    "izvor": "Košnica",
                    "treba_kontakt": True,
                }
        if nasao:
            print(f"  [Košnica] kategorija: {kat}")
