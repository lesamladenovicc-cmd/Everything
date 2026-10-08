"""Radni fajl trenutnog pokretanja (rad/trenutno.json) i istorija svih uzetih lidova."""

import json
import os
from datetime import datetime
from pathlib import Path

from lidovi.common import slug

KOREN = Path(__file__).resolve().parent.parent
RAD = KOREN / "rad" / "trenutno.json"
ISTORIJA = KOREN / "istorija.json"
REZULTATI = KOREN / "rezultati"


def _ucitaj(putanja, podrazumevano):
    if putanja.exists():
        with open(putanja, encoding="utf-8") as f:
            return json.load(f)
    return podrazumevano


def _sacuvaj(putanja, podaci):
    putanja.parent.mkdir(parents=True, exist_ok=True)
    privremeni = putanja.with_suffix(".tmp")
    with open(privremeni, "w", encoding="utf-8") as f:
        json.dump(podaci, f, ensure_ascii=False, indent=1)
    os.replace(privremeni, putanja)


def kljucevi(lid):
    """Ključevi po kojima prepoznajemo isti biznis (telefon, mejl, naziv+grad)."""
    k = {f"t:{t}" for t in lid.get("telefoni", [])}
    k |= {f"m:{m}" for m in lid.get("mailovi", [])}
    naziv = slug(lid.get("naziv", ""))
    grad = slug((lid.get("mesto") or "").split("(")[0])
    if len(naziv) >= 6 and "-" in naziv:  # jednorečni nazivi ("Električar") su pregenerički
        k.add(f"n:{naziv}|{grad}")
    if lid.get("link"):
        k.add(f"l:{lid['link'].split('#')[0].rstrip('/')}")
    return k


class Istorija:
    def __init__(self):
        self.podaci = _ucitaj(ISTORIJA, {"kljucevi": [], "lidovi": []})
        self.skup = set(self.podaci["kljucevi"])

    def sadrzi(self, lid):
        return bool(kljucevi(lid) & self.skup)

    def dodaj(self, lidovi):
        datum = datetime.now().strftime("%Y-%m-%d")
        for lid in lidovi:
            novi = kljucevi(lid) - self.skup
            self.skup |= novi
            self.podaci["kljucevi"].extend(sorted(novi))
            self.podaci["lidovi"].append({
                "naziv": lid["naziv"], "mesto": lid["mesto"],
                "telefon": ", ".join(lid.get("telefoni", [])), "datum": datum,
            })
        _sacuvaj(ISTORIJA, self.podaci)


class Rad:
    """Lidovi jednog pokretanja."""

    def __init__(self, podaci):
        self.podaci = podaci

    @classmethod
    def novi(cls, delatnost, grad, cilj):
        return cls({
            "delatnost": delatnost, "grad": grad, "cilj": cilj,
            "pocetak": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "sledeci_id": 1, "lidovi": [],
        })

    @classmethod
    def ucitaj(cls):
        podaci = _ucitaj(RAD, None)
        if podaci is None:
            raise SystemExit("Nema započetog pokretanja. Prvo: py -m lidovi sakupi --delatnost ... --grad ...")
        return cls(podaci)

    def sacuvaj(self):
        _sacuvaj(RAD, self.podaci)

    @property
    def lidovi(self):
        return self.podaci["lidovi"]

    def nadji(self, lid_id):
        for lid in self.lidovi:
            if lid["id"] == lid_id:
                return lid
        raise SystemExit(f"Nema lida sa id {lid_id}")

    def duplikat(self, lid, osim_id=None):
        """Vraća postojeći lid koji je isti biznis, ili None."""
        k = kljucevi(lid)
        for postojeci in self.lidovi:
            if postojeci["id"] != osim_id and k & kljucevi(postojeci):
                return postojeci
        return None

    def dodaj(self, lid):
        lid["id"] = self.podaci["sledeci_id"]
        self.podaci["sledeci_id"] += 1
        lid.setdefault("izabran", False)
        self.lidovi.append(lid)
        return lid

    def kompletni(self):
        return [l for l in self.lidovi if ima_kontakt(l)]


def ima_kontakt(lid):
    return bool(lid.get("telefoni") or lid.get("mailovi"))
