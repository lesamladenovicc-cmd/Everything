"""Zajedničke pomoćne funkcije: HTTP, normalizacija teksta, telefona i mejlova."""

import re
import time
import unicodedata
from urllib.parse import urlparse

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"
)

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "sr-RS,sr;q=0.9,en;q=0.5"})

# Domeni koji nisu "sajt firme" (društvene mreže, oglasnici, imenici).
NIJE_SAJT = (
    "facebook.", "instagram.", "tiktok.", "youtube.", "linkedin.", "twitter.", "x.com",
    "wa.me", "whatsapp.", "viber.", "google.", "goo.gl", "apple.com",
    "planplus.rs", "011info.com", "kosnica.net", "kupujemprodajem.com", "halooglasi.com",
    "fontawesome.com", "w3.org", "schema.org",
)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LOSI_MAILOVI = ("example.", "sentry.", "wixpress.", "@2x.", ".png", ".jpg", ".svg", ".webp")
LOSI_MAIL_DOMENI = ("planplus.rs", "011info.com", "kosnica.net", "gradoid.com")


def get(url, timeout=25, pokusaja=3):
    """GET sa par ponovnih pokušaja. Vraća Response ili None."""
    for i in range(pokusaja):
        try:
            r = _session.get(url, timeout=timeout)
            if r.status_code == 404:
                return None
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def slug(tekst):
    """'Novi Sad' -> 'novi-sad', 'Frizerski salon Đurđa' -> 'frizerski-salon-djurdja'."""
    t = (tekst or "").strip().lower()
    t = t.replace("đ", "dj").replace("Đ", "dj")
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t.strip("-")


def koreni(tekst, duzina=5):
    """Skraćeni koreni reči za grubo poređenje ('frizeri' i 'frizerski' -> 'frize')."""
    return {w[:duzina] for w in slug(tekst).split("-") if len(w) >= 3}


def slicnost(delatnost, tekst):
    """Koliko reči delatnosti se poklapa sa tekstom (kategorijom).

    Reč se poklapa ako im je zajednički početak bar 5 slova i bar 70% tražene reči:
    'elektricar' ~ 'elektricari' (da), 'elektricar' ~ 'elektronske' (ne), 'frizer' ~ 'frizerski' (da).
    """
    reci_t = [w for w in slug(tekst).split("-") if len(w) >= 3]
    pogodaka = 0
    for w in slug(delatnost).split("-"):
        if len(w) < 3:
            continue
        for t in reci_t:
            zajednicko = 0
            for x, y in zip(w, t):
                if x != y:
                    break
                zajednicko += 1
            if zajednicko >= min(5, len(w)) and zajednicko >= 0.7 * len(w):
                pogodaka += 1
                break
    return pogodaka


def normalizuj_telefon(t):
    """Vraća broj u obliku 0641234567 ili None ako ne liči na srpski broj."""
    cifre = re.sub(r"\D", "", t or "")
    if cifre.startswith("00381"):
        cifre = "0" + cifre[5:]
    elif cifre.startswith("381"):
        cifre = "0" + cifre[3:]
    elif not cifre.startswith("0") and len(cifre) in (8, 9):
        cifre = "0" + cifre
    if not cifre.startswith("0") or not 8 <= len(cifre) <= 11:
        return None
    if re.fullmatch(r"0(\d)\1{6,}", cifre):  # 0000000 i slično
        return None
    return cifre


def je_mobilni(tel):
    return tel.startswith("06")


def sredi_telefone(lista):
    """Normalizuje, izbacuje duplikate, mobilne stavlja prve."""
    vidjeni = []
    for t in lista:
        n = normalizuj_telefon(t)
        if n and n not in vidjeni:
            vidjeni.append(n)
    return sorted(vidjeni, key=lambda x: not je_mobilni(x))


def sredi_mailove(lista):
    vidjeni = []
    for m in lista:
        m = (m or "").strip().strip(".,;").lower()
        if m.startswith("mailto:"):
            m = m[7:].split("?")[0]
        if not EMAIL_RE.fullmatch(m):
            continue
        if any(x in m for x in LOSI_MAILOVI) or m.split("@")[1] in LOSI_MAIL_DOMENI:
            continue
        if m not in vidjeni:
            vidjeni.append(m)
    return vidjeni


def je_pravi_sajt(url):
    if not url or not url.lower().startswith(("http://", "https://")):
        return False
    host = urlparse(url).netloc.lower()
    return bool(host) and not any(x in host for x in NIJE_SAJT)


def ocisti_sajt(url):
    url = (url or "").strip()
    if url and not url.lower().startswith(("http://", "https://")) and "." in url:
        url = "https://" + url
    return url.rstrip("/") if je_pravi_sajt(url) else ""
