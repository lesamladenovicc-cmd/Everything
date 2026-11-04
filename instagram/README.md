# IG autopilot za @prikaz.rs (radi 24/7 u oblaku)

Claude se pokreće **svakih sat vremena u oblaku** (zakazani zadatak na claude.ai), pa radi i kad je laptop ugašen.
Ne koristi Chrome, nego zvanični Instagram API, pa nalog nije u opasnosti od blokade za "bota".

| Radi sam | Ne može preko API-ja (ostaje za Chrome skill `prikaz-instagram`) |
|---|---|
| Kači objave, karusele, reelsove i storije iz `plan.json` | Lajkovanje i komentarisanje tuđih objava |
| Odgovara na komentare na našim objavama, sakriva spam | Praćenje naloga |
| Odgovara na DM poruke (u roku od 24h od njihove poruke) | Storiji sa anketom / pitanjem |
| Dnevna statistika, izveštaj posle svakog prolaza | Prvi DM nekome ko nam nije pisao |

## Podešavanje (jednom, ~20 minuta)

1. **Profesionalni nalog:** u Instagram aplikaciji @prikaz.rs mora biti *Business* ili *Creator* nalog
   (Podešavanja → Tip naloga i alati).
2. **Meta aplikacija:** na https://developers.facebook.com → My Apps → Create App → tip *Business*,
   dodaj proizvod **Instagram** → "API setup with Instagram login".
3. Dozvole: `instagram_business_basic`, `instagram_business_content_publish`,
   `instagram_business_manage_comments`, `instagram_business_manage_messages`, `instagram_business_manage_insights`.
4. U "Generate access tokens" dodaj @prikaz.rs i klikni **Generate token**. Dobijaš dugotrajni token (60 dana).
   Za sopstveni nalog aplikacija radi u *Development* modu bez Meta pregleda, jer si ti admin aplikacije.
5. **Cloud okruženje na claude.ai:** u podešavanjima okruženja dodaj promenljivu `IG_TOKEN=<token>`.
   Mreža okruženja mora da pusti `graph.instagram.com`.
6. Javi Claude-u "token je unet" — on pokrene `python -m instagram provera` i napravi zakazani zadatak (svaki sat).

Token traje 60 dana. Autopilot ga ponedeljkom produžava i javlja koliko još važi; ako javi da se promenio
ili da ističe, napravi novi u koraku 4 i zameni `IG_TOKEN`.

## Mediji za objave

Instagram sam preuzima sliku/video sa **javnog https linka** (`.jpg` slike, `.mp4` video; reel 9:16).
Opcije: sopstveni hosting na prikaz.rs (npr. `prikaz.rs/ig/reel-01.mp4`), GitHub Pages ili bilo koji CDN.
Google Drive linkovi često ne rade jer nisu direktan fajl.

## Plan (`plan.json`)

```json
{
  "objave": [
    {"id": "reel-telefon-cuti", "kada": "2026-11-06T19:30:00+01:00", "tip": "reel",
     "mediji": ["https://prikaz.rs/ig/reel-01.mp4"],
     "caption": "Plaćate reklame, a telefon ćuti?\n\n...\n\nNapišite REKLAME u DM ili pozovite 060 533 9990\n#marketingsrbija #beograd"},
    {"id": "story-pet", "kada": "2026-11-07T10:00:00+01:00", "tip": "story",
     "mediji": ["https://prikaz.rs/ig/story-01.jpg", "https://prikaz.rs/ig/story-02.jpg"]}
  ]
}
```

- Autopilot proverava svaki sat, pa objava izlazi u roku od ~1h posle `kada`.
- Već objavljeno prepoznaje po captionu (postovi) ili po vremenu storija, pa ništa ne kači dvaput.
- Post koji kasni više od 24h i story koji kasni više od 2h se ne kače, nego se prijave.
- Storiji: više slika ide u jednu stavku; stavke za storije bar 2h razmaka.
- Autopilot čita plan sa **glavne grane** repozitorijuma — posle izmene uradi commit i push.

## Komande (ručno)

```
python -m instagram provera            # da li token radi
python -m instagram plan               # status svake stavke iz plana
python -m instagram objavi-plan --suvo # šta bi sad bilo objavljeno
python -m instagram komentari          # komentari bez našeg odgovora
python -m instagram poruke             # DM-ovi bez odgovora
python -m instagram statistika
```
