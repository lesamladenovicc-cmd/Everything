"""011info (011info.com): samo Beograd. Pretraga + stranica firme (telefon, mejl, sajt)."""

import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from lidovi.common import get, ocisti_sajt, slicnost, slug, sredi_mailove, sredi_telefone

BAZA = "https://www.011info.com"
LINK_FIRME = re.compile(r"^https://www\.011info\.com/([a-z0-9-]+)/([a-z0-9-]+)$")
PRESKOCI_SEKCIJE = {
    "baza-biznis-znanja", "pretraga", "download", "uploads", "vesti", "interakcije",
    "dogadjaji", "kamere", "fotografije-beograda", "beogradske-opstine",
}


def je_beograd(grad):
    return slug(grad) in ("beograd", "belgrade", "bg")


def _detalji(url):
    r = get(url)
    if not r:
        return None
    s = BeautifulSoup(r.text, "html.parser")
    h1 = s.find("h1")
    naziv = h1.get_text(" ", strip=True) if h1 else ""
    adresa, telefoni, mailovi, sajt = "", [], [], ""
    labela = s.find("strong", string=re.compile(r"Telefon|Adresa|E-mail"))
    ul = labela.find_parent("ul") if labela else None
    if ul:
        for li in ul.find_all("li"):
            tekst = li.get_text(" ", strip=True)
            if tekst.startswith("Adresa"):
                adresa = tekst.split(":", 1)[-1].strip()
            for a in li.find_all("a", href=True):
                h = a["href"]
                if h.startswith("tel:"):
                    telefoni.append(h[4:])
                elif h.lower().startswith("mailto:"):
                    mailovi.append(h)
                elif not sajt:
                    sajt = ocisti_sajt(h)
            if tekst.startswith("Telefon"):
                telefoni += re.findall(r"0\d[\d/ -]{5,}\d", tekst)
    return naziv, adresa, sredi_telefone(telefoni), sredi_mailove(mailovi), sajt


def _zanimanje(sekcija, delatnost):
    """Kategorija sa 011info ako liči na traženu delatnost, inače sama delatnost."""
    naziv = sekcija.replace("-", " ")
    if slicnost(delatnost, naziv):
        return naziv.capitalize()
    return delatnost.strip().capitalize()


def lidovi(delatnost, grad, max_stranica=5):
    if not je_beograd(grad):
        print("  [011info] preskačem (samo Beograd)")
        return
    vidjeni = set()
    for strana in range(1, max_stranica + 1):
        r = get(f"{BAZA}/pretraga/{strana}?text={quote_plus(delatnost)}")
        if not r:
            break
        linkovi = []
        for m in re.finditer(r'href="(https://www\.011info\.com/[a-z0-9-]+/[a-z0-9-]+)"', r.text):
            url = m.group(1)
            sekcija = LINK_FIRME.match(url).group(1)
            if url not in vidjeni and sekcija not in PRESKOCI_SEKCIJE and not url.endswith("/blizu-mene"):
                vidjeni.add(url)
                linkovi.append(url)
        if not linkovi:
            break
        with ThreadPoolExecutor(max_workers=4) as ex:
            detalji = list(ex.map(_detalji, linkovi))
        for url, d in zip(linkovi, detalji):
            if not d or not d[0]:
                continue
            naziv, adresa, telefoni, mailovi, sajt = d
            yield {
                "naziv": naziv.title() if naziv.isupper() else naziv,
                "zanimanje": _zanimanje(LINK_FIRME.match(url).group(1), delatnost),
                "mesto": "Beograd" + (f" ({adresa})" if adresa else ""),
                "telefoni": telefoni,
                "mailovi": mailovi,
                "sajt": sajt,
                "link": url,
                "izvor": "011info",
            }
