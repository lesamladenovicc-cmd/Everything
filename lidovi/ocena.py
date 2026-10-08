"""Google ocena 0-100 i prioritet lida (za prodaju sajtova i SEO)."""

PROSEK = 3.5  # ka ovome "vučemo" ocene sa malo recenzija
TEZINA = 5    # koliko "zamišljenih" recenzija ima PROSEK


def google_ocena(profil, zvezdice, broj):
    """0 = nema profila; profil bez recenzija = 20; inače bajesovski prosek preslikan na 0-100.

    Primeri: 5.0★ (2) -> 73, 4.7★ (200) -> 92, 4.0★ (15) -> 72, 3.0★ (40) -> 51.
    """
    if not profil:
        return 0
    broj = int(broj or 0)
    if broj <= 0 or not zvezdice:
        return 20
    z = max(1.0, min(5.0, float(zvezdice)))
    prosek = (broj * z + TEZINA * PROSEK) / (broj + TEZINA)
    return round((prosek - 1) / 4 * 100)


def poeni_pre_google(lid):
    """Rangiranje pre Google provere: bez sajta i sa mobilnim je najbolje."""
    p = 0 if lid.get("sajt") else 50
    if any(t.startswith("06") for t in lid.get("telefoni", [])):
        p += 10
    if lid.get("mailovi"):
        p += 5
    return p


def prioritet(lid):
    """VISOK / SREDNJI / NIZAK: koliko mu trebaju sajt, Google profil i recenzije."""
    p = 0 if lid.get("sajt") else 50
    g = lid.get("google") or {}
    if g:
        if not g.get("profil"):
            p += 30
        else:
            if g.get("ocena", 0) < 60:
                p += 15
            if int(g.get("broj") or 0) < 10:
                p += 10
    if p >= 50:
        return "VISOK", p
    if p >= 25:
        return "SREDNJI", p
    return "NIZAK", p
