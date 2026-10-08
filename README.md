# Lidovi: 50 lidova po pokretanju

Unosiš **delatnost** i **grad**, a dobijaš `.txt` tabelu sa do 50 novih lidova sa sajtova
**Plan Plus, 011info, Košnica, KupujemProdajem i Halo Oglasi**. Za svaki lid je proveren i Google profil.

## Šta dobijaš

Fajl `rezultati/lidovi_<delatnost>_<grad>_<datum>.txt`. Kolone su odvojene tabom, pa ga možeš otvoriti
u Notepad-u ili ga označiti, kopirati i nalepiti u Excel / Google Sheets.

| Kolona | Primer |
|---|---|
| Naziv | Frizerski salon Bella |
| Zanimanje | Frizerski saloni |
| Mesto | Novi Sad (Gajeva 14) |
| Telefon | 0641234567 (ili `ne`) |
| Mail | salon@gmail.com (ili `ne`) |
| Sajt | `da: https://...` ili `ne` |
| Link oglasa | link do oglasa ili profila |
| Google profil | `da` / `ne` |
| Google ocena (0-100) | 87 (0 = nema profila) |
| Google recenzije | `4.6★ (120)` ili `ne` |
| Prioritet | VISOK / SREDNJI / NIZAK |

- Lid bez telefona i bez mejla se preskače.
- **Prioritet** je napravljen za prodaju sajtova i SEO: VISOK znači da nema sajt, a često ni Google profil ili ima slabe recenzije. Lista je poređana od najboljih.
- **Google ocena** uzima prosek zvezdica, ali ga za firme sa malo recenzija vuče ka 3,5: 5★ sa 2 recenzije = 73, 4,7★ sa 200 recenzija = 92. Profil bez recenzija = 20, bez profila = 0.
- **Bez ponavljanja:** `istorija.json` pamti sve što je već izvezeno, pa ti sledeće pokretanje ne vraća iste ljude.

## Kako radi

1. **Python (brzo, ~30 s):** Plan Plus i 011info (011info samo za Beograd) daju naziv, telefon, mejl i sajt. Sa Košnice uzima listu biznisa.
2. **Chrome (Claude in Chrome):** kontakti sa Košnice (vide se samo ulogovanima), pa KupujemProdajem i Halo Oglasi ako fali lidova. Ovi sajtovi nemaju API i blokiraju automatske zahteve, pa ide preko tvog Chrome-a.
3. **Izbor najboljih 50:** prvo bez sajta, sa mobilnim i mejlom.
4. **Google Maps provera** za svaki od 50 (Chrome, bez API ključa).
5. **Pravi `.txt`** i upisuje u istoriju.

Jedno pokretanje traje otprilike 15-30 minuta, a najviše vremena odlazi na Google proveru.

## Instalacija na Windows laptopu (jednom)

1. **Chrome + Claude in Chrome ekstenzija:** instaliraj ekstenziju iz Chrome Web Store-a i uloguj se istim Claude nalogom.
2. **Claude Code:** u PowerShell-u pokreni
   ```
   irm https://claude.ai/install.ps1 | iex
   ```
   pa jednom pokreni `claude` i uloguj se.
3. **Preuzmi ovaj projekat** (vidi „Prebacivanje na novi repozitorijum" ispod) u neki folder, npr. `C:\lidovi`.
4. **Dupli klik na `setup.bat`.** Instalira Git, Python i biblioteke. Ako kaže da zatvoriš prozor, zatvori ga i pokreni `setup.bat` ponovo.
5. U Chrome-u se **uloguj na kosnica.net i kupujemprodajem.com** (da bi se videli telefoni).

> Claude Code pokreći iz običnog Windows terminala (CMD / PowerShell ili lokalni terminal u MobaXterm-u), **ne iz WSL-a**, jer Chrome integracija ne radi u WSL-u.

## Pokretanje

- **Dupli klik na `pokreni.bat`**, upiši delatnost i grad, i to je to. Chrome mora biti otvoren.
- Ili ručno, u folderu projekta:
  ```
  claude --chrome
  ```
  pa u Claude-u: `/lidovi delatnost: frizer, grad: Novi Sad`

Kada Claude prvi put otvara neki sajt, ekstenzija može da traži dozvolu, pa klikni „Allow".
Ako sajt traži login ili CAPTCHA, Claude stane i zamoli te da to uradiš, pa nastavi.

### Ručne komande (ako hoćeš bez Claude-a, samo brzi sajtovi)

```
py -m lidovi sakupi --delatnost "frizer" --grad "Novi Sad"
py -m lidovi izaberi
py -m lidovi zavrsi --bez-google
py -m lidovi status --sve
```

## Prebacivanje na novi repozitorijum

Kod kuće napravi **novi prazan** repozitorijum na GitHub-u (bez README-a), pa u terminalu:

```
git clone -b claude/lidovi-skripta https://github.com/lesamladenovicc-cmd/Everything.git C:\lidovi
cd C:\lidovi
git remote set-url origin https://github.com/<tvoj-nalog>/<novi-repo>.git
git push -u origin claude/lidovi-skripta:main
git branch -m main
git branch -u origin/main
```

Bez Git-a: na GitHub-u otvori granu `claude/lidovi-skripta`, pa **Code → Download ZIP**, raspakuj u `C:\lidovi` i ubaci fajlove u novi repo.

`istorija.json`, `rad/` i `rezultati/` se ne šalju na GitHub (lični podaci). Ako hoćeš istoriju i na drugom računaru, kopiraj `istorija.json` ručno.

## Napomene

- KupujemProdajem i Halo Oglasi u svojim pravilima ne dozvoljavaju automatsko izvlačenje podataka. Zato tamo Claude ide sporo, kroz tvoj Chrome, i ne otvara masovno oglase. Ne teraj ga na stotine oglasa dnevno jer može da ti blokira nalog.
- Kontakti su lični podaci (Zakon o zaštiti podataka o ličnosti). Koristi ih za jednu ličnu, relevantnu ponudu i ukloni svakoga ko kaže da ne želi da ga kontaktiraš.
