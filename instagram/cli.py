"""Komande: provera, komentari, odgovori, sakrij, poruke, posalji, plan, objavi-plan, objavi, statistika, osvezi-token.

Pokretanje:  python -m instagram <komanda> [opcije]
Izlaz je JSON (da ga Claude lako čita). Token: promenljiva IG_TOKEN.
"""

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from instagram import api
from instagram.api import IGGreska

PLAN = Path(__file__).with_name("plan.json")
STORY_PROZOR = timedelta(hours=2)   # story se kači samo u ovom prozoru posle zakazanog vremena
POST_PROZOR = timedelta(hours=24)   # post koji je zakasnio više od ovoga se preskače i prijavljuje


def ispis(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _vreme(s):
    s = s.replace("Z", "+00:00")
    if re.search(r"[+-]\d{4}$", s):
        s = s[:-2] + ":" + s[-2:]
    d = datetime.fromisoformat(s)
    if d.tzinfo is None:
        raise ValueError(f"Vreme bez vremenske zone: {s} (dodaj npr. +01:00)")
    return d


def _norm(tekst):
    t = unicodedata.normalize("NFKD", tekst or "").lower()
    return re.sub(r"\W+", "", t)[:80]


def _sada():
    return datetime.now(timezone.utc)


# ---------- provera ----------

def k_provera(a):
    ispis({"nalog": api.ja(), "api_verzija": api._ver()})


def k_osvezi_token(a):
    r = api.osvezi_token()
    if "access_token" in r:
        dana = int(r.get("expires_in", 0)) // 86400
        ispis({"ok": True, "vazi_jos_dana": dana,
               "napomena": "Ako se vrednost tokena promenila, upiši novu u IG_TOKEN u podešavanjima okruženja.",
               "token_promenjen": r["access_token"] != api._token()})
    else:
        ispis({"ok": False, "odgovor": r})


# ---------- komentari ----------

def k_komentari(a):
    moj = api.ja()["username"]
    granica = _sada() - timedelta(days=a.dana)
    rezultat = []
    for m in api.poslednje_objave(a.objava):
        if _vreme(m["timestamp"]) < granica - timedelta(days=60) or not m.get("comments_count"):
            continue
        for c in api.komentari_objave(m["id"]):
            if c.get("username") == moj or c.get("hidden"):
                continue
            if _vreme(c["timestamp"]) < granica:
                continue
            odgovori = c.get("replies", {}).get("data", [])
            if any(r.get("username") == moj for r in odgovori):
                continue
            rezultat.append({
                "comment_id": c["id"], "od": c.get("username"), "tekst": c.get("text"),
                "vreme": c["timestamp"], "objava": m.get("permalink"),
                "caption_objave": (m.get("caption") or "")[:200],
                "ostali_odgovori": [{"od": r.get("username"), "tekst": r.get("text")} for r in odgovori],
            })
    ispis({"bez_odgovora": len(rezultat), "komentari": rezultat})


def k_odgovori(a):
    ispis({"ok": True, "odgovor": api.odgovori_na_komentar(a.comment_id, a.tekst)})


def k_sakrij(a):
    ispis({"ok": True, "odgovor": api.sakrij_komentar(a.comment_id, not a.otkrij)})


# ---------- poruke ----------

def k_poruke(a):
    moj_id = str(api.ja()["user_id"])
    granica = _sada() - timedelta(hours=a.sati)
    rezultat = []
    for r in api.razgovori(a.max):
        poruke = r.get("messages", {}).get("data", [])
        if not poruke:
            continue
        zadnja = poruke[0]
        if str(zadnja.get("from", {}).get("id")) == moj_id:
            continue
        if _vreme(zadnja["created_time"]) < granica:
            continue
        drugi = [p for p in r.get("participants", {}).get("data", []) if str(p.get("id")) != moj_id]
        rezultat.append({
            "korisnik_id": drugi[0]["id"] if drugi else zadnja["from"]["id"],
            "korisnik": (drugi[0].get("username") if drugi else zadnja["from"].get("username")),
            "poslednja_poruka_vreme": zadnja["created_time"],
            "istorija": [{"od": "MI" if str(p.get("from", {}).get("id")) == moj_id else p.get("from", {}).get("username"),
                          "tekst": p.get("message"), "vreme": p.get("created_time")} for p in reversed(poruke)],
        })
    ispis({"bez_odgovora": len(rezultat), "razgovori": rezultat,
           "napomena": "Odgovor je moguć samo u roku od 24h od poslednje poruke te osobe."})


def k_posalji(a):
    ispis({"ok": True, "odgovor": api.posalji_poruku(a.korisnik_id, a.tekst)})


# ---------- plan i objavljivanje ----------

def _ucitaj_plan():
    if not PLAN.exists():
        return []
    return json.loads(PLAN.read_text(encoding="utf-8")).get("objave", [])


def _proveri_stavku(s):
    greske = []
    for polje in ("id", "kada", "tip", "mediji"):
        if not s.get(polje):
            greske.append(f"fali '{polje}'")
    if s.get("tip") not in ("post", "karusel", "reel", "story"):
        greske.append("tip mora biti post|karusel|reel|story")
    if s.get("tip") != "story" and not s.get("caption"):
        greske.append("fali caption")
    for u in s.get("mediji") or []:
        if not str(u).startswith("https://"):
            greske.append(f"medij nije javni https URL: {u}")
    try:
        _vreme(s.get("kada", ""))
    except ValueError as e:
        greske.append(str(e))
    return greske


def _status_stavki(stavke):
    sada = _sada()
    objave = api.poslednje_objave(30)
    captioni = {_norm(o.get("caption")) for o in objave if o.get("caption")}
    storiji = [_vreme(s["timestamp"]) for s in api.aktivni_storiji()]
    izlaz = []
    for s in stavke:
        greske = _proveri_stavku(s)
        if greske:
            izlaz.append((s, "neispravno", "; ".join(greske)))
            continue
        kada = _vreme(s["kada"])
        if s["tip"] == "story":
            if any(kada <= t <= kada + STORY_PROZOR + timedelta(minutes=30) for t in storiji):
                status = "objavljeno"
            elif kada > sada:
                status = "zakazano"
            elif sada - kada <= STORY_PROZOR:
                status = "za_objavu"
            else:
                status = "propusteno"
        else:
            if _norm(s["caption"]) in captioni:
                status = "objavljeno"
            elif kada > sada:
                status = "zakazano"
            elif sada - kada <= POST_PROZOR:
                status = "za_objavu"
            else:
                status = "propusteno"
        izlaz.append((s, status, ""))
    return izlaz


def k_plan(a):
    stavke = _ucitaj_plan()
    if not stavke:
        ispis({"plan": [], "napomena": f"Plan je prazan ({PLAN.name})."})
        return
    ispis({"plan": [{"id": s.get("id"), "kada": s.get("kada"), "tip": s.get("tip"), "status": st,
                     **({"greska": g} if g else {})} for s, st, g in _status_stavki(stavke)]})


def k_objavi_plan(a):
    rezultat = []
    for s, status, g in _status_stavki(_ucitaj_plan()):
        if status != "za_objavu":
            if status in ("neispravno", "propusteno"):
                rezultat.append({"id": s.get("id"), "status": status, "greska": g})
            continue
        if a.suvo:
            rezultat.append({"id": s["id"], "status": "bi_bilo_objavljeno"})
            continue
        try:
            if s["tip"] == "story":
                info = [api.objavi("story", [u]) for u in s["mediji"]]
            else:
                info = api.objavi(s["tip"], s["mediji"], s["caption"])
            rezultat.append({"id": s["id"], "status": "objavljeno_sada", "info": info})
        except IGGreska as e:
            rezultat.append({"id": s["id"], "status": "greska", "greska": str(e)})
    ispis({"rezultat": rezultat})


def k_objavi(a):
    if a.tip == "story":
        ispis({"info": [api.objavi("story", [u]) for u in a.mediji]})
    else:
        ispis({"info": api.objavi(a.tip, a.mediji, a.caption or "")})


# ---------- statistika ----------

def k_statistika(a):
    objave = api.poslednje_objave(a.objava)
    ispis({
        "nalog": api.ja(),
        f"poslednjih_{a.dana}_dana": api.statistika_naloga(a.dana),
        "objave": [{"link": o.get("permalink"), "tip": o.get("media_type"), "vreme": o.get("timestamp"),
                    "lajkovi": o.get("like_count"), "komentari": o.get("comments_count"),
                    "caption": (o.get("caption") or "")[:80], **api.statistika_objave(o["id"])} for o in objave],
    })


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="python -m instagram")
    sp = p.add_subparsers(dest="komanda", required=True)

    sp.add_parser("provera").set_defaults(f=k_provera)
    sp.add_parser("osvezi-token").set_defaults(f=k_osvezi_token)

    x = sp.add_parser("komentari", help="komentari na našim objavama bez našeg odgovora")
    x.add_argument("--dana", type=int, default=7)
    x.add_argument("--objava", type=int, default=15, help="koliko poslednjih objava gledati")
    x.set_defaults(f=k_komentari)

    x = sp.add_parser("odgovori", help="odgovori na komentar")
    x.add_argument("comment_id")
    x.add_argument("tekst")
    x.set_defaults(f=k_odgovori)

    x = sp.add_parser("sakrij", help="sakrij komentar (spam/uvrede)")
    x.add_argument("comment_id")
    x.add_argument("--otkrij", action="store_true")
    x.set_defaults(f=k_sakrij)

    x = sp.add_parser("poruke", help="DM razgovori gde je poslednja poruka od druge osobe")
    x.add_argument("--sati", type=int, default=24)
    x.add_argument("--max", type=int, default=30)
    x.set_defaults(f=k_poruke)

    x = sp.add_parser("posalji", help="pošalji DM (samo u 24h prozoru)")
    x.add_argument("korisnik_id")
    x.add_argument("tekst")
    x.set_defaults(f=k_posalji)

    sp.add_parser("plan", help="status stavki iz plan.json").set_defaults(f=k_plan)

    x = sp.add_parser("objavi-plan", help="objavi sve iz plan.json čije je vreme došlo")
    x.add_argument("--suvo", action="store_true", help="samo pokaži šta bi bilo objavljeno")
    x.set_defaults(f=k_objavi_plan)

    x = sp.add_parser("objavi", help="objavi odmah")
    x.add_argument("--tip", required=True, choices=["post", "karusel", "reel", "story"])
    x.add_argument("--mediji", nargs="+", required=True, help="javni https URL-ovi")
    x.add_argument("--caption", default="")
    x.set_defaults(f=k_objavi)

    x = sp.add_parser("statistika")
    x.add_argument("--dana", type=int, default=7)
    x.add_argument("--objava", type=int, default=10)
    x.set_defaults(f=k_statistika)

    a = p.parse_args()
    try:
        a.f(a)
    except IGGreska as e:
        ispis({"greska": str(e)})
        sys.exit(1)


if __name__ == "__main__":
    main()
