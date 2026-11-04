# Polako slanje draftova (jednom podesiš, radi samo)

Skill `/kafici-restorani` samo **pravi draftove** u Gmail-u. Šalje ih ova skripta, u Google-ovom oblaku,
pa laptop ne mora da bude uključen.

## Postavljanje (5 minuta, jednom)

1. U Chrome-u se uloguj kao **prikazreklame@gmail.com** i otvori <https://script.google.com> → **Novi projekat**.
2. Obriši sve iz `Code.gs` i nalepi ceo sadržaj fajla `slanje/posalji_draftove.gs`. Sačuvaj (Ctrl+S), nazovi projekat „Kampanja slanje".
3. Gore u meniju izaberi funkciju **`podesi`** → **Pokreni**. Google traži dozvolu: izaberi nalog prikazreklame,
   „Advanced" → „Go to Kampanja slanje" → **Allow**.
4. Gotovo. U **Executions** (levo) vidiš svako slanje.

- `stanje` → koliko je poslato danas, koliki je limit, koliko draftova čeka.
- `zaustavi` → prestaje da šalje (draftovi ostaju).

## Koliko i kada šalje

| | |
|---|---|
| Dani | ponedeljak–petak |
| Vreme | 9:00–17:00 (Beograd) |
| Razmak | jedan po jedan, nasumično na ~10–30 min |
| Prvi dan | 15 mejlova |
| Svaki sledeći radni dan | +5 |
| Najviše | 40 dnevno |

Tako 500 mejlova ode za oko 3 nedelje. Ovo je namerno sporo: nov Gmail nalog koji odjednom pošalje stotine
mejlova nepoznatim ljudima Google brzo označi kao spam ili zaključa slanje. Brojeve menjaš na vrhu skripte
(`PRVI_DAN`, `RAST_PO_DANU`, `MAKS_PO_DANU`), ali ne idi preko ~50 dnevno sa običnim Gmail nalogom.

## Zaštite

- Šalje **samo** draftove kampanje (one sa rečenicom „odgovorite sa NE…"). Tvoji drugi draftovi se ne diraju.
- Nikad ne šalje istoj adresi dva puta i ne piše onome ko ti je već pisao/odgovorio (taj draft obriše).
- Ako u jednom danu stigne 4+ „Delivery failed", staje do sutra.
- Svaki poslat mejl dobija labelu **Kampanja/poslato**, da lako vidiš odgovore.

## Da mejlovi ne idu u spam

- Pre prvog slanja u Gmail podešavanjima stavi **ime pošiljaoca** (npr. „Aleksa | Prikaz") i sliku profila.
- Odgovaraj brzo onima koji odgovore. Razgovori podižu ugled naloga.
- Ko odgovori „NE": skill ga pri sledećem pokretanju upiše u `firme/odjave.txt` i nikad mu više ne piše.
