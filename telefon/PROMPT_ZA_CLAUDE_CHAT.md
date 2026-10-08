# Prompt za Claude Chat (telefon): skripta za 10 lidova u Google dokument

Kopiraj sve ispod linije i pošalji Claude-u u Claude Chat aplikaciji
(najbolje u novom Projektu, npr. „Lidovi telefon"). Pre toga u Settings → Connectors uključi **Google Drive / Google Docs**.

---

Napravi mi „skriptu" (uputstvo za ovaj Projekat) koju ću pokretati sa telefona jednom porukom, npr.
`lidovi: frizer, Novi Sad`. Svako pokretanje treba da nađe **10 novih lidova** i da ih doda u **Google dokument**.
Kada napraviš uputstvo, sačuvaj ga u instrukcije Projekta (ili mi ga daj da ga nalepim tamo), pa ga odmah testiraj
jednim pokretanjem za `frizer, Beograd`.

## Ko sam i šta mi treba
Prodajem marketing: izradu sajtova, SEO (ključne reči, optimizacija), reklame. Lidovi su male radnje, majstori i
preduzetnici koji kače oglase. Najbolji lid je onaj **bez sajta** i sa **slabim ili nepostojećim Google profilom**.

## Izvori (redom, stani kad imaš 10)
Na telefonu nemam Chrome ekstenziju, pa koristi samo ono što možeš da otvoriš preko web fetch-a i web pretrage:

1. **Plan Plus** (planplus.rs), javni telefoni:
   - Lista kategorija grada: `https://www.planplus.rs/<grad-slug>/kategorije` (npr. `novi-sad`, `beograd`, `nis`). Izaberi kategoriju koja odgovara delatnosti.
   - Lista: `https://www.planplus.rs/<grad-slug>/<kategorija>` i strane `/2`, `/3`… Svaka firma je `div.box.box-item` sa `data-name`, `data-address` i `tel:` linkom. Preskoči „privremeno zatvoren".
   - Stranica firme (`/<naziv>/<id>`): sajt je link sa `objectWebSiteClick`, a mejl stoji u JSON-LD kao `"email":"malito:..."` (sa greškom u kucanju, skini `malito:`/`mailto:`).
2. **011info** (011info.com), **samo za Beograd**: pretraga `https://www.011info.com/pretraga/<strana>?text=<delatnost>`. Stranica firme ima listu „Adresa / Telefon / E-mail".
3. **Košnica** (kosnica.net): lista `https://kosnica.net/<delatnost>-<grad-slug>` (JSON-LD `ItemList` sa nazivima). Kontakt se vidi samo ulogovanima, pa za te firme probaj da nađeš telefon ili mejl web pretragom („<naziv> <grad> telefon"). Ako ne nađeš, preskoči.
4. **KupujemProdajem / Halo Oglasi**: obično blokiraju fetch. Probaj web pretragom („<delatnost> <grad> kupujemprodajem"); uzmi samo ono što je javno vidljivo. Ako ne ide, preskoči bez trošenja vremena.

Ako delatnost nema kategoriju, probaj sinonim (zubar → stomatolog, mehaničar → auto servis).

## Pravila za lidove
- Lid mora imati **telefon ili mejl**. Ako nema ni jedno, preskoči.
- Telefon zapiši kao `0641234567` (mobilni prvo). Više brojeva odvoji zarezom.
- Ne izmišljaj i ne pogađaj podatke. Uzimaj samo javno objavljene kontakte.
- **Bez ponavljanja:** pre traženja pročitaj ceo Google dokument „Lidovi" i preskoči svaku firmu čiji telefon, mejl ili naziv+grad već postoji u njemu. Dokument je istorija.
- Od kandidata uzmi 10 najboljih: prvo bez sajta, sa mobilnim brojem i mejlom.

## Google provera (za svakog od 10)
Web pretragom („<naziv> <grad>", „<naziv> <grad> google recenzije") nađi Google Maps / Business profil:
- **Google profil**: `da` / `ne`
- **Google recenzije**: `4.6★ (120)`, ili `ne`
- **Google ocena 0–100** (ova formula, ne procena napamet): ako nema profila → 0; profil bez recenzija → 20;
  inače `prosek = (broj × zvezdice + 5 × 3.5) / (broj + 5)`, pa `ocena = round((prosek − 1) / 4 × 100)`.
  Primeri: 5.0★ (2) = 73, 4.7★ (200) = 92, 4.0★ (15) = 72.
- Ako Google profil ima sajt, a mi ga nismo imali, upiši ga.
- Ako ne možeš pouzdano da utvrdiš, napiši `nije provereno`, nemoj da izmišljaš.

**Prioritet**: poeni = 50 ako nema sajt; + 30 ako nema Google profil; ili, ako ima profil, + 15 ako je ocena < 60 i + 10 ako ima manje od 10 recenzija.
VISOK ≥ 50, SREDNJI ≥ 25, inače NIZAK. Poređaj od najvećeg.

## Google dokument
- Jedan dokument u mom Google Drive-u, naziv **„Lidovi"**. Ako ne postoji, napravi ga.
- Svako pokretanje doda **novi beč na kraj** dokumenta:
  - naslov: `Beč <redni broj>: <delatnost>, <grad> (<datum>)`
  - tabela sa 10 redova i kolonama:
    `Naziv | Zanimanje | Mesto | Telefon | Mail | Sajt | Link oglasa | Google profil | Google ocena (0-100) | Google recenzije | Prioritet`
  - gde nečega nema piše `ne`; kolona Sajt je `da: <url>` ili `ne`.
- Ne briši i ne menjaj prethodne bečeve.

## Na kraju svakog pokretanja
U jednoj kratkoj poruci: link ka dokumentu, broj beča, koliko je VISOK prioritet, odakle su lidovi (po sajtu),
i ako nisi našao svih 10 – koliko fali i zašto.

## Ograničenja
Bez slanja poruka, upita ili plaćanja na sajtovima. Ne loguj se nigde. Ako sajt blokira pristup, pređi na sledeći izvor.
