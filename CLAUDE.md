# Lidovi

Alat koji skuplja lidove (male radnje i majstore) sa Plan Plus, 011info, Košnice, KupujemProdajem i Halo Oglasa,
proverava njihov Google profil i pravi .txt tabelu u `rezultati/`.

- Glavni tok: komanda `/lidovi delatnost: <x>, grad: <y>` (`.claude/commands/lidovi.md`).
- Python alat: `py -m lidovi <komanda>` (Windows) ili `python -m lidovi <komanda>`. Komande: sakupi, status, kontakt, dodaj, izaberi, google, zavrsi.
- Plan Plus, 011info i lista Košnice idu kroz Python (requests). Kontakti sa Košnice, KP, Halo Oglasi i Google Maps idu kroz Claude in Chrome.
- `istorija.json` pamti sve izvezene lidove da se ne ponavljaju. Ne briši ga osim ako korisnik to traži.
- `rad/trenutno.json` je stanje trenutnog pokretanja; `sakupi` ga pravi iz početka.
- Korisnik prodaje sajtove, SEO i marketing: najbolji lid je bez sajta i sa slabim ili nepostojećim Google profilom.
