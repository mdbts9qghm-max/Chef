/* Baukasten – Woche in der App selbst zusammenstellen (generiert aus tools/web_static/baukasten.js).
   Regeln wie im Planer (tools/planer.py: struktur, kochtag, plan_dict, einfrieren, notiz) und Einkauf wie
   tools/einkauf.py (berechne, kosten). Daten: window.BAUKASTEN (tools/web.py → baukasten_daten). */
(function () {
  "use strict";
  var B = window.BAUKASTEN, D = window.REZEPTBUCH || {};
  var wurzel = document.getElementById("baukasten");
  if (!wurzel || !B) return;
  var R = B.regeln, REZ = B.rezepte, PK = B.packungen, G = R.gewicht, EPS = 1e-6;
  var SLOTS = R.slots, HAUPT = ["mittag", "abend"];
  var GRUPPE = { fruehstueck: "fruehstueck", mittag: "haupt", abend: "haupt", snack: "snack" };

  // --- Hilfen ------------------------------------------------------------------------------------
  function zahl(x, nk) {
    nk = nk === undefined ? 1 : nk;
    return Number(x).toLocaleString("de-DE", { minimumFractionDigits: 0, maximumFractionDigits: nk });
  }
  function euro(x) { return Number(x).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €"; }
  function gramm(g) { return zahl(g, g >= 10 ? 0 : 1) + " g"; }
  function el(tag, attrs, kinder) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") e.textContent = attrs[k]; else if (k === "html") e.innerHTML = attrs[k]; else e.setAttribute(k, attrs[k]);
    });
    (kinder || []).forEach(function (c) { if (c) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return e;
  }
  function speicher(key, wert) {
    try {
      if (wert === undefined) { var v = window.localStorage.getItem(key); return v ? JSON.parse(v) : null; }
      if (wert === null) window.localStorage.removeItem(key); else window.localStorage.setItem(key, JSON.stringify(wert));
    } catch (e) { /* privater Modus: nur im Speicher */ }
    return null;
  }
  var PARAM = new URLSearchParams(location.search);
  function heuteIso() {
    var p = PARAM.get("heute");
    if (p && /^\d{4}-\d{2}-\d{2}$/.test(p)) return p;
    try { return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Berlin" }); }
    catch (e) { return new Date().toISOString().slice(0, 10); }
  }
  function tageZwischen(a, b) { return Math.round((Date.parse(b + "T12:00:00Z") - Date.parse(a + "T12:00:00Z")) / 864e5); }
  function plusTage(iso, n) { return new Date(Date.parse(iso + "T12:00:00Z") + n * 864e5).toISOString().slice(0, 10); }
  function wtag(iso) { return R.wochentage[(new Date(iso + "T12:00:00Z").getUTCDay() + 6) % 7]; }
  function wtagLang(iso) { return R.wochentage_lang[(new Date(iso + "T12:00:00Z").getUTCDay() + 6) % 7]; }
  function ddmm(iso) { return iso.slice(8, 10) + "." + iso.slice(5, 7) + "."; }
  function slotName(s) { return R.slot_namen[s]; }
  function passtZuSlot(r, slot) {
    if (slot === "fruehstueck") return r.mahlzeit === "Frühstück" && r.geschmack === "süß";
    if (slot === "snack") return r.mahlzeit === "Snack";
    return r.mahlzeit === "Mittag/Abend";
  }
  function aussortiert(r) { return r.sterne !== null && r.sterne !== undefined && r.sterne <= 2; }

  // --- Woche und Entwurf -----------------------------------------------------------------------------
  var HEUTE = heuteIso();
  var WOCHEN = B.wochen;
  function wocheVon(iso) { return WOCHEN.filter(function (w) { return w.tage[0] <= iso && iso <= w.tage[6]; })[0]; }
  var aktuell = wocheVon(HEUTE), naechste = aktuell ? WOCHEN[WOCHEN.indexOf(aktuell) + 1] : null;
  var W = WOCHEN.filter(function (w) { return w.name === PARAM.get("woche"); })[0] || naechste || aktuell;
  var SCHICHT = {};
  WOCHEN.forEach(function (w) { w.tage.forEach(function (t, i) { SCHICHT[t] = w.schichten[i]; }); });

  function leererEntwurf() { return { tage: {}, auswaerts: {}, basis: "leer" }; }
  function ausPlan(name) {
    var p = B.plaene[name];
    if (!p) return null;
    var e = { tage: {}, auswaerts: {}, basis: "plan" };
    p.tage.forEach(function (t) {
      var iso = String(t.datum).slice(0, 10);
      e.tage[iso] = {};
      SLOTS.forEach(function (s) {
        var x = t[s];
        if (x) e.tage[iso][s] = { r: x.rezept, f: x.faktor === undefined ? 1 : Number(x.faktor), rest: x.rest_von || null };
      });
      if (t.auswaerts && t.auswaerts.mahlzeit) e.auswaerts[iso] = t.auswaerts.mahlzeit;
    });
    return e;
  }
  function schluessel(w) { return "baukasten:" + w.name; }
  function laden(w) {
    var e = speicher(schluessel(w));
    if (e && e.gespeichert && B.erstellt > e.gespeichert && w.plan) e = null;   // GitHub hat die Woche übernommen
    return e || ausPlan(w.name) || leererEntwurf();
  }
  var E = laden(W);
  function sichern() { E.geaendert = new Date().toISOString(); speicher(schluessel(W), E); }
  function eintrag(e, iso, slot) { return (e.tage[iso] || {})[slot] || null; }
  function setzen(e, iso, slot, x) {
    e.tage[iso] = e.tage[iso] || {};
    if (x) e.tage[iso][slot] = x; else delete e.tage[iso][slot];
  }
  function gesperrt(iso) { return iso < HEUTE; }
  function kopie(e) { return JSON.parse(JSON.stringify(e)); }

  // --- Struktur ableiten (wie planer.plan_dict) --------------------------------------------------------
  function kochtag(iso) { return SCHICHT[iso] === "Tag" ? plusTage(iso, -1) : iso; }
  function einkaufFuer(iso, w) {
    var t = w.einkauf.slice().sort(), vorher = t.filter(function (x) { return x <= iso; });
    return vorher.length ? vorher[vorher.length - 1] : t[0];
  }
  function ableiten(e, w) {
    var liste = [], idx = {};
    w.tage.forEach(function (iso, i) {
      SLOTS.forEach(function (slot) {
        var x = eintrag(e, iso, slot);
        if (!x || !REZ[x.r]) return;
        var m = { key: iso + "/" + slot, datum: iso, tag: i, slot: slot, r: x.r, fest: x.f === undefined ? null : x.f,
                  rest: x.rest || null, kinder: [], fehler: [] };
        m.pos = liste.length; liste.push(m); idx[m.key] = m;
      });
    });
    liste.forEach(function (m) {   // gültige Reste: Original vorher, gleiches Rezept, gekocht, Platz frei
      var q = m.rest ? idx[m.rest] : null;
      if (!q || q.rest || q.r !== m.r || q.pos >= m.pos || q.kinder.length + 1 >= R.max_ladungen) { m.rest = null; }
      else q.kinder.push(m);
    });
    liste.forEach(function (m) {
      m.kochen = !m.rest;
      if (m.kochen) m.gekocht_am = kochtag(m.datum);
    });
    liste.forEach(function (m) {
      var q = m.rest ? idx[m.rest] : null;
      m.original = q;
      if (q) m.gekocht_am = q.gekocht_am;
      m.ladungen = m.kochen ? 1 + m.kinder.length : 0;
      var alter = tageZwischen(m.gekocht_am, m.datum);
      if (alter < 0) m.fehler.push("wird vor dem Kochen gegessen");
      else if (alter > REZ[m.r].tage) m.fehler.push(REZ[m.r].name + " ist dann " + alter + " Tage alt (erlaubt " + REZ[m.r].tage + ")");
      var s = SCHICHT[m.datum], boxen = R.boxen[s] || [];
      m.box = boxen.indexOf(m.slot) >= 0 || (m.slot === "snack" && !!R.boxen[s]);
      m.einfrieren = m.kochen && REZ[m.r].frische.some(function (f) {
        return f[1] === "frisch" && tageZwischen(einkaufFuer(m.gekocht_am, w), m.gekocht_am) > f[2];
      });
      m.notiz = notiz(m);
    });
    faktorenSetzen(liste, e, w);
    return { liste: liste, idx: idx };
  }
  function notiz(m) {
    var s = SCHICHT[m.datum];
    if (HAUPT.indexOf(m.slot) >= 0 && m.kinder.length) {
      var k = m.kinder[0], ziel = slotName(k.slot) + " " + wtag(k.datum);
      if (s === "Nacht" && m.slot === "abend") return "nachmittags mitkochen, Box für die Nacht; zweite Ladung = " + ziel;
      return "zweite Ladung = " + ziel;
    }
    if (s === "Nacht" && m.slot === "mittag" && m.kochen) return "vor der Schicht";
    return "";
  }

  // --- Tageswerte, Bewertung und automatischer Faktor -------------------------------------------------
  var TYPISCH = {};   // Ø Portion je Slot-Gruppe (für noch leere Plätze)
  (function () {
    var summe = {}, n = {};
    Object.keys(REZ).forEach(function (id) {
      var r = REZ[id];
      SLOTS.forEach(function (s) {
        if (!passtZuSlot(r, s) || aussortiert(r)) return;
        var g = GRUPPE[s]; summe[g] = summe[g] || { kcal: 0, protein: 0, fett: 0, kh: 0 }; n[g] = (n[g] || 0) + 1;
        ["kcal", "protein", "fett", "kh"].forEach(function (k) { summe[g][k] += r.p[k]; });
      });
    });
    Object.keys(summe).forEach(function (g) { TYPISCH[g] = {}; ["kcal", "protein", "fett", "kh"].forEach(function (k) { TYPISCH[g][k] = summe[g][k] / n[g]; }); });
  })();
  function offeneSlots(e, iso) {
    return SLOTS.filter(function (s) { return !eintrag(e, iso, s) && e.auswaerts[iso] !== s; });
  }
  function tagSumme(liste, e, iso, faktorVon) {
    var s = { kcal: 0, protein: 0, fett: 0, kh: 0, zucker: 0 };
    liste.forEach(function (m) {
      if (m.datum !== iso) return;
      var f = faktorVon ? faktorVon(m) : (m.kochen ? m.faktor : m.original.faktor), p = REZ[m.r].p;
      Object.keys(s).forEach(function (k) { s[k] += p[k] * f; });
    });
    if (e.auswaerts[iso]) ["kcal", "protein", "fett", "kh"].forEach(function (k) { s[k] += R.auswaerts[k]; });
    return s;
  }
  function strafe(s) {
    var z = R.ziele, p = 0;
    if (s.protein < R.protein_min) p += (R.protein_min - s.protein) * G.protein_fehlt;
    if (s.kcal > R.kcal_max) p += (s.kcal - R.kcal_max) * G.kcal_ueber;
    if (s.kcal < R.kcal_min) p += (R.kcal_min - s.kcal) * G.kcal_unter;
    var df = Math.abs(s.fett - z.fett) - R.fett_toleranz;
    if (df > 0) p += df * G.fett;
    if (s.fett < R.fett_min) p += (R.fett_min - s.fett) * G.fett;
    var dk = Math.abs(s.kh - z.kh) - R.kh_toleranz;
    if (dk > 0) p += dk * G.kh;
    return p;
  }
  function mitErwartung(s, e, iso, ohne) {   // leere Plätze mit typischen Werten auffüllen
    var x = { kcal: s.kcal, protein: s.protein, fett: s.fett, kh: s.kh };
    offeneSlots(e, iso).forEach(function (slot) {
      if (slot === ohne) return;
      var t = TYPISCH[GRUPPE[slot]];
      if (t) Object.keys(x).forEach(function (k) { x[k] += t[k]; });
    });
    return x;
  }
  function tagStatus(s) {
    var z = R.ziele, probleme = [];
    if (s.protein < R.protein_min) probleme.push("noch " + zahl(R.protein_min - s.protein, 0) + " g Protein offen");
    if (s.kcal > R.kcal_max) probleme.push(zahl(s.kcal - R.kcal_max, 0) + " kcal zu viel");
    if (s.kcal < R.kcal_min) probleme.push("noch " + zahl(R.kcal_min - s.kcal, 0) + " kcal offen");
    if (s.fett < Math.max(R.fett_min, z.fett - R.fett_toleranz)) probleme.push("wenig Fett (" + zahl(s.fett, 0) + " g)");
    if (s.fett > z.fett + R.fett_toleranz) probleme.push("viel Fett (" + zahl(s.fett, 0) + " g)");
    if (Math.abs(s.kh - z.kh) > R.kh_toleranz) probleme.push("KH " + zahl(s.kh, 0) + " g (Ziel " + z.kh + " ± " + R.kh_toleranz + ")");
    return { ok: !probleme.length, probleme: probleme };
  }
  function faktorenSetzen(liste, e, w) {
    liste.forEach(function (m) { if (m.kochen) { m.faktor = m.fest !== null ? m.fest : 1; m.auto = false; } });
    function von(m) { return m.kochen ? m : m.original; }
    w.tage.forEach(function (iso) {
      var frei = liste.filter(function (m) { return m.datum === iso && m.kochen && m.fest === null; });
      if (!frei.length || offeneSlots(e, iso).length || gesperrt(iso)) return;
      var best = null, n = frei.length, F = R.faktoren;
      for (var c = 0; c < Math.pow(F.length, n); c++) {
        var wahl = [], x = c, pf = 0;
        for (var j = 0; j < n; j++) { wahl.push(F[x % F.length]); pf += Math.abs(F[x % F.length] - 1) * G.faktor; x = Math.floor(x / F.length); }
        var s = tagSumme(liste, e, iso, function (m) { var q = von(m), k = frei.indexOf(q); return k >= 0 ? wahl[k] : q.faktor; });
        var p = strafe(s) + pf;
        if (!best || p < best.p - 1e-9) best = { p: p, wahl: wahl };
      }
      frei.forEach(function (m, k) { m.faktor = best.wahl[k]; m.auto = true; });
    });
    liste.forEach(function (m) { if (!m.kochen) m.faktor = m.original.faktor; });
  }

  // --- Wochenregeln (wie wochenplan.pruefe_plan, im Baukasten nur Hinweise) ----------------------------
  function wochenHinweise(a, e, w) {
    var h = [], vorher = null;
    w.tage.forEach(function (iso) {
      var ab = a.idx[iso + "/abend"];
      if (ab && !e.auswaerts[iso]) {
        var r = REZ[ab.r], jetzt = [r.kueche, r.quelle];
        if (vorher) {
          if (jetzt[0] === vorher[0]) h.push(wtag(iso) + ": Abendessen wieder " + jetzt[0] + " wie am Vortag");
          if (jetzt[1] && jetzt[1] === vorher[1]) h.push(wtag(iso) + ": Abendessen wieder mit " + (R.protein_gruppen[jetzt[1]] || jetzt[1]) + " wie am Vortag");
        }
        vorher = jetzt;
      } else vorher = null;
    });
    var haupt = {}, tage = { fruehstueck: {}, snack: {} }, drei = {};
    a.liste.forEach(function (m) {
      if (m.kochen && HAUPT.indexOf(m.slot) >= 0) haupt[m.r] = (haupt[m.r] || 0) + 1;
      if (tage[m.slot]) tage[m.slot][m.r] = (tage[m.slot][m.r] || 0) + 1;
      if (REZ[m.r].sterne === 3) drei[m.r] = 1;
      m.fehler.forEach(function (f) { h.push(wtag(m.datum) + " " + slotName(m.slot) + ": " + f); });
    });
    Object.keys(haupt).forEach(function (id) {
      if (haupt[id] > R.haupt_max_kochen) h.push("„" + REZ[id].name + "“ wird " + haupt[id] + "× gekocht (max. " + R.haupt_max_kochen + "×, Reste zählen nicht)");
    });
    [["fruehstueck", R.fruehstueck_max_tage], ["snack", R.snack_max_tage]].forEach(function (x) {
      Object.keys(tage[x[0]]).forEach(function (id) {
        if (tage[x[0]][id] > x[1]) h.push("„" + REZ[id].name + "“ an " + tage[x[0]][id] + " Tagen als " + slotName(x[0]) + " (max. " + x[1] + ")");
      });
    });
    if (Object.keys(drei).length > R.drei_sterne_max) h.push("3-Sterne-Rezepte " + Object.keys(drei).length + "× (max. " + R.drei_sterne_max + ")");
    return h;
  }
  function strukturFehler(a) {
    var f = [];
    a.liste.forEach(function (m) { m.fehler.forEach(function (x) { f.push(wtag(m.datum) + " " + slotName(m.slot) + ": " + x); }); });
    return f;
  }

  // --- Einkaufsliste (wie einkauf.berechne + einkauf.kosten) ---------------------------------------------
  function einkaufListe(a, w) {
    var termine = w.einkauf.slice().sort(), bestand = {};
    Object.keys(w.bestand).forEach(function (z) { bestand[z] = w.bestand[z] === null ? Infinity : w.bestand[z]; });
    function terminFuer(d) { var v = termine.filter(function (t) { return t <= d; }); return v.length ? v[v.length - 1] : termine[0]; }
    var je = {}, reihen = [], letzte = {};
    a.liste.forEach(function (m) {
      if (!m.kochen) return;
      var r = REZ[m.r], mult = m.faktor * m.ladungen;
      var txt = wtag(m.datum) + " " + slotName(m.slot) + (m.gekocht_am !== m.datum ? " (vorgekocht " + wtag(m.gekocht_am) + ")" : "") +
        ": " + r.name + (mult !== 1 ? " × " + zahl(mult, 2) : "");
      r.zutaten.forEach(function (z) {
        var k = terminFuer(m.gekocht_am) + "|" + z[0];
        if (!je[k]) { je[k] = { termin: terminFuer(m.gekocht_am), zutat: z[0], n: [] }; reihen.push(je[k]); }
        je[k].n.push({ g: z[1] * mult, wofuer: txt, einfrieren: m.einfrieren, datum: m.gekocht_am });
        if (!letzte[z[0]] || m.gekocht_am > letzte[z[0]]) letzte[z[0]] = m.gekocht_am;
      });
    });
    reihen.sort(function (x, y) { return x.termin < y.termin ? -1 : x.termin > y.termin ? 1 : x.zutat < y.zutat ? -1 : x.zutat > y.zutat ? 1 : 0; });
    var listen = termine.map(function (t) { return { datum: t, zeilen: [] }; });
    reihen.forEach(function (g) {
      var bedarf = g.n.reduce(function (s, n) { return s + n.g; }, 0);
      var vorhanden = bestand[g.zutat] === undefined ? 0 : bestand[g.zutat];
      var aus = Math.min(bedarf, vorhanden), rest = bedarf - aus, p = PK[g.zutat];
      var pakete = p && rest > EPS ? Math.ceil(rest / p[1] - EPS) : 0;
      if (vorhanden !== Infinity) {
        var gekauft = p ? pakete * p[1] : 0;
        bestand[g.zutat] = vorhanden - aus + (gekauft ? gekauft - rest : 0);
      }
      var wofuer = [];
      g.n.forEach(function (n) { if (wofuer.indexOf(n.wofuer) < 0) wofuer.push(n.wofuer); });
      var z = { zutat: g.zutat, bedarf: bedarf, aus_bestand: aus, pakete: pakete, packung: p || null, wofuer: wofuer,
                vorrat_unbekannt: vorhanden === Infinity, kosten: p && p[3] !== null ? pakete * p[3] : 0,
                vorratskauf: !!p && p[4] >= R.vorratskauf_ab, hinweis: frischeHinweis(g.zutat, g.n, g.termin, p) };
      listen.filter(function (l) { return l.datum === g.termin; })[0].zeilen.push(z);
    });
    var reste = {};
    Object.keys(bestand).forEach(function (z) {
      var g = bestand[z];
      if (g === Infinity || !(g > EPS) || !letzte[z]) return;
      var p = PK[z];
      reste[z] = { g: g, haltbar_bis: p ? plusTage(letzte[z], p[4]) : null };
    });
    return { listen: listen, reste: reste, kosten: kosten(listen) };
  }
  function frischeHinweis(zutat, ns, termin, p) {
    var frisch = null;
    Object.keys(REZ).some(function (id) { return REZ[id].frische.some(function (f) { if (f[0] === zutat) { frisch = f; return true; } return false; }); });
    if (!frisch) return "";
    if (p && p[0] === R.tk_abteilung) return "TK, jeweils am Vorabend im Kühlschrank auftauen";
    var teile = ["frisch: bis " + ddmm(plusTage(termin, frisch[2])) + " verbrauchen"];
    var einfr = ns.filter(function (n) { return n.einfrieren; });
    if (einfr.length) {
      teile.push("davon " + gramm(einfr.reduce(function (s, n) { return s + n.g; }, 0)) + " am Einkaufstag portionsweise einfrieren (" +
        einfr.map(function (n) { return n.wofuer.split(":")[0]; }).join(", ") + ")");
    }
    return teile.join("; ");
  }
  function kosten(listen) {
    var gekauft = [];
    listen.forEach(function (l) { l.zeilen.forEach(function (z) { if (z.pakete) gekauft.push(z); }); });
    var woche = 0, verbrauch = 0, vorrat = 0;
    gekauft.forEach(function (z) {
      if (z.vorratskauf) { vorrat += z.kosten; return; }
      woche += z.kosten;
      verbrauch += Math.min(z.bedarf - z.aus_bestand, z.pakete * z.packung[1]) / z.packung[1] * z.kosten / z.pakete;
    });
    return { woche: woche, verbrauch: verbrauch, reste: woche - verbrauch, vorrat: vorrat };
  }

  // --- Plandatei (Format wie tools/planer.py → eintrag_text) -------------------------------------------
  function wert(v) {
    if (typeof v === "boolean") return v ? "true" : "false";
    if (typeof v === "string" && /[ :=;]/.test(v)) return '"' + v.replace(/"/g, "'") + '"';
    return String(v);
  }
  function eintragText(m) {
    var teile = [["rezept", m.r]];
    if (m.rest) teile.push(["rest_von", m.rest]); else teile.push(["kochen", true]);
    if (m.faktor !== 1) teile.push(["faktor", m.faktor]);
    if (m.ladungen > 1) teile.push(["ladungen", m.ladungen]);
    if (m.kochen && m.gekocht_am !== m.datum) teile.push(["gekocht_am", m.gekocht_am]);
    if (m.kochen && m.einfrieren) teile.push(["einfrieren", true]);
    if (m.box) teile.push(["box", true]);
    if (m.notiz) teile.push(["notiz", m.notiz]);
    return "{" + teile.map(function (t) { return t[0] + ": " + wert(t[1]); }).join(", ") + "}";
  }
  function planYaml(a, e, w) {
    var z = ["# Wochenplan KW " + w.kw + "/" + w.jahr + " – im Baukasten der App zusammengestellt (" + HEUTE + ")",
      "quelle: baukasten", "kw: " + w.kw, "jahr: " + w.jahr, "einkauf:"];
    w.einkauf.forEach(function (t, i) { z.push("  - {tag: " + wtag(t) + ", datum: " + t + ", art: " + (w.einkauf_art[i] || "gross") + "}"); });
    z.push("tage:");
    w.tage.forEach(function (iso) {
      z.push("  - datum: " + iso);
      SLOTS.forEach(function (s) { var m = a.idx[iso + "/" + s]; z.push("    " + s + ": " + (m ? eintragText(m) : "null")); });
      z.push("    auswaerts: " + (e.auswaerts[iso] ? "{mahlzeit: " + e.auswaerts[iso] + "}" : "null"));
    });
    return z.join("\n") + "\n";
  }
  function speichernUrl(text) {
    var stempel = new Date().toISOString().replace(/[-:]/g, "").replace("T", "-").slice(0, 15);
    return "https://github.com/" + D.github + "/new/main?filename=" + encodeURIComponent("daten/baukasten/" + W.name + "-" + stempel + ".yaml") +
      "&value=" + encodeURIComponent(text);
  }

  // --- Bearbeiten ----------------------------------------------------------------------------------------
  function doppeltZiel(iso, slot) {   // planer.struktur: Abend → Mittag am Folgetag, vor der Tagschicht Mittag → Abend
    var i = W.tage.indexOf(iso);
    if (i < 0 || i + 1 >= W.tage.length) return null;
    var morgen = W.tage[i + 1], uebermorgen = W.tage[i + 2];
    if (slot === "abend" && !(uebermorgen && SCHICHT[uebermorgen] === "Tag") && E.auswaerts[morgen] !== "mittag") return morgen + "/mittag";
    if (slot === "mittag" && SCHICHT[morgen] === "Tag" && E.auswaerts[morgen] !== "abend") return morgen + "/abend";
    return null;
  }
  function restOptionen(e, iso, slot) {   // Koch-Einträge vorher mit freier Ladung, noch haltbar
    var a = ableiten(e, W), ziel = iso + "/" + slot, out = [];
    a.liste.forEach(function (m) {
      if (!m.kochen || m.key === ziel || GRUPPE[m.slot] !== GRUPPE[slot] || m.datum > iso) return;
      if (m.kinder.length + 1 >= R.max_ladungen) return;
      if (tageZwischen(m.gekocht_am, iso) > REZ[m.r].tage) return;
      if (W.tage.indexOf(m.datum) * 4 + SLOTS.indexOf(m.slot) >= W.tage.indexOf(iso) * 4 + SLOTS.indexOf(slot)) return;
      out.push(m);
    });
    return out;
  }
  function waehlen(e, iso, slot, rid, doppelt) {
    var alt = eintrag(e, iso, slot);
    if (e.auswaerts[iso] === slot) delete e.auswaerts[iso];
    // gleiches Rezept vorher mit freier Ladung und haltbar → als Rest verplanen
    var rest = restOptionen(e, iso, slot).filter(function (m) { return m.r === rid; })[0];
    setzen(e, iso, slot, { r: rid, f: null, rest: rest ? rest.key : null });
    if (alt && !alt.rest) {   // Reste des alten Gerichts folgen dem neuen
      kinderVon(e, iso + "/" + slot).forEach(function (k) { setzen(e, k[0], k[1], { r: rid, f: null, rest: iso + "/" + slot }); });
    }
    if (doppelt && !rest) {
      var z = doppeltZiel(iso, slot);
      if (z && !eintrag(e, z.split("/")[0], z.split("/")[1])) setzen(e, z.split("/")[0], z.split("/")[1], { r: rid, f: null, rest: iso + "/" + slot });
    }
  }
  function kinderVon(e, key) {
    var out = [];
    Object.keys(e.tage).forEach(function (iso) {
      SLOTS.forEach(function (s) { var x = e.tage[iso][s]; if (x && x.rest === key) out.push([iso, s]); });
    });
    return out;
  }
  function leeren(e, iso, slot) {
    var key = iso + "/" + slot;
    kinderVon(e, key).forEach(function (k) { setzen(e, k[0], k[1], null); });
    setzen(e, iso, slot, null);
    if (e.auswaerts[iso] === slot) delete e.auswaerts[iso];
  }
  function alsRest(e, iso, slot, quelle) {
    var q = quelle.split("/"), x = eintrag(e, q[0], q[1]);
    leeren(e, iso, slot);
    setzen(e, iso, slot, { r: x.r, f: null, rest: quelle });
  }
  function auswaerts(e, iso, slot) {
    leeren(e, iso, slot);
    if (e.auswaerts[iso]) leeren(e, iso, e.auswaerts[iso]);
    e.auswaerts[iso] = slot;
  }
  function faktorAendern(e, iso, slot, schritt) {
    var a = ableiten(e, W), m = a.idx[iso + "/" + slot];
    if (!m) return;
    if (m.rest) m = a.idx[m.rest];
    var F = R.faktoren, i = F.indexOf(m.faktor), neu = F[Math.max(0, Math.min(F.length - 1, (i < 0 ? F.indexOf(1) : i) + schritt))];
    var x = eintrag(e, m.datum, m.slot);
    x.f = neu;
  }

  // Bewertung eines Kandidaten für einen Platz (Sortierung und Auffüllen)
  function regelHinweise(e, a, iso, slot, rid) {
    var r = REZ[rid], h = [];
    if (slot === "abend") {
      [plusTage(iso, -1), plusTage(iso, 1)].forEach(function (t) {
        var ab = a.idx[t + "/abend"];
        if (!ab || e.auswaerts[t]) return;
        var o = REZ[ab.r];
        if (o.kueche === r.kueche) h.push((t < iso ? "gestern" : "morgen") + " Abend schon " + r.kueche);
        else if (r.quelle && o.quelle === r.quelle) h.push((t < iso ? "gestern" : "morgen") + " Abend schon " + (R.protein_gruppen[r.quelle] || r.quelle));
      });
    }
    var n = 0;
    a.liste.forEach(function (m) {
      if (m.r !== rid || m.key === iso + "/" + slot) return;
      if (HAUPT.indexOf(slot) >= 0 && m.kochen && HAUPT.indexOf(m.slot) >= 0) n++;
      if ((slot === "fruehstueck" || slot === "snack") && m.slot === slot) n++;
    });
    if (HAUPT.indexOf(slot) >= 0 && n >= R.haupt_max_kochen) h.push("schon " + n + "× gekocht");
    var max = slot === "fruehstueck" ? R.fruehstueck_max_tage : R.snack_max_tage;
    if ((slot === "fruehstueck" || slot === "snack") && n >= max) h.push("schon " + n + "× als " + slotName(slot));
    if (r.sterne === 3) {
      var drei = {};
      a.liste.forEach(function (m) { if (REZ[m.r].sterne === 3 && m.key !== iso + "/" + slot) drei[m.r] = 1; });
      if (!drei[rid] && Object.keys(drei).length >= R.drei_sterne_max) h.push("3-Sterne-Limit erreicht");
    }
    return h;
  }
  function kandidaten(e, iso, slot, mitRest) {
    var a0 = ableiten(e, W), basisKosten = einkaufListe(a0, W).kosten.woche;
    var doppelt = HAUPT.indexOf(slot) >= 0 ? doppeltZiel(iso, slot) : null;
    if (doppelt && eintrag(e, doppelt.split("/")[0], doppelt.split("/")[1])) doppelt = null;
    var out = [];
    Object.keys(REZ).forEach(function (id) {
      var r = REZ[id];
      if (!passtZuSlot(r, slot) || aussortiert(r)) return;
      var e2 = kopie(e);
      waehlen(e2, iso, slot, id, !!doppelt);
      var a = ableiten(e2, W), m = a.idx[iso + "/" + slot];
      var s = tagSumme(a.liste, e2, iso), voll = !offeneSlots(e2, iso).length;
      var p = strafe(mitErwartung(s, e2, iso));
      var regeln = regelHinweise(e, a0, iso, slot, id);
      var mehr = einkaufListe(a, W).kosten.woche - basisKosten;   // was der Einkauf dadurch mehr kostet
      out.push({ id: id, r: r, faktor: m ? m.faktor : 1, summe: s, voll: voll, status: tagStatus(s), regeln: regeln, mehrkosten: mehr,
                 wert: p + regeln.length * G.regel + mehr * G.kosten - (r.sterne >= 4 ? G.packung : 0) });
    });
    out.sort(function (x, y) { return x.wert - y.wert || (x.r.name < y.r.name ? -1 : 1); });
    var reste = mitRest ? restOptionen(e, iso, slot) : [];
    return { liste: out, reste: reste, doppelt: doppelt };
  }
  function wochenWert(e) {   // Summe der Tagesstrafen (volle Tage) + Regelverstöße
    var a = ableiten(e, W), p = 0;
    W.tage.forEach(function (iso) { if (!gesperrt(iso)) p += strafe(mitErwartung(tagSumme(a.liste, e, iso), e, iso)); });
    return p + wochenHinweise(a, e, W).length * G.regel;
  }
  function auffuellen(e) {
    var gefuellt = [];
    W.tage.forEach(function (iso) {
      if (gesperrt(iso)) return;
      SLOTS.forEach(function (slot) {
        if (eintrag(e, iso, slot) || e.auswaerts[iso] === slot) return;
        var k = kandidaten(e, iso, slot, true), a0 = ableiten(e, W);
        var bester = k.liste.filter(function (c) { return !c.regeln.length; })[0] || k.liste[0];
        var rest = k.reste.filter(function (m) { return !regelHinweise(e, a0, iso, slot, m.r).length; })[0];
        if (rest) {   // Rest verplanen, wenn der Tag damit mindestens so gut passt (spart Einkauf)
          var e2 = kopie(e); alsRest(e2, iso, slot, rest.key);
          var a2 = ableiten(e2, W), pr = strafe(mitErwartung(tagSumme(a2.liste, e2, iso), e2, iso));
          if (!bester || pr <= bester.wert + G.packung) { alsRest(e, iso, slot, rest.key); gefuellt.push([iso, slot]); return; }
        }
        if (bester) { waehlen(e, iso, slot, bester.id, !!k.doppelt); gefuellt.push([iso, slot]); }
      });
    });
    // Verbessern: aufgefüllte Koch-Plätze gegen die besten Alternativen tauschen, solange die Woche besser wird
    for (var runde = 0; runde < 2; runde++) {
      var besser = false;
      gefuellt.forEach(function (x) {
        var jetzt = eintrag(e, x[0], x[1]);
        if (!jetzt || jetzt.rest) return;
        var wert = wochenWert(e);
        kandidaten(e, x[0], x[1], false).liste.slice(0, 10).forEach(function (c) {
          if (c.id === eintrag(e, x[0], x[1]).r) return;
          var e2 = kopie(e); waehlen(e2, x[0], x[1], c.id, false);
          var w2 = wochenWert(e2);
          if (w2 < wert - 1e-6) { e.tage = e2.tage; e.auswaerts = e2.auswaerts; wert = w2; besser = true; }
        });
      });
      if (!besser) break;
    }
    return gefuellt.length;
  }

  // --- Anzeige ---------------------------------------------------------------------------------------------
  var A = null;   // aktuelle Ableitung
  function makroBalken(s) {
    var z = R.ziele, teile = [["kcal", "kcal", ""], ["protein", "P", " g"], ["fett", "F", " g"], ["kh", "KH", " g"]];
    return el("div", { class: "bk-makros" }, teile.map(function (t) {
      var anteil = Math.min(1.25, s[t[0]] / z[t[0]]);
      return el("div", { class: "bk-makro bk-m-" + t[0] }, [
        el("span", { class: "bk-ml", text: t[1] + " " + zahl(s[t[0]], 0) + t[2] }),
        el("span", { class: "bk-spur" }, [el("span", { class: "bk-fuell", style: "width:" + Math.round(anteil * 80) + "%" }),
          el("span", { class: "bk-ziel", style: "left:80%" })])]);
    }));
  }
  function zeichnen() {
    A = ableiten(E, W);
    wurzel.innerHTML = "";
    // Wochenwahl
    var wahl = el("div", { class: "knopfreihe bk-wochen" });
    [aktuell, naechste].concat([aktuell, naechste].indexOf(W) < 0 ? [W] : []).forEach(function (w) {
      if (!w) return;
      var a = el("a", { class: "knopf" + (w === W ? " primaer" : ""), href: "?woche=" + w.name + (PARAM.get("heute") ? "&heute=" + PARAM.get("heute") : ""),
                        text: (w === aktuell ? "Diese Woche" : w === naechste ? "Nächste Woche" : "Woche") + " · KW " + w.kw });
      wahl.appendChild(a);
    });
    wurzel.appendChild(wahl);
    var info = "KW " + W.kw + " · " + ddmm(W.tage[0]) + "–" + ddmm(W.tage[6]) + " · Einkauf " + W.einkauf.map(function (t) { return wtag(t) + " " + ddmm(t); }).join(", ");
    wurzel.appendChild(el("p", { class: "leise", text: info + (E.basis === "plan" ? " · gespeicherter Plan geladen" : "") +
      (E.gespeichert ? " · auf GitHub gespeichert, wird in 1–2 Minuten übernommen" : "") }));
    // Wochenleiste
    var leiste = el("div", { class: "wochenleiste", role: "navigation", "aria-label": "Tage" });
    W.tage.forEach(function (iso) {
      var s = SCHICHT[iso];
      leiste.appendChild(el("a", { class: "wtag s-" + s.toLowerCase(), href: "#bk-" + iso }, [
        el("span", { class: "wt", text: wtag(iso) }), el("span", { class: "dz", text: String(Number(iso.slice(8))) }),
        el("span", { class: "ic", "aria-label": R.schicht_name[s], text: R.schicht_icon[s] }),
        el("span", { class: "ex", text: tagStatus(tagSumme(A.liste, E, iso)).ok && !offeneSlots(E, iso).length ? "✓" : "" })]));
    });
    wurzel.appendChild(leiste);
    // Tage
    W.tage.forEach(function (iso) { wurzel.appendChild(tagKarte(iso)); });
    // Hinweise
    var h = wochenHinweise(A, E, W);
    if (h.length) wurzel.appendChild(el("section", { class: "karte bk-hinweise" }, [el("h2", { text: "Hinweise" }),
      el("ul", {}, h.map(function (t) { return el("li", { text: t }); })), el("p", { class: "leise", text: "Nur Hinweise – du entscheidest." })]));
    // Aktionen oben, schmale Leiste unten (Kosten + Festlegen), Rest am Ende
    var ek = einkaufListe(A, W), k = ek.kosten, budget = speicherBudget(), fehler = strukturFehler(A), leer = 0;
    W.tage.forEach(function (iso) { if (!gesperrt(iso)) leer += offeneSlots(E, iso).length; });
    var aktionen = el("div", { class: "knopfreihe bk-aktionen" }, [
      el("button", { type: "button", id: "bk-auffuellen", text: "✨ Rest auffüllen" + (leer ? " (" + leer + ")" : "") }),
      el("button", { type: "button", id: "bk-einkauf", text: "🛒 Einkaufsliste" })]);
    wurzel.insertBefore(aktionen, leiste.nextSibling);
    aktionen.querySelector("#bk-auffuellen").disabled = !leer;
    aktionen.querySelector("#bk-auffuellen").addEventListener("click", function () {
      var b = this; b.disabled = true; b.textContent = "⏳ rechnet …";
      setTimeout(function () { auffuellen(E); sichern(); zeichnen(); }, 30);
    });
    aktionen.querySelector("#bk-einkauf").addEventListener("click", function () { einkaufZeigen(ek); });
    var unten = el("div", { class: "bk-leiste" }, [
      el("div", { class: "bk-kosten", html: "<strong>" + euro(k.woche) + "</strong>" + (budget ? " / " + euro(budget) : "") +
        "<br><span class=\"leise\">" + (leer ? leer + " Plätze frei" : "alle Plätze belegt") + "</span>" }),
      el("button", { type: "button", class: "primaer", id: "bk-speichern", text: "💾 Woche festlegen" })]);
    var sp = unten.querySelector("#bk-speichern");
    sp.disabled = !A.liste.length || !!fehler.length || !D.github;
    sp.addEventListener("click", function () {
      var url = speichernUrl(planYaml(A, E, W));
      E.gespeichert = new Date().toISOString(); sichern();
      location.href = url;
    });
    var ende = el("section", { class: "karte" }, [
      el("p", { class: "bk-kosten", html: "Einkauf <strong>" + euro(k.woche) + "</strong> · davon diese Woche verbraucht " + euro(k.verbrauch) +
        " · Reste " + euro(k.reste) + (k.vorrat ? " · Vorratskäufe " + euro(k.vorrat) : "") + (budget ? " · Budget " + euro(budget) : "") }),
      fehler.length ? el("p", { class: "warn", text: "Vor dem Festlegen beheben: " + fehler.join(" · ") }) : null,
      el("p", { class: "leise", text: "„Woche festlegen“ öffnet GitHub mit der fertigen Plandatei – dort „Commit changes“ tippen. " +
        "Nach 1–2 Minuten zeigen Heute, Woche und Einkauf die neue Woche." + (leer ? " Leere Plätze bleiben leer." : "") }),
      el("div", { class: "knopfreihe" }, [el("button", { type: "button", id: "bk-verwerfen", text: "↺ Entwurf verwerfen" })]),
      el("details", {}, [el("summary", { text: "Vorschau der Plandatei" }), el("pre", { id: "bk-yaml", text: planYaml(A, E, W) })])]);
    wurzel.appendChild(ende);
    wurzel.appendChild(unten);
    ende.querySelector("#bk-verwerfen").addEventListener("click", function () {
      if (!window.confirm("Entwurf verwerfen und " + (W.plan ? "den gespeicherten Plan" : "eine leere Woche") + " laden?")) return;
      speicher(schluessel(W), null); E = ausPlan(W.name) || leererEntwurf(); zeichnen();
    });
  }
  function speicherBudget() {
    var b = speicher("budget");
    return typeof b === "number" && b >= 0 ? b : D.budget;
  }
  function tagKarte(iso) {
    var s = SCHICHT[iso], zu = gesperrt(iso), summe = tagSumme(A.liste, E, iso), st = tagStatus(summe), offen = offeneSlots(E, iso);
    var marken = [];
    if (W.einkauf.indexOf(iso) >= 0) marken.push(el("span", { class: "marke", text: "🛒 Einkauf" }));
    var vorkochen = A.liste.filter(function (m) { return m.kochen && m.gekocht_am === iso && m.datum !== iso; });
    if (vorkochen.length) marken.push(el("span", { class: "marke", text: "🍱 Meal Prep" }));
    var karte = el("section", { class: "karte tag bk-tag s-" + s.toLowerCase() + (zu ? " gesperrt" : ""), id: "bk-" + iso }, [
      el("div", { class: "band" }, [el("span", { html: R.schicht_icon[s] + " <strong>" + wtagLang(iso) + ", " + ddmm(iso) + "</strong> · " +
        R.schicht_name[s] + (R.schichtzeiten[s] ? " " + R.schichtzeiten[s] : "") + (zu ? " · 🔒 vorbei" : "") })].concat(marken))]);
    var plaetze = el("div", { class: "bk-plaetze" });
    SLOTS.forEach(function (slot) { plaetze.appendChild(platz(iso, slot, zu)); });
    karte.appendChild(plaetze);
    karte.appendChild(makroBalken(summe));
    karte.appendChild(el("p", { class: "bk-status " + (offen.length ? "leise" : st.ok ? "ok" : "warn"),
      text: offen.length ? offen.length + " Platz/Plätze frei" + (st.probleme.length ? " · " + st.probleme[0] : "") : st.ok ? "✓ Tag im Ziel" : "⚠️ " + st.probleme.join(" · ") }));
    return karte;
  }
  function platz(iso, slot, zu) {
    var m = A.idx[iso + "/" + slot], aus = E.auswaerts[iso] === slot;
    var knopf = el("button", { type: "button", class: "bk-platz" + (m ? " voll" : "") + (aus ? " auswaerts" : ""), "data-platz": iso + "/" + slot });
    knopf.appendChild(el("span", { class: "slot", text: R.slot_icon[slot] + " " + slotName(slot) }));
    if (aus) {
      knopf.appendChild(el("span", { class: "name", text: "🍴 Auswärts" }));
      knopf.appendChild(el("span", { class: "werte", text: "Platzhalter " + zahl(R.auswaerts.kcal, 0) + " kcal" }));
    } else if (m) {
      var r = REZ[m.r], p = r.p, sym = (m.box ? "📦 " : "") + (m.rest ? "↻ " : "") + (m.einfrieren ? "❄️ " : "");
      knopf.appendChild(el("span", { class: "name", text: r.name }));
      knopf.appendChild(el("span", { class: "werte", text: sym + zahl(p.kcal * m.faktor, 0) + " kcal · " + zahl(p.protein * m.faktor, 0) + " g P" +
        (m.faktor !== 1 ? " · ×" + zahl(m.faktor, 2) : "") + (m.auto && m.faktor !== 1 ? " (auto)" : "") }));
      var hinweis = m.rest ? "Rest von " + wtag(m.rest.split("/")[0]) + " " + slotName(m.rest.split("/")[1]) :
        m.gekocht_am !== m.datum ? "vorbereitet am " + wtag(m.gekocht_am) : m.notiz || (m.ladungen > 1 ? m.ladungen + " Ladungen" : "");
      if (hinweis) knopf.appendChild(el("span", { class: "mhinweis", text: hinweis }));
      m.fehler.forEach(function (f) { knopf.appendChild(el("span", { class: "mhinweis warn", text: "⚠️ " + f })); });
    } else {
      knopf.appendChild(el("span", { class: "name leise", text: zu ? "–" : "＋ wählen" }));
    }
    if (zu) knopf.disabled = true;
    else knopf.addEventListener("click", function () { auswahl(iso, slot); });
    if (!m || zu || aus) return knopf;
    var reihe = el("div", { class: "bk-platzreihe" }, [knopf, el("div", { class: "bk-faktor" }, [
      el("button", { type: "button", "aria-label": "Portion kleiner", text: "–", "data-schritt": "-1" }),
      el("button", { type: "button", "aria-label": "Portion größer", text: "＋", "data-schritt": "1" })])]);
    reihe.querySelectorAll(".bk-faktor button").forEach(function (b) {
      b.addEventListener("click", function () { faktorAendern(E, iso, slot, +b.getAttribute("data-schritt")); sichern(); zeichnen(); });
    });
    return reihe;
  }

  // Auswahl-Fenster
  function auswahl(iso, slot) {
    var k = kandidaten(E, iso, slot, true), x = eintrag(E, iso, slot);
    var dlg = el("div", { class: "bk-fenster", role: "dialog", "aria-modal": "true", "aria-label": slotName(slot) + " " + wtagLang(iso) });
    var innen = el("div", { class: "bk-fenster-innen" });
    dlg.appendChild(innen);
    innen.appendChild(el("div", { class: "bk-fenster-kopf" }, [el("h2", { text: R.slot_icon[slot] + " " + slotName(slot) + " · " + wtagLang(iso) + " " + ddmm(iso) }),
      el("button", { type: "button", class: "bk-zu", "aria-label": "Schließen", text: "✕" })]));
    var doppelt = null;
    if (k.doppelt) {
      var z = k.doppelt.split("/");
      doppelt = el("input", { type: "checkbox", id: "bk-doppelt", checked: "checked" });
      innen.appendChild(el("label", { class: "haken bk-doppelt" }, [doppelt, "Doppelt kochen → auch " + slotName(z[1]) + " " + wtag(z[0])]));
    }
    var jetzt = A.idx[iso + "/" + slot];
    if (jetzt) innen.appendChild(el("p", { class: "leise", text: "Aktuell: " + REZ[jetzt.r].name + (jetzt.rest ? " (Rest)" : "") }));
    var oben = el("ul", { class: "bk-optionen" });
    k.reste.forEach(function (m) {
      oben.appendChild(el("li", {}, [el("button", { type: "button", class: "bk-option rest", "data-rest": m.key,
        text: "↻ Rest von " + wtag(m.datum) + " " + slotName(m.slot) + ": " + REZ[m.r].name })]));
    });
    if (HAUPT.indexOf(slot) >= 0) oben.appendChild(el("li", {}, [el("button", { type: "button", class: "bk-option", "data-aktion": "auswaerts", text: "🍴 Auswärts essen" })]));
    if (x || E.auswaerts[iso] === slot) oben.appendChild(el("li", {}, [el("button", { type: "button", class: "bk-option", "data-aktion": "leer", text: "Leer lassen" })]));
    innen.appendChild(oben);
    var suche = el("input", { type: "search", class: "bk-suche", placeholder: "Suchen: Name, Zutat oder Küche", "aria-label": "Rezepte durchsuchen" });
    innen.appendChild(suche);
    var liste = el("ul", { class: "bk-kandidaten" });
    innen.appendChild(liste);
    function fuellen() {
      var q = suche.value.trim().toLowerCase();
      liste.innerHTML = "";
      k.liste.forEach(function (c) {
        var text = (c.r.name + " " + c.r.kueche + " " + c.r.zutaten.map(function (z) { return z[0]; }).join(" ")).toLowerCase();
        if (q && text.indexOf(q) < 0) return;
        var marken = [];
        if (c.voll) marken.push(el("span", { class: c.status.ok ? "ok" : "warn", text: c.status.ok ? "✓ Tag im Ziel" : "⚠️ " + c.status.probleme[0] }));
        c.regeln.forEach(function (t) { marken.push(el("span", { class: "warn", text: t })); });
        if (c.r.sterne >= 4) marken.push(el("span", { text: "★ " + c.r.sterne }));
        marken.push(el("span", { class: "bk-mehr", text: "💶 " + (c.mehrkosten < 0.005 ? "nichts extra (alles da)" : "+" + euro(c.mehrkosten) + " Einkauf") }));
        if (c.r.eigen) marken.push(el("span", { text: "✍️ eigenes" }));
        liste.appendChild(el("li", {}, [el("button", { type: "button", class: "bk-kandidat", "data-id": c.id }, [
          el("span", { class: "name", text: c.r.name }),
          el("span", { class: "werte", text: "+" + zahl(c.r.p.kcal * c.faktor, 0) + " kcal · +" + zahl(c.r.p.protein * c.faktor, 0) + " g P" +
            (c.faktor !== 1 ? " · ×" + zahl(c.faktor, 2) : "") + " · " + (R.kueche_icon[c.r.kueche] || "") + " " + c.r.kueche + " · ⏱ " + c.r.zeit + " min" }),
          el("span", { class: "bk-marken" }, marken)])]));
      });
    }
    fuellen();
    suche.addEventListener("input", fuellen);
    function zu() { dlg.remove(); document.body.classList.remove("bk-offen"); }
    dlg.addEventListener("click", function (ev) {
      var t = ev.target.closest("button");
      if (ev.target === dlg || (t && t.classList.contains("bk-zu"))) { zu(); return; }
      if (!t) return;
      if (t.hasAttribute("data-id")) waehlen(E, iso, slot, t.getAttribute("data-id"), doppelt ? doppelt.checked : false);
      else if (t.hasAttribute("data-rest")) alsRest(E, iso, slot, t.getAttribute("data-rest"));
      else if (t.getAttribute("data-aktion") === "auswaerts") auswaerts(E, iso, slot);
      else if (t.getAttribute("data-aktion") === "leer") leeren(E, iso, slot);
      else return;
      sichern(); zu(); zeichnen();
    });
    document.body.appendChild(dlg);
    document.body.classList.add("bk-offen");
  }

  // Einkaufsliste als Fenster
  function einkaufZeigen(ek) {
    var dlg = el("div", { class: "bk-fenster", role: "dialog", "aria-modal": "true", "aria-label": "Einkaufsliste" });
    var innen = el("div", { class: "bk-fenster-innen", id: "bk-einkaufsliste" });
    dlg.appendChild(innen);
    innen.appendChild(el("div", { class: "bk-fenster-kopf" }, [el("h2", { text: "🛒 Einkaufsliste KW " + W.kw }),
      el("button", { type: "button", class: "bk-zu", "aria-label": "Schließen", text: "✕" })]));
    innen.appendChild(el("p", { class: "leise", text: "Live aus deiner Auswahl. Nach „Woche festlegen“ steht sie im Tab Einkauf." }));
    ek.listen.forEach(function (l) {
      innen.appendChild(el("h3", { text: "Einkauf " + wtagLang(l.datum) + ", " + ddmm(l.datum) }));
      var kaufen = l.zeilen.filter(function (z) { return z.pakete > 0; });
      var abt = R.abteilungen.slice();
      kaufen.forEach(function (z) { var a = z.packung ? z.packung[0] : "Sonstiges"; if (abt.indexOf(a) < 0) abt.push(a); });
      abt.forEach(function (a) {
        var teil = kaufen.filter(function (z) { return (z.packung ? z.packung[0] : "Sonstiges") === a; }).sort(function (x, y) { return x.zutat < y.zutat ? -1 : 1; });
        if (!teil.length) return;
        innen.appendChild(el("h4", { text: (R.abt_icon[a] || "📦") + " " + a }));
        innen.appendChild(el("ul", { class: "liste bk-liste" }, teil.map(function (z) {
          var menge = z.pakete === 1 ? z.packung[2] : z.pakete + " × " + z.packung[2];
          return el("li", { "data-zutat": z.zutat }, [el("span", {}, [
            el("span", { class: "titel" }, [el("strong", { text: z.zutat }), " · " + menge + (z.packung[3] !== null ? " · ca. " + euro(z.kosten) : "")]),
            el("div", { class: "detail", text: "Bedarf " + gramm(z.bedarf) + (z.aus_bestand > EPS ? " (davon " + gramm(z.aus_bestand) + " schon da)" : "") + " · " + z.wofuer.join("; ") }),
            z.hinweis ? el("div", { class: "detail warn", text: "⚠️ " + z.hinweis }) : null])]);
        })));
      });
      var vorrat = l.zeilen.filter(function (z) { return z.pakete === 0; });
      if (vorrat.length) innen.appendChild(el("p", { class: "leise", text: "Aus dem Vorrat: " + vorrat.map(function (z) { return z.zutat + " " + gramm(z.bedarf); }).join(", ") }));
    });
    var k = ek.kosten;
    innen.appendChild(el("p", { class: "bk-kosten", html: "Einkauf ca. <strong>" + euro(k.woche) + "</strong> · davon diese Woche verbraucht " + euro(k.verbrauch) +
      " · Reste " + euro(k.reste) + (k.vorrat ? " · Vorratskäufe " + euro(k.vorrat) : "") }));
    var reste = Object.keys(ek.reste).sort();
    if (reste.length) innen.appendChild(el("p", { class: "leise", text: "Reste nach der Woche: " + reste.map(function (z) { return z + " " + gramm(ek.reste[z].g); }).join(", ") }));
    dlg.addEventListener("click", function (ev) {
      if (ev.target === dlg || ev.target.classList.contains("bk-zu")) { dlg.remove(); document.body.classList.remove("bk-offen"); }
    });
    document.body.appendChild(dlg);
    document.body.classList.add("bk-offen");
  }

  if (!W) {
    wurzel.appendChild(el("p", { class: "hinweis", text: "Für diese Woche liegen noch keine Daten vor – die App wird beim nächsten Veröffentlichen aktualisiert." }));
    return;
  }
  zeichnen();
  // für Tests: Ableitung, Einkauf und Plandatei von außen abrufbar
  window.BAUKASTEN_API = {
    woche: function () { return W.name; },
    ableitung: function () {
      return ableiten(E, W).liste.map(function (m) {
        return { key: m.key, r: m.r, faktor: m.faktor, kochen: m.kochen, rest: m.rest, ladungen: m.ladungen, gekocht_am: m.gekocht_am,
                 box: m.box, einfrieren: m.einfrieren, notiz: m.notiz };
      });
    },
    tage: function () { var a = ableiten(E, W); return W.tage.map(function (iso) { return tagSumme(a.liste, E, iso); }); },
    einkauf: function () {
      var ek = einkaufListe(ableiten(E, W), W);
      return { listen: ek.listen.map(function (l) { return { datum: l.datum, zeilen: l.zeilen.map(function (z) {
        return { zutat: z.zutat, bedarf: z.bedarf, aus_bestand: z.aus_bestand, pakete: z.pakete, kosten: z.kosten, hinweis: z.hinweis, wofuer: z.wofuer }; }) }; }),
        reste: ek.reste, kosten: ek.kosten };
    },
    yaml: function () { return planYaml(ableiten(E, W), E, W); },
    url: function () { return speichernUrl(planYaml(ableiten(E, W), E, W)); }
  };
})();
