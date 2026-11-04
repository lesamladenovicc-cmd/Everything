/**
 * Polako slanje draftova kampanje iz Gmail-a (prikazreklame@gmail.com).
 *
 * Radi u Google-ovom oblaku, laptop ne mora biti uključen.
 * Postavljanje (jednom): vidi slanje/UPUTSTVO.md
 *
 * Šalje SAMO draftove koji imaju liniju za odjavu iz kampanje (OZNAKA), jedan po jedan,
 * radnim danima u radno vreme, sa nasumičnim razmacima. Broj po danu raste polako
 * ("zagrevanje" novog naloga) da Gmail ne bi označio nalog kao spam.
 */

var PODESAVANJA = {
  OZNAKA: 'odgovorite sa NE i više vam nećemo pisati', // rečenica koja postoji samo u mejlovima kampanje
  ZONA: 'Europe/Belgrade',
  OD_SATA: 9,            // šalje od 9:00
  DO_SATA: 17,           // do 17:00
  DANI: [1, 2, 3, 4, 5], // pon-pet (0 = nedelja)
  PRVI_DAN: 15,          // prvog dana šalje 15
  RAST_PO_DANU: 5,       // svakog radnog dana +5
  MAKS_PO_DANU: 40,      // nikad više od 40 dnevno
  MAKS_ODBIJENIH: 4,     // ako danas stigne 4+ "Delivery failed", pauza do sutra
  LABELA: 'Kampanja/poslato'
};

/** Pokreni JEDNOM ručno: pravi okidač na svakih 10 minuta. */
function podesi() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'posaljiSledeci') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('posaljiSledeci').timeBased().everyMinutes(10).create();
  GmailApp.createLabel(PODESAVANJA.LABELA);
  Logger.log('Okidač napravljen. Na čekanju: ' + brojDraftovaKampanje_() + ' draftova.');
}

/** Zaustavlja slanje (draftovi ostaju). */
function zaustavi() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  Logger.log('Slanje zaustavljeno.');
}

/** Pregled: koliko je poslato danas, koliko čeka, koliki je današnji limit. */
function stanje() {
  var s = stanje_();
  Logger.log('Danas poslato: ' + s.danas + '/' + limitZaDanas_(s) +
    ' | radnih dana slanja: ' + s.radnihDana + ' | ukupno poslato: ' + s.ukupno +
    ' | čeka draftova: ' + brojDraftovaKampanje_());
}

function posaljiSledeci() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    var P = PODESAVANJA;
    var sada = new Date();
    var dan = Number(Utilities.formatDate(sada, P.ZONA, 'u')) % 7; // 1=pon ... 7=ned -> 0
    var sat = Number(Utilities.formatDate(sada, P.ZONA, 'H'));
    var minut = Number(Utilities.formatDate(sada, P.ZONA, 'm'));
    if (P.DANI.indexOf(dan) < 0 || sat < P.OD_SATA || sat >= P.DO_SATA) return;

    var s = stanje_();
    var limit = limitZaDanas_(s);
    if (s.danas >= limit) return;

    // ravnomerno kroz dan: do sada bi trebalo da je poslato limit * (proteklo vreme / ceo dan)
    var proteklo = ((sat - P.OD_SATA) * 60 + minut) / ((P.DO_SATA - P.OD_SATA) * 60);
    var trebalo = Math.ceil(limit * Math.min(1, proteklo + 0.05));
    if (s.danas >= trebalo) return;
    if (Math.random() < 0.35) return; // nasumičan razmak, ne šalje uvek na tačno 10 minuta

    if (odbijenihDanas_() >= P.MAKS_ODBIJENIH) {
      Logger.log('Previše odbijenih mejlova danas, pauza do sutra.');
      return;
    }

    var kandidati = sledeciDraftovi_(10);
    for (var i = 0; i < kandidati.length; i++) {
      var d = kandidati[i];
      var prima = adresa_(d.getMessage().getTo());
      if (!prima) continue;
      // nikad dva puta istoj adresi i ne pišemo onome ko nam je već odgovorio / pisao
      if (GmailApp.search('in:sent to:' + prima, 0, 1).length ||
          GmailApp.search('from:' + prima + ' -in:drafts', 0, 1).length) {
        Logger.log('Preskačem (već u kontaktu): ' + prima);
        d.deleteDraft();
        continue;
      }
      var poruka = d.send();
      poruka.getThread().addLabel(GmailApp.getUserLabelByName(P.LABELA) || GmailApp.createLabel(P.LABELA));
      s.danas += 1;
      s.ukupno += 1;
      sacuvajStanje_(s);
      Logger.log('Poslato: ' + prima + ' (' + s.danas + '/' + limit + ' danas)');
      return; // jedan mejl po pokretanju
    }
  } finally {
    lock.releaseLock();
  }
}

// ---------- pomoćne ----------

var UPIT_ = 'in:drafts "' + PODESAVANJA.OZNAKA + '"';

/** Do `koliko` draftova kampanje (malo poziva Gmail-u, bez čitanja svih 500 draftova). */
function sledeciDraftovi_(koliko) {
  var idPoruka = {};
  var niti = GmailApp.search(UPIT_, 0, 50);
  niti.reverse().slice(0, koliko).forEach(function (t) {
    t.getMessages().forEach(function (m) { if (m.isDraft()) idPoruka[m.getId()] = true; });
  });
  return GmailApp.getDrafts().filter(function (d) { return idPoruka[d.getMessageId()]; });
}

function brojDraftovaKampanje_() {
  var n = 0, strana;
  do {
    strana = GmailApp.search(UPIT_, n, 100);
    n += strana.length;
  } while (strana.length === 100);
  return n;
}

function adresa_(to) {
  var m = String(to || '').match(/[^\s<>,;"]+@[^\s<>,;"]+/);
  return m ? m[0].toLowerCase() : '';
}

function stanje_() {
  var props = PropertiesService.getScriptProperties();
  var danas = Utilities.formatDate(new Date(), PODESAVANJA.ZONA, 'yyyy-MM-dd');
  var s = JSON.parse(props.getProperty('stanje') || '{}');
  if (s.datum !== danas) {
    if (s.datum && s.danas > 0) s.radnihDana = (s.radnihDana || 0) + 1;
    s.datum = danas;
    s.danas = 0;
  }
  s.radnihDana = s.radnihDana || 0;
  s.ukupno = s.ukupno || 0;
  sacuvajStanje_(s);
  return s;
}

function sacuvajStanje_(s) {
  PropertiesService.getScriptProperties().setProperty('stanje', JSON.stringify(s));
}

function limitZaDanas_(s) {
  var P = PODESAVANJA;
  return Math.min(P.MAKS_PO_DANU, P.PRVI_DAN + P.RAST_PO_DANU * s.radnihDana);
}

function odbijenihDanas_() {
  return GmailApp.search('from:mailer-daemon newer_than:1d', 0, 50).length;
}
