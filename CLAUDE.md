# Lidovi

Alat koji skuplja lidove (male radnje i majstore) sa Plan Plus, 011info, Košnice, KupujemProdajem i Halo Oglasa,
proverava njihov Google profil i pravi .txt tabelu u `rezultati/`.

- Glavni tok: komanda `/lidovi delatnost: <x>, grad: <y>` (`.claude/commands/lidovi.md`).
- Python alat: `py -m lidovi <komanda>` (Windows) ili `python -m lidovi <komanda>`. Komande: sakupi, status, kontakt, dodaj, izaberi, google, zavrsi.
- Plan Plus, 011info i lista Košnice idu kroz Python (requests). Kontakti sa Košnice, KP, Halo Oglasi i Google Maps idu kroz Claude in Chrome.
- `istorija.json` pamti sve izvezene lidove da se ne ponavljaju. Ne briši ga osim ako korisnik to traži.
- `rad/trenutno.json` je stanje trenutnog pokretanja; `sakupi` ga pravi iz početka.
- Korisnik prodaje sajtove, SEO i marketing: najbolji lid je bez sajta i sa slabim ili nepostojećim Google profilom.

## Mejl kampanja: kafići i restorani

- Skill `/kafici-restorani` (`.claude/skills/kafici-restorani/SKILL.md`): nova tabela 500 ugostitelja sa mejlom, bez onih iz ranijih tabela, pa Gmail draftovi na prikazreklame@gmail.com.
- Komande: `repo`, `podesi`, `firme`, `mejlovi`, `draftovano`, `odjava` (kod u `lidovi/firme.py`).
- Podaci su u `firme/` i idu u repozitorijum SAMO ako je privatan (`py -m lidovi repo`). `firme/odjave.txt` se nikad ne briše.
- Claude pravi samo draftove; šalje ih `slanje/posalji_draftove.gs` (Google Apps Script) polako, 15-40 dnevno.
