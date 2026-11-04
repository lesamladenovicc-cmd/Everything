"""Tanak omotač oko Instagram API-ja sa Instagram prijavom (graph.instagram.com).

Token se čita iz promenljive okruženja IG_TOKEN (dugotrajni token, važi 60 dana).
Verzija API-ja: IG_API_VER (podrazumevano v24.0).
"""

import os
import time

import requests

BAZA = "https://graph.instagram.com"


class IGGreska(Exception):
    pass


def _ver():
    return os.environ.get("IG_API_VER", "v24.0")


def _token():
    t = os.environ.get("IG_TOKEN", "").strip()
    if not t:
        raise IGGreska("Nema IG_TOKEN u okruženju. Dodaj ga u podešavanja cloud okruženja (vidi instagram/README.md).")
    return t


def zahtev(metod, putanja, **params):
    url = f"{BAZA}/{_ver()}/{putanja.lstrip('/')}"
    params["access_token"] = _token()
    for pokusaj in range(3):
        try:
            if metod == "GET":
                r = requests.get(url, params=params, timeout=60)
            else:
                r = requests.post(url, data=params, timeout=120)
        except requests.RequestException as e:
            if pokusaj == 2:
                raise IGGreska(f"Mreža: {e}")
            time.sleep(2 ** pokusaj)
            continue
        if r.status_code >= 500 and pokusaj < 2:
            time.sleep(2 ** pokusaj)
            continue
        try:
            podaci = r.json()
        except ValueError:
            raise IGGreska(f"HTTP {r.status_code}: {r.text[:300]}")
        if "error" in podaci:
            g = podaci["error"]
            raise IGGreska(f"{g.get('type', '')} {g.get('code', '')}: {g.get('message', '')}")
        return podaci
    raise IGGreska("Neuspeo zahtev")


def get(putanja, **p):
    return zahtev("GET", putanja, **p)


def post(putanja, **p):
    return zahtev("POST", putanja, **p)


def sve_stranice(putanja, max_stavki=200, **p):
    """GET sa praćenjem paging.next."""
    podaci = get(putanja, **p)
    stavke = list(podaci.get("data", []))
    sledeca = podaci.get("paging", {}).get("next")
    while sledeca and len(stavke) < max_stavki:
        r = requests.get(sledeca, timeout=60).json()
        if "error" in r:
            break
        stavke += r.get("data", [])
        sledeca = r.get("paging", {}).get("next")
    return stavke[:max_stavki]


def ja():
    return get("me", fields="user_id,username,name,followers_count,media_count")


def osvezi_token():
    """Produžava dugotrajni token za još 60 dana (token mora biti star bar 24h)."""
    r = requests.get(f"{BAZA}/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": _token()}, timeout=60)
    return r.json()


# ---------- objavljivanje ----------

def _sacekaj_kontejner(cid, max_sek=600):
    kraj = time.time() + max_sek
    while time.time() < kraj:
        s = get(cid, fields="status_code,status")
        kod = s.get("status_code")
        if kod in ("FINISHED", "PUBLISHED"):
            return
        if kod in ("ERROR", "EXPIRED"):
            raise IGGreska(f"Kontejner {cid}: {s.get('status')}")
        time.sleep(8)
    raise IGGreska(f"Kontejner {cid} nije spreman posle {max_sek}s")


def _je_video(url):
    return url.lower().split("?")[0].endswith((".mp4", ".mov"))


def napravi_kontejner(tip, mediji, caption=""):
    """tip: post | karusel | reel | story. mediji: lista javnih URL-ova."""
    if not mediji:
        raise IGGreska("Nema medija")
    if tip == "karusel":
        if not 2 <= len(mediji) <= 10:
            raise IGGreska("Karusel mora imati 2-10 medija")
        deca = []
        for u in mediji:
            p = {"is_carousel_item": "true"}
            if _je_video(u):
                p.update(media_type="VIDEO", video_url=u)
            else:
                p["image_url"] = u
            c = post("me/media", **p)["id"]
            _sacekaj_kontejner(c)
            deca.append(c)
        cid = post("me/media", media_type="CAROUSEL", children=",".join(deca), caption=caption)["id"]
    elif tip == "reel":
        cid = post("me/media", media_type="REELS", video_url=mediji[0], caption=caption, share_to_feed="true")["id"]
    elif tip == "story":
        u = mediji[0]
        p = {"media_type": "STORIES"}
        p.update({"video_url": u} if _je_video(u) else {"image_url": u})
        cid = post("me/media", **p)["id"]
    elif tip == "post":
        u = mediji[0]
        if _je_video(u):
            cid = post("me/media", media_type="REELS", video_url=u, caption=caption)["id"]
        else:
            cid = post("me/media", image_url=u, caption=caption)["id"]
    else:
        raise IGGreska(f"Nepoznat tip: {tip}")
    _sacekaj_kontejner(cid)
    return cid


def objavi(tip, mediji, caption=""):
    cid = napravi_kontejner(tip, mediji, caption)
    mid = post("me/media_publish", creation_id=cid)["id"]
    try:
        info = get(mid, fields="id,permalink,timestamp")
    except IGGreska:
        info = {"id": mid}
    return info


def poslednje_objave(n=25):
    return sve_stranice("me/media", max_stavki=n,
                        fields="id,caption,media_type,timestamp,permalink,comments_count,like_count", limit=25)


def aktivni_storiji():
    try:
        return get("me/stories", fields="id,timestamp,permalink").get("data", [])
    except IGGreska:
        return []


# ---------- komentari ----------

def komentari_objave(media_id):
    return sve_stranice(f"{media_id}/comments", max_stavki=300,
                        fields="id,text,username,timestamp,hidden,from,replies{id,text,username,timestamp}",
                        limit=50)


def odgovori_na_komentar(comment_id, tekst):
    return post(f"{comment_id}/replies", message=tekst)


def sakrij_komentar(comment_id, sakrij=True):
    return post(comment_id, hide="true" if sakrij else "false")


# ---------- poruke (DM) ----------

def razgovori(n=30):
    return sve_stranice("me/conversations", max_stavki=n, platform="instagram",
                        fields="id,updated_time,participants,messages.limit(6){id,from,to,message,created_time}")


def posalji_poruku(ig_user_id, tekst):
    import json
    return post("me/messages", recipient=json.dumps({"id": ig_user_id}), message=json.dumps({"text": tekst}))


# ---------- statistika ----------

NALOG_METRIKE = ["reach", "views", "profile_views", "accounts_engaged", "total_interactions",
                 "website_clicks", "follows_and_unfollows"]


def statistika_naloga(dana=7):
    do = int(time.time())
    od = do - dana * 86400
    rezultat = {}
    for m in NALOG_METRIKE:
        try:
            d = get("me/insights", metric=m, period="day", metric_type="total_value", since=od, until=do)
            for stavka in d.get("data", []):
                rezultat[m] = stavka.get("total_value", {}).get("value")
        except IGGreska as e:
            rezultat[m] = f"n/a ({str(e)[:60]})"
    return rezultat


def statistika_objave(media_id):
    try:
        d = get(f"{media_id}/insights", metric="reach,views,likes,comments,shares,saved,total_interactions")
        return {s["name"]: (s.get("values") or [{}])[0].get("value") for s in d.get("data", [])}
    except IGGreska as e:
        return {"greska": str(e)[:100]}
