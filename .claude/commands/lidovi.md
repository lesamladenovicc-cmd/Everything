---
description: Skupi 50 lidova (Plan Plus, 011info, Košnica, KupujemProdajem, Halo Oglasi) + Google provera, izlaz .txt
argument-hint: delatnost: <npr. frizer>, grad: <npr. Novi Sad>
---

Zadatak: skupi lidove za **$ARGUMENTS** i napravi .txt fajl u `rezultati/`.
Ako delatnost ili grad nisu jasni iz argumenata, pitaj korisnika jednim kratkim pitanjem.

Sav rad sa podacima ide kroz Python alat `py -m lidovi ...` (ako `py` ne postoji, koristi `python -m lidovi ...`).
Nikad ne piši rezultate ručno u fajl; alat sam proverava telefone, mejlove, duplikate i istoriju.
Posle svake komande pročitaj red `SLEDEĆE:` iz izlaza i uradi to.

## Korak 1: brzi sajtovi (bez browsera)

```
py -m lidovi sakupi --delatnost "<delatnost>" --grad "<grad>" [--sinonimi "<sinonim1>, <sinonim2>"]
```

- Dodaj 1-2 sinonima ako ih delatnost ima (zubar -> stomatolog; auto mehaničar -> auto servis; šminkerka -> šminker, kozmetički salon).
- Ako ispiše `nema kategorije` i ima malo lidova, ponovi `sakupi` sa boljim sinonimima.

## Korak 2: ako fali lidova, Chrome (tim redom, stani čim `Sa kontaktom` >= cilj)

Koristi Claude in Chrome alate (`mcp__claude-in-chrome__*`). Radi u NOVOM tabu, ne diraj korisnikove tabove.
Za čitanje stranica koristi čitanje teksta stranice (brže), a screenshot samo kad moraš.

**a) Košnica kontakti**: za svaki id koji `status` izlista:
- Otvori link. Kontakt se vidi samo ulogovanom korisniku. Ako piše „Prijavi se da vidiš kontakt", STANI i zamoli korisnika
  da se jednom uloguje na kosnica.net u tom Chrome-u, pa nastavi.
- Klikni da prikažeš kontakt (telefon / mejl / sajt) i upiši:
  `py -m lidovi kontakt --id <id> --telefon "<broj>" [--mail "<mejl>"] [--sajt "<url>"]`
- Ako nema kontakta: `py -m lidovi kontakt --id <id> --nema`
- NIKAD ne šalji upit ili poruku, ne troši „dukate", ne plaćaj ništa.

**b) KupujemProdajem** (kupujemprodajem.com):
- Pretraži `<delatnost> <grad>` (po mogućstvu kategorija Usluge). Uzimaj oglase koji nude USLUGU ili radnju
  (majstor, salon, servis), ne prodaju polovnih stvari.
- U oglasu klikni na prikaz broja telefona. Ime prodavca ili firme = naziv. Ako broj traži login, zamoli korisnika da se uloguje.
- `py -m lidovi dodaj --naziv "<naziv>" --zanimanje "<šta radi>" --mesto "<grad>" --telefon "<broj>" [--mail ...] [--sajt ...] --link "<url oglasa>" --izvor KupujemProdajem`
- Isti prodavac sa više oglasa = jedan lid (alat sam odbija duplikate po telefonu).

**c) Halo Oglasi** (halooglasi.com): isto kao KP, `--izvor "Halo Oglasi"`.
Ako se pojavi Cloudflare provera ili CAPTCHA, zamoli korisnika da je reši, pa nastavi.

Između otvaranja oglasa pravi kratke pauze (1-3 s). Bez masovnog otvaranja tabova.

## Korak 3: izbor

```
py -m lidovi izaberi
```
Bira najboljih N: prvo oni BEZ sajta, sa mobilnim brojem i mejlom (korisnik prodaje sajtove, SEO i marketing).

## Korak 4: Google provera (Chrome), za svaki id koji `status` izlista

- Otvori `https://www.google.com/maps/search/<naziv> <grad>` (URL-enkodovano).
- Profil postoji ako se pojavi biznis sa tim (ili vrlo sličnim) nazivom u tom gradu, ili sa istim telefonom.
  Ako je lista rezultata, uzmi onaj koji se poklapa. Ako ništa ne odgovara: profil = ne.
- Pročitaj prosečnu ocenu (zvezdice) i broj recenzija. Ako profil ima dugme za sajt, upiši i sajt.
- `py -m lidovi google --id <id> --profil da --zvezdice 4.6 --broj 120 [--sajt "<url>"] [--link "<maps url>"]`
- ili `py -m lidovi google --id <id> --profil ne`
- Alat sam računa ocenu 0-100. Ne izmišljaj podatke; ako stranica ne može da se učita, probaj još jednom pa upiši `--profil ne`.

## Korak 5: završetak

```
py -m lidovi zavrsi
```
Javi korisniku: putanju do .txt fajla, koliko lidova, koliko je VISOK prioritet, i odakle su (po sajtu).
Ako nije bilo moguće skupiti ceo cilj, reci koliko fali i zašto.

## Pravila

- Uzimaj samo javno objavljene kontakte iz oglasa i profila. Ne pogađaj mejlove i brojeve.
- Bez slanja poruka, poziva, upita, plaćanja ili objavljivanja bilo čega na ovim sajtovima.
- Ne loguj se umesto korisnika i ne unosi lozinke; kad treba login, zamoli korisnika.
