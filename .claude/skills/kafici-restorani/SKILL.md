---
name: kafici-restorani
description: Nova tabela 500 kafića, restorana, picerija, poslastičarnica i kafana iz Beograda i Srbije (bez firmi iz ranijih tabela u repozitorijumu), pa za svaku personalizovan mejl kao Gmail draft na prikazreklame@gmail.com; slanje ide polako preko Apps Script-a da ne ode u spam. Koristi kad korisnik kaže "kafici restorani", "500 firmi", "nova tabela firmi", "mejl kampanja", "napravi draftove".
argument-hint: "[broj firmi, podrazumevano 500] [samo Beograd]"
---

# Kafići i restorani: 500 firmi + Gmail draftovi

Cilj: **$ARGUMENTS** (ako nije rečeno: 500 firmi, Beograd + ostali gradovi Srbije).

Sve ide kroz Python alat `py -m lidovi ...` (ako `py` ne postoji: `python -m lidovi ...`).
Posle svake komande pročitaj red `SLEDEĆE:` i uradi to. Nikad ne piši tabelu ili mejlove ručno.
Podaci se čuvaju u `firme/` ovog repozitorijuma: `tabele/` (sve dosadašnje tabele), `kampanje/`, `odjave.txt`, `podesavanja.json`.

## Korak 1: najnovije tabele iz repozitorijuma + provera privatnosti

```
git pull
py -m lidovi repo
```
- Ako `repo` ispiše `STOP: ... JAVAN`: reci korisniku da repo prebaci na **Private** (poruka kaže gde) i **ne radi push** dok to ne uradi.
  Skupljanje i draftovi mogu da se urade, ali `firme/` ne sme na javni GitHub (to su lični podaci).
- Ako `git pull` ne uspe zbog lokalnih izmena, javi korisniku, ne briši ništa.

## Korak 2: podešavanja (samo prvi put)

```
py -m lidovi podesi
```
Ako je `potpis` prazan, pitaj korisnika jednim pitanjem: ime za potpis i telefon/Instagram za kontakt. Pa:
`py -m lidovi podesi --potpis "<ime>" --kontakt "<telefon · instagram>"`

## Korak 3: odjave iz Gmail-a (pre nove tabele)

Gmail alati (`mcp__Gmail__*`, učitaj ih preko ToolSearch). Nalog mora biti **prikazreklame@gmail.com**:
pogledaj pošiljaoca jednog mejla iz `search_threads` sa `in:sent`. Ako je drugi nalog, STANI i reci korisniku
da poveže Gmail konektor sa prikazreklame@gmail.com (claude.ai → Settings → Connectors).

- `search_threads` upit `label:Kampanja/poslato in:inbox newer_than:60d` → ko je odgovorio „NE", „ne hvala",
  „ne želim", „odjava", „unsubscribe" ili slično: `py -m lidovi odjava --mail "<adresa>" --razlog "rekao NE"`.
  Ko je zainteresovan: navedi ga korisniku na kraju (ime, mejl, šta je napisao). Ne odgovaraj umesto korisnika.
- `search_threads` upit `from:mailer-daemon newer_than:60d` → adresa koja ne postoji:
  `py -m lidovi odjava --mail "<adresa>" --razlog "ne postoji"`.

## Korak 4: nova tabela

```
py -m lidovi firme --cilj 500
```
- Traje 10–25 minuta (otvara Plan Plus i 011info stranice). Pusti ga da radi do kraja (Bash timeout 600000, ili u pozadini).
- Alat sam preskače svaku firmu koja postoji u nekoj ranijoj tabeli (`firme/tabele/`, `rezultati/`), u `istorija.json`
  ili u `odjave.txt`, i uzima samo firme sa **javnim mejlom**.
- Opcije: `--samo-beograd`, `--gradovi "Novi Sad, Niš"`.
- Ako ispiše `PAŽNJA: fali ...`, javi korisniku koliko je nađeno; ne izmišljaj firme ni mejlove.

## Korak 5: Gmail draftovi

Ponavljaj dok ne ispiše da su svi napravljeni:
```
py -m lidovi mejlovi --broj 25
```
Za svaki red iz JSON-a: `mcp__Gmail__create_draft` sa `to: [<to>]`, `subject: <naslov>`, `body: <telo>`
(tekst tačno kakav jeste, plain text, bez `htmlBody`, bez priloga). Posle svake grupe:
`py -m lidovi draftovano --id <id> <id> ...` (samo id-jevi za koje je draft stvarno napravljen).

- **Nikad ne šalji** mejlove (`send_message`). Skill pravi samo draftove; šalje ih Apps Script, polako.
- Ako `create_draft` vrati grešku za neku adresu, preskoči je (ne označavaj) i nastavi.
- Prvi put pokaži korisniku 1 primer mejla (`py -m lidovi mejlovi --pregled --broj 1`) pre pravljenja svih draftova.

## Korak 6: sačuvaj u repozitorijum

Samo ako je `py -m lidovi repo` rekao OK (privatan):
```
git add firme/
git commit -m "Firme: nova tabela <broj> (<datum>)"
git push
```

## Korak 7: slanje

Proveri da li korisnik ima podešenu skriptu za slanje (pitaj ako ne znaš). Ako nema: uputi ga na `slanje/UPUTSTVO.md`
(jednom nalepi `slanje/posalji_draftove.gs` u script.google.com na nalogu prikazreklame i pokrene `podesi`).
Skripta šalje pon–pet 9–17h, jedan po jedan, počinje sa 15 dnevno i raste do 40, staje kad ima previše odbijenih.

## Na kraju javi korisniku

- putanju tabele i broj firmi (po gradu, koliko bez sajta),
- koliko draftova je napravljeno i za koliko dana će otići (oko 3 nedelje za 500),
- ko je odgovorio da je zainteresovan (iz koraka 3), koliko je novih odjava,
- da li je push urađen (ili zašto nije).

## Pravila

- Samo javno objavljeni poslovni mejlovi sa Plan Plus-a i 011info-a. Ne pogađaj i ne dopisuj adrese.
- Svaki mejl ima ko piše (agencija + potpis) i rečenicu za odjavu. Ne uklanjaj je: po njoj skripta prepoznaje draftove kampanje.
- Ko je rekao NE ili ga nema, ide u `odjave.txt` i nikad mu se ne piše ponovo.
- Ne povećavaj tempo slanja preko onoga što je u `posalji_draftove.gs` bez korisnikovog izričitog zahteva, i upozori ga na rizik.
