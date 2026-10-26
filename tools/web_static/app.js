/* Rezeptbuch – Web-App (generiert aus tools/web_static/app.js). Vanilla JS, keine Abhängigkeiten. */
(function () {
  "use strict";
  var D = window.REZEPTBUCH || { rezepte: [], plaene: [], ziele: {} };
  var basis = document.body.getAttribute("data-basis") || "";

  // --- Hilfen ------------------------------------------------------------------
  function zahl(x, nk) {
    nk = nk === undefined ? 1 : nk;
    var s = Number(x).toLocaleString("de-DE", { minimumFractionDigits: 0, maximumFractionDigits: nk });
    return s;
  }
  function euro(x) { return Number(x).toLocaleString("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €"; }
  function budgetWert() { var b = speicher("budget"); return typeof b === "number" && b >= 0 ? b : D.budget; }
  function gramm(g) { return zahl(g, g >= 10 ? 0 : 1) + " g"; }
  var BRUECHE = { "½": 0.5, "⅓": 1 / 3, "⅔": 2 / 3, "¼": 0.25, "¾": 0.75 };
  function bruchText(v) {
    var ganz = Math.floor(v + 1e-9), rest = v - ganz, zeichen = "";
    var kandidaten = [[0, ""], [0.25, "¼"], [1 / 3, "⅓"], [0.5, "½"], [2 / 3, "⅔"], [0.75, "¾"], [1, ""]];
    var best = kandidaten[0];
    kandidaten.forEach(function (k) { if (Math.abs(rest - k[0]) < Math.abs(rest - best[0])) best = k; });
    if (best[0] === 1) { ganz += 1; } else { zeichen = best[1]; }
    return (ganz > 0 ? String(ganz) : (zeichen ? "" : "0")) + zeichen;
  }
  // „2 Eier Gr. M“ × 1,5 → „3 Eier Gr. M“; ohne führende Zahl bleibt der Text
  function skaliereAnzeige(anz, f) {
    if (f === 1) return anz;
    var m = anz.match(/^(ca\. )?(\d+)?([½⅓⅔¼¾])?(\s|$)/);
    if (!m || (!m[2] && !m[3])) return anz;
    var wert = (m[2] ? parseInt(m[2], 10) : 0) + (m[3] ? BRUECHE[m[3]] : 0);
    return (m[1] || "") + bruchText(wert * f) + anz.slice(m[0].length - m[4].length);
  }
  function speicher(key, wert) {
    try {
      if (wert === undefined) { var v = window.localStorage.getItem(key); return v ? JSON.parse(v) : null; }
      window.localStorage.setItem(key, JSON.stringify(wert));
    } catch (e) { /* privater Modus o. Ä.: nur im Speicher */ }
    return null;
  }
  function meldung(text) {
    var el = document.createElement("div");
    el.className = "meldung"; el.setAttribute("role", "status"); el.textContent = text;
    document.body.appendChild(el);
    setTimeout(function () { el.remove(); }, 2200);
  }
  function heuteIso() {
    var p = new URLSearchParams(location.search).get("datum");
    if (p && /^\d{4}-\d{2}-\d{2}$/.test(p)) return p;
    try { return new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Berlin" }); }
    catch (e) { return new Date().toISOString().slice(0, 10); }
  }
  function datumDe(iso) { var t = iso.split("-"); return t[2] + "." + t[1] + "." + t[0]; }
  var WOCHENTAGE = ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"];
  function el(tag, attrs, kinder) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") e.textContent = attrs[k]; else if (k === "html") e.innerHTML = attrs[k]; else e.setAttribute(k, attrs[k]);
    });
    (kinder || []).forEach(function (c) { if (c) e.appendChild(c); });
    return e;
  }

  // --- Service Worker -------------------------------------------------------------
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register(basis + "sw.js").catch(function () { /* offline-Funktion optional */ });
    });
  }

  var SCHICHT = { Tag: ["☀️", "Tagschicht"], Nacht: ["🌙", "Nachtschicht"], frei: ["🏠", "frei"] };
  var SVGNS = "http://www.w3.org/2000/svg";
  function svgEl(tag, attrs) {
    var e = document.createElementNS(SVGNS, tag);
    Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }
  // Ring: Ist-Wert als Bogen (Makrofarbe), Zielbereich als dünner grauer Außenbogen, Zahl + Einheit in der Mitte
  function ring(k, label, einheit, ist, soll, band) {
    var lo = band[0], hi = band[1], max = (hi || soll * 1.1) * 1.15, gr = 92, r = 34, u = 2 * Math.PI * r;
    var ok = ist >= lo && (hi === null || ist <= hi);
    var svg = svgEl("svg", { viewBox: "0 0 " + gr + " " + gr, width: gr, height: gr, role: "img",
      "aria-label": label + " " + zahl(ist, 0) + " " + einheit + (ok ? ", im Ziel" : ", außerhalb des Ziels") });
    var c = gr / 2, dreh = "rotate(-90 " + c + " " + c + ")";
    svg.appendChild(svgEl("circle", { cx: c, cy: c, r: r, fill: "none", class: "spur", "stroke-width": 10 }));
    var ru = 2 * Math.PI * (r + 9), von = lo / max, bis = (hi || max) / max;
    svg.appendChild(svgEl("circle", { cx: c, cy: c, r: r + 9, fill: "none", class: "zielbogen", "stroke-width": 3,
      "stroke-dasharray": ((bis - von) * ru).toFixed(1) + " " + ru.toFixed(1), "stroke-dashoffset": (-von * ru).toFixed(1), transform: dreh }));
    var anteil = Math.min(ist / max, 1);
    svg.appendChild(svgEl("circle", { cx: c, cy: c, r: r, fill: "none", class: "bogen m-" + k, "stroke-width": 10, "stroke-linecap": "round",
      "stroke-dasharray": Math.max(anteil * u, 0.1).toFixed(1) + " " + u.toFixed(1), transform: dreh }));
    var t1 = svgEl("text", { x: c, y: c + 2, class: "rz" }); t1.textContent = zahl(ist, 0);
    var t2 = svgEl("text", { x: c, y: c + 16, class: "re" }); t2.textContent = einheit + (ok ? " ✓" : "");
    svg.appendChild(t1); svg.appendChild(t2);
    var ziel = hi ? zahl(lo, 0) + "–" + zahl(hi, 0) : "ab " + zahl(lo, 0);
    return el("figure", { class: "ring" + (ok ? " ok" : "") }, [svg, el("figcaption", { html: "<strong>" + label + "</strong><br>Ziel " + ziel + " " + einheit })]);
  }

  // Tabs „Woche“/„Einkauf“ zeigen auf den Plan der aktuellen Woche (sonst den nächsten, sonst den letzten)
  function aktuellerPlan(iso) {
    var drin = null, naechster = null;
    D.plaene.forEach(function (p) {
      var von = p.tage[0].datum, bis = p.tage[p.tage.length - 1].datum;
      if (iso >= von && iso <= bis) drin = p;
      if (von > iso && (!naechster || von < naechster.tage[0].datum)) naechster = p;
    });
    return drin || naechster || D.plaene[D.plaene.length - 1] || null;
  }
  function tabsAktualisieren() {
    var p = aktuellerPlan(heuteIso());
    if (!p) return;
    Array.prototype.forEach.call(document.querySelectorAll("nav.tabs a"), function (a) {
      var t = a.textContent;
      if (/Woche/.test(t)) a.setAttribute("href", basis + "woche/" + p.name + ".html");
      if (/Einkauf/.test(t) && D.einkaufslisten) a.setAttribute("href", basis + "einkauf/" + p.name + ".html");
    });
    var e = naechsterEinkauf(heuteIso());
    if (D.einkaufslisten && e) {
      D.einkauf = "einkauf/" + e.plan.name + ".html";
      Array.prototype.forEach.call(document.querySelectorAll("nav.tabs a"), function (a) {
        if (/Einkauf/.test(a.textContent)) a.setAttribute("href", basis + D.einkauf);
      });
    }
  }
  // nächster anstehender Einkauf (heute oder später) → {plan, datum}; sonst null
  function naechsterEinkauf(iso) {
    var best = null;
    D.plaene.forEach(function (p) { (p.einkauf_tage || []).forEach(function (d) {
      if (d >= iso && (!best || d < best.datum)) best = { plan: p, datum: d };
    }); });
    return best;
  }

  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  // Rezept-Link mit dem Portionsfaktor aus dem Plan (Rezeptseite zeigt dann genau diese Portion)
  function rezeptLink(m) {
    return basis + "rezept/" + m.id + ".html" + (m.faktor && m.faktor !== 1 ? "?faktor=" + m.faktor : "");
  }

  // --- Heute ------------------------------------------------------------------------
  function heute() {
    var ziel = document.getElementById("heute");
    if (!ziel) return;
    var iso = heuteIso(), tag = null, plan = null;
    D.plaene.forEach(function (p) { p.tage.forEach(function (t) { if (t.datum === iso) { tag = t; plan = p; } }); });
    var d = new Date(iso + "T12:00:00");
    ziel.innerHTML = "";
    ziel.appendChild(el("p", { class: "leise", text: WOCHENTAGE[d.getDay()] + ", " + datumDe(iso) }));
    if (tag) {
      var marken = (tag.einkauf ? '<span class="marke">🛒 ' + (tag.start_einkauf ? "Starteinkauf" : "Einkauf") + "</span>" : "") +
        (tag.mealprep ? '<span class="marke">🍱 Heute vorkochen</span>' : "");
      ziel.appendChild(el("div", { class: "schicht-banner s-" + tag.schicht.toLowerCase(), html: "<span>" + SCHICHT[tag.schicht][0] + " <strong>" +
        SCHICHT[tag.schicht][1] + "</strong>" + (tag.schichtzeit ? " " + tag.schichtzeit : "") + "</span>" + marken }));
    }
    if (!tag) {
      var naechster = null;
      D.plaene.forEach(function (p) { p.tage.forEach(function (t) { if (t.datum > iso && (!naechster || t.datum < naechster.datum)) naechster = t; }); });
      var karte = el("div", { class: "karte" }, [el("h2", { text: "Für heute ist nichts geplant" })]);
      if (naechster) {
        karte.appendChild(el("p", { html: "Der nächste Plan beginnt am <strong>" + datumDe(naechster.datum) + "</strong>." }));
        karte.appendChild(el("a", { class: "knopf primaer", href: basis + "index.html?datum=" + naechster.datum, text: "Diesen Tag ansehen" }));
      } else {
        karte.appendChild(el("p", { text: "Sag in Claude „Woche planen“, dann erscheint hier dein Tag." }));
      }
      ziel.appendChild(karte);
      return;
    }
    var mk = el("div", { class: "karte" }, [el("h2", { text: "Mahlzeiten" })]);
    tag.mahlzeiten.forEach(function (m) {
      var info = (m.box ? "📦 " : "") + (m.einfrieren ? "❄️ " : "");
      var a = el("a", { class: "mahlzeit", href: rezeptLink(m) }, [
        el("span", { class: "slot", text: m.label + (m.zeit ? " · " + m.zeit : "") }),
        el("span", { class: "name", html: esc(info + m.name + (m.rest ? " (Rest)" : "")) +
          (m.faktor && m.faktor !== 1 ? ' <span class="faktor">×' + zahl(m.faktor, 2) + "</span>" : "") +
          (m.hinweis ? '<span class="mhinweis">' + esc(m.hinweis) + "</span>" : "") }),
        el("span", { class: "werte", html: zahl(m.kcal, 0) + " kcal<br>" + zahl(m.protein, 0) + " g P" })]);
      mk.appendChild(a);
    });
    if (tag.auswaerts) mk.appendChild(el("div", { class: "mahlzeit" }, [el("span", { class: "slot", text: "Auswärts" }),
      el("span", { class: "name", text: tag.auswaerts }), el("span", { class: "werte", text: "Platzhalter" })]));
    tag.extras.forEach(function (x) {
      mk.appendChild(el("div", { class: "mahlzeit" }, [el("span", { class: "slot", text: "Extra" }),
        el("span", { class: "name", text: x.text }), el("span", { class: "werte", html: zahl(x.kcal, 0) + " kcal<br>" + zahl(x.protein, 0) + " g P" })]));
    });
    ziel.appendChild(mk);

    // Meal Prep: klar sagen, ob heute etwas für später mitgekocht wird
    var vk = tag.vorkochen || [];
    var prep = el("div", { class: "karte vorkochen-karte " + (vk.length ? "ja" : "nein") }, [
      el("h2", { text: vk.length ? "🍱 Heute für später vorkochen" : "✓ Heute nichts vorkochen" })]);
    if (vk.length) {
      var pl = el("ul", {});
      vk.forEach(function (t) { pl.appendChild(el("li", { text: t })); });
      prep.appendChild(pl);
    } else {
      prep.appendChild(el("p", { class: "leise", text: "Du kochst heute nur für heute." }));
    }
    ziel.appendChild(prep);

    var bk = el("div", { class: "karte" }, [el("h2", { text: "Tagessumme" })]);
    var ringe = el("div", { class: "ringe" });
    [["kcal", "Kalorien", "kcal"], ["protein", "Protein", "g"], ["fett", "Fett", "g"], ["kh", "KH", "g"]].forEach(function (b) {
      ringe.appendChild(ring(b[0], b[1], b[2], tag.summe[b[0]], D.ziele[b[0]], D.korridor[b[0]]));
    });
    bk.appendChild(ringe);
    bk.appendChild(el("p", { class: "leise", text: "Grauer Bogen = Zielbereich · ✓ = im Ziel" }));
    ziel.appendChild(bk);

    var kochen = tag.mahlzeiten.filter(function (m) { return m.kochen; });
    if (kochen.length) {
      ziel.appendChild(el("div", { class: "knopfreihe" }, [el("a", { class: "knopf primaer",
        href: rezeptLink(kochen[0]) + "#kochmodus", text: "Jetzt kochen: " + kochen[0].name })]));
    }
    if (tag.erinnerungen.length) {
      var ek = el("div", { class: "karte" }, [el("h2", { text: "Erinnerungen für morgen" })]);
      var ul = el("ul", {});
      tag.erinnerungen.forEach(function (t) { ul.appendChild(el("li", { text: t })); });
      ek.appendChild(ul); ziel.appendChild(ek);
    }
    ziel.appendChild(el("p", {}, [el("a", { href: basis + "woche/" + plan.name + ".html", text: "Ganzen Wochenplan ansehen →" })]));
    var ne = naechsterEinkauf(iso);
    if (ne && ne.datum === iso && D.einkaufslisten) {
      ziel.insertBefore(el("a", { class: "knopf primaer einkauf-heute", href: basis + "einkauf/" + ne.plan.name + ".html",
        text: "🛒 Heute einkaufen für KW " + ne.plan.kw + " → Einkaufsliste" }), ziel.children[2] || null);
    } else if (!ne) {
      ziel.appendChild(el("p", { class: "leise", text: "📅 Der nächste Wochenplan mit Einkaufsliste kommt automatisch Freitagabend." }));
    }
    if (D.einkauf && budgetWert()) {
      ziel.appendChild(el("p", { class: "leise" }, [el("a", { href: basis + D.einkauf, text: "🛒 Einkaufsliste · Budget " + zahl(budgetWert(), 0) + " € →" })]));
    }
  }

  // --- Rezeptbuch ---------------------------------------------------------------------
  function rezeptbuch() {
    var form = document.getElementById("filter");
    if (!form) return;
    var liste = document.getElementById("kacheln");
    var kacheln = Array.prototype.slice.call(liste.children);
    var gespeichert = speicher("rezeptbuch-filter") || {};
    Array.prototype.forEach.call(form.elements, function (e) { if (e.name && gespeichert[e.name] !== undefined) e.value = gespeichert[e.name]; });
    function anwenden() {
      var f = {};
      Array.prototype.forEach.call(form.elements, function (e) { if (e.name) f[e.name] = e.value; });
      speicher("rezeptbuch-filter", f);
      var q = (f.suche || "").toLowerCase().trim(), n = 0;
      kacheln.forEach(function (k) {
        var d = k.dataset, sterne = d.sterne ? parseInt(d.sterne, 10) : 0;
        var ok = (!q || d.suche.indexOf(q) >= 0) &&
          (!f.kategorie || d.kategorien.split("|").indexOf(f.kategorie) >= 0) &&
          (!f.kueche || d.kueche === f.kueche) && (!f.mahlzeit || d.mahlzeit === f.mahlzeit) &&
          (!f.zeit || parseInt(d.zeit, 10) <= parseInt(f.zeit, 10)) &&
          (!f.bewertung || (f.bewertung === "neu" ? !sterne : sterne >= parseInt(f.bewertung, 10)));
        k.hidden = !ok; if (ok) n++;
      });
      var feld = f.sortierung || "name";
      kacheln.sort(function (a, b) {
        if (feld === "name") return a.dataset.name.localeCompare(b.dataset.name, "de");
        var richtung = feld === "protein" ? -1 : 1;
        return richtung * (parseFloat(a.dataset[feld]) - parseFloat(b.dataset[feld]));
      }).forEach(function (k) { liste.appendChild(k); });
      document.getElementById("treffer").textContent = n + " von " + kacheln.length + " Rezepten";
    }
    form.addEventListener("input", anwenden);
    form.addEventListener("change", anwenden);          // Safari (iPhone) meldet bei <select> oft nur „change“
    form.addEventListener("submit", function (e) { e.preventDefault(); });
    anwenden();
  }

  // --- Rezeptseite: Portionsrechner, MacroFactor, Kochmodus ---------------------------
  var faktor = 1;
  function mengeText(span, f) {
    var g = parseFloat(span.dataset.g) * f, anz = span.dataset.anz, name = span.dataset.name || "";
    if (span.dataset.art === "zelle") return anz ? skaliereAnzeige(anz, f) + " (" + gramm(g) + ")" : gramm(g);
    if (anz) return skaliereAnzeige(anz, f) + (name ? " " + name : "") + " (" + gramm(g) + ")";
    return gramm(g) + (name ? " " + name : "");
  }
  function skalieren(wurzel) {
    Array.prototype.forEach.call((wurzel || document).querySelectorAll(".m[data-g]"), function (s) { s.textContent = mengeText(s, faktor); });
  }
  function rezeptseite() {
    var rechner = document.getElementById("portionen");
    if (!rechner) return;
    var basisPortionen = parseInt(rechner.dataset.basis, 10), anzahl = basisPortionen;
    var out = rechner.querySelector("output");
    function setze(n) {
      anzahl = Math.max(1, Math.min(6, n)); faktor = anzahl / basisPortionen;
      out.textContent = anzahl; skalieren();
      document.getElementById("faktor-hinweis").hidden = faktor === 1;
    }
    // ?faktor=1.25 aus Heute/Woche: Portion wie im Plan (Mengen × Faktor, Nährwerte der Plan-Portion)
    var pf = parseFloat(new URLSearchParams(location.search).get("faktor"));
    var box = document.getElementById("plan-faktor");
    if (box && pf > 0 && pf <= 2 && pf !== 1 && Math.abs(pf * 4 - Math.round(pf * 4)) < 1e-9) {
      faktor = pf; skalieren();
      out.textContent = basisPortionen + " × " + zahl(pf, 2);
      var d = box.dataset;
      box.innerHTML = "📅 <strong>Im Plan mit Faktor " + zahl(pf, 2) + "</strong>: alle Mengen × " + zahl(pf, 2) +
        ". Deine Portion: <strong>" + zahl(d.kcal * pf, 0) + " kcal · " + zahl(d.protein * pf, 0) + " g Protein</strong> · " +
        zahl(d.fett * pf, 0) + " g Fett · " + zahl(d.kh * pf, 0) + " g KH. In MacroFactor " + zahl(pf, 2) +
        " Portionen loggen (oder nach Gramm). Die Nährwerte unten gelten für die Grundportion.";
      box.hidden = false;
    }
    rechner.querySelector("[data-schritt='-1']").addEventListener("click", function () { setze(anzahl - 1); });
    rechner.querySelector("[data-schritt='1']").addEventListener("click", function () { setze(anzahl + 1); });

    var mf = document.getElementById("macrofactor");
    mf.addEventListener("click", function () {
      var text = document.getElementById("macrofactor-text").textContent.trim();
      function fallback() {
        var ta = el("textarea", { readonly: "", style: "position:fixed;top:-1000px" }); ta.value = text;
        document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); meldung("Zutaten kopiert – in MacroFactor einfügen"); }
        catch (e) { meldung("Kopieren nicht möglich – bitte Text markieren"); }
        ta.remove();
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(function () { meldung("Zutaten kopiert – in MacroFactor einfügen"); }, fallback);
      } else { fallback(); }
    });
    document.getElementById("kochmodus-start").addEventListener("click", function () { kochmodus(0); });
    if (location.hash === "#kochmodus") kochmodus(0);
  }

  var wakeLock = null;
  function wachHalten(an) {
    try {
      if (an && navigator.wakeLock) navigator.wakeLock.request("screen").then(function (w) { wakeLock = w; }, function () {});
      if (!an && wakeLock) { wakeLock.release(); wakeLock = null; }
    } catch (e) { /* nicht unterstützt: still ignorieren */ }
  }
  function piep() {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext, ctx = new Ctx();
      [0, 0.4, 0.8].forEach(function (t) {
        var o = ctx.createOscillator(), g = ctx.createGain();
        o.frequency.value = 880; o.connect(g); g.connect(ctx.destination);
        g.gain.setValueAtTime(0.25, ctx.currentTime + t); g.gain.setValueAtTime(0, ctx.currentTime + t + 0.25);
        o.start(ctx.currentTime + t); o.stop(ctx.currentTime + t + 0.3);
      });
    } catch (e) { /* kein Audio */ }
    try { if (navigator.vibrate) navigator.vibrate([300, 150, 300, 150, 300]); } catch (e) { /* keine Vibration */ }
  }
  function kochmodus(start) {
    var schritte = JSON.parse(document.getElementById("kochdaten").textContent);
    var i = start, timer = null, rest = 0;
    var box = el("div", { class: "kochmodus", role: "dialog", "aria-modal": "true", "aria-label": "Kochmodus" });
    var zaehler = el("span", { class: "zaehler" });
    var zu = el("button", { type: "button", "aria-label": "Kochmodus schließen", text: "✕ Schließen" });
    var inhalt = el("div", { class: "inhalt" });
    var zurueck = el("button", { type: "button", text: "← Zurück" });
    var weiter = el("button", { type: "button", class: "primaer", text: "Weiter →" });
    box.appendChild(el("div", { class: "oben" }, [zaehler, zu]));
    box.appendChild(inhalt);
    box.appendChild(el("div", { class: "unten" }, [zurueck, weiter]));
    document.body.appendChild(box);
    document.body.style.overflow = "hidden";
    wachHalten(true);

    function stopTimer() { if (timer) { clearInterval(timer); timer = null; } }
    function zeige() {
      stopTimer();
      var s = schritte[i];
      zaehler.textContent = "Schritt " + (i + 1) + " von " + schritte.length;
      inhalt.innerHTML = "";
      inhalt.appendChild(el("h2", { text: s.titel }));
      var text = el("div", { class: "text", html: s.html }); skalieren(text); inhalt.appendChild(text);
      if (s.timer) {
        var anzeige = el("div", { class: "timer", text: s.timer + ":00" });
        var knopf = el("button", { type: "button", class: "primaer", text: "⏱ Timer " + s.timer + " min starten" });
        knopf.addEventListener("click", function () {
          stopTimer(); rest = s.timer * 60; anzeige.classList.remove("fertig");
          timer = setInterval(function () {
            rest -= 1;
            anzeige.textContent = Math.floor(rest / 60) + ":" + String(rest % 60).padStart(2, "0");
            if (rest <= 0) { stopTimer(); anzeige.textContent = "Fertig!"; anzeige.classList.add("fertig"); piep(); }
          }, 1000);
          knopf.textContent = "⏱ Neu starten";
        });
        inhalt.appendChild(anzeige); inhalt.appendChild(knopf);
      }
      if (s.zutaten.length) {
        var z = el("div", { class: "zutaten", html: "<strong>Zutaten in diesem Schritt:</strong><br>" + s.zutaten.join("<br>") });
        skalieren(z); inhalt.appendChild(z);
      }
      zurueck.disabled = i === 0;
      weiter.textContent = i === schritte.length - 1 ? "Fertig ✓" : "Weiter →";
    }
    function schliessen() {
      stopTimer(); wachHalten(false); box.remove(); document.body.style.overflow = "";
      if (location.hash === "#kochmodus") history.replaceState(null, "", location.pathname + location.search);
    }
    zu.addEventListener("click", schliessen);
    zurueck.addEventListener("click", function () { if (i > 0) { i--; zeige(); } });
    weiter.addEventListener("click", function () { if (i < schritte.length - 1) { i++; zeige(); } else { schliessen(); } });
    var x0 = null;
    inhalt.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    inhalt.addEventListener("touchend", function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0; x0 = null;
      if (dx < -60 && i < schritte.length - 1) { i++; zeige(); } else if (dx > 60 && i > 0) { i--; zeige(); }
    });
    document.addEventListener("visibilitychange", function () { if (document.visibilityState === "visible" && box.isConnected) wachHalten(true); });
    zeige();
  }

  // --- Einkaufsliste ----------------------------------------------------------------------
  function einkauf() {
    var wurzel = document.getElementById("einkauf");
    if (!wurzel) return;
    var key = "einkauf:" + wurzel.dataset.plan;
    var stand = speicher(key) || {};
    function sortiere(ul) {
      var items = Array.prototype.slice.call(ul.children);
      items.sort(function (a, b) {
        return (a.classList.contains("erledigt") - b.classList.contains("erledigt")) || (a.dataset.pos - b.dataset.pos);
      }).forEach(function (li) { ul.appendChild(li); });
    }
    Array.prototype.forEach.call(wurzel.querySelectorAll(".liste"), function (ul) {
      Array.prototype.forEach.call(ul.children, function (li, n) {
        li.dataset.pos = n;
        var cb = li.querySelector("input[type=checkbox]");
        cb.checked = !!stand[cb.dataset.key];
        li.classList.toggle("erledigt", cb.checked);
        cb.addEventListener("change", function () {
          stand[cb.dataset.key] = cb.checked; if (!cb.checked) delete stand[cb.dataset.key];
          speicher(key, stand); li.classList.toggle("erledigt", cb.checked); sortiere(ul);
        });
      });
      sortiere(ul);
    });
    document.getElementById("zuruecksetzen").addEventListener("click", function () {
      stand = {}; speicher(key, stand);
      Array.prototype.forEach.call(wurzel.querySelectorAll(".liste"), function (ul) {
        Array.prototype.forEach.call(ul.children, function (li) { li.querySelector("input").checked = false; li.classList.remove("erledigt"); });
        sortiere(ul);
      });
      meldung("Alle Haken zurückgesetzt");
    });
    budget();
  }

  // Balken: Verbrauch (kräftig) + Reste (hell) = Einkauf, senkrechte Linie = Budget; alles beschriftet
  function budgetBalken(k, b) {
    var max = Math.max(k.woche, b) * 1.08, pz = function (v) { return (100 * v / max).toFixed(1) + "%"; };
    var spur = el("div", { class: "bspur", role: "img", "aria-label": "Einkauf " + euro(k.woche) + ", davon verbraucht " +
      euro(k.verbrauch) + ", Budget " + euro(b) }, [
      el("span", { class: "bverbrauch", style: "width:" + pz(k.verbrauch) }),
      el("span", { class: "breste", style: "width:" + pz(k.reste) }),
      el("span", { class: "blinie", style: "left:" + pz(b) })]);
    var leg = el("div", { class: "blegende", html: '<span><i class="bverbrauch"></i>verbraucht ' + euro(k.verbrauch) + '</span>' +
      '<span><i class="breste"></i>Reste ' + euro(k.reste) + '</span><span><i class="blinie-l"></i>Budget ' + euro(b) + "</span>" });
    return el("div", { class: "budgetbalken" }, [spur, leg]);
  }

  function budget() {
    var karte = document.getElementById("budget");
    if (!karte) return;
    var k = JSON.parse(document.getElementById("kostendaten").textContent);
    var eingabe = document.getElementById("budget-betrag"), ergebnis = document.getElementById("budget-ergebnis");
    var standard = Number(karte.dataset.standard);
    function zeige() {
      var b = Number(eingabe.value), gesamt = k.woche + k.vorrat;
      ergebnis.innerHTML = "";
      ergebnis.appendChild(el("p", { html: "Wochenbedarf ca. <strong>" + euro(k.woche) + "</strong>, dazu einmalige Vorratskäufe ca. " +
        euro(k.vorrat) + " (z. B. Whey, Gewürze, Öl – reichen mehrere Wochen)." }));
      ergebnis.appendChild(el("p", { class: "leise", html: "Davon verbraucht diese Woche ca. <strong>" + euro(k.verbrauch) +
        "</strong>; Reste für ca. " + euro(k.reste) + " bleiben für die nächsten Wochen." }));
      if (b > 0) ergebnis.appendChild(budgetBalken(k, b));
      if (!(b > 0)) return;
      if (k.verbrauch <= b && k.woche > b) ergebnis.appendChild(el("p", { class: "ok", text: "✓ Verbrauch im Budget." }));
      if (gesamt <= b) {
        ergebnis.appendChild(el("p", { class: "ok", text: "✓ Im Budget – noch " + euro(b - gesamt) + " Luft." }));
        return;
      }
      ergebnis.appendChild(el("p", { class: "warn", text: k.woche <= b ? "⚠️ Mit Vorratskäufen über Budget (" + euro(gesamt) + ", " + euro(gesamt - b) + " zu viel)."
        : "⚠️ Schon der Wochenbedarf liegt über dem Budget (" + euro(k.woche - b) + " zu viel)." }));
      var ul = el("ul", {});
      k.teuer.forEach(function (t) { ul.appendChild(el("li", { text: t.zutat + " (" + euro(t.kosten) + "): günstigere Alternative im Plan tauschen oder Eigenmarke wählen" })); });
      ul.appendChild(el("li", { text: k.spar_whey }));
      ergebnis.appendChild(el("p", { html: "<strong>Sparvorschläge:</strong>" }));
      ergebnis.appendChild(ul);
    }
    eingabe.value = budgetWert();
    eingabe.addEventListener("input", function () {
      var b = Number(eingabe.value);
      if (eingabe.value !== "" && b >= 0) speicher("budget", b);
      zeige();
    });
    document.getElementById("budget-standard").addEventListener("click", function () {
      eingabe.value = standard; speicher("budget", standard); zeige(); meldung("Budget auf " + standard + " € zurückgesetzt");
    });
    zeige();
  }

  // --- Rezept löschen (über GitHub) --------------------------------------------------------
  function loeschen() {
    var knopf = document.getElementById("loeschen");
    if (!knopf || !D.github) return;
    knopf.addEventListener("click", function () {
      var id = knopf.dataset.id, heute = heuteIso(), tage = [];
      D.plaene.forEach(function (p) { p.tage.forEach(function (t) {
        if (t.datum >= heute && t.mahlzeiten.some(function (m) { return m.id === id; })) tage.push(datumDe(t.datum));
      }); });
      var text = tage.length
        ? "Achtung: „" + knopf.dataset.name + "“ steht im Wochenplan am " + tage.join(", ") + ".\nErst in Claude „tauschen“ sagen, sonst ist der Plan ungültig.\n\nTrotzdem zu GitHub wechseln und löschen?"
        : "„" + knopf.dataset.name + "“ wirklich löschen?\nDu landest bei GitHub und bestätigst dort mit „Commit changes“. Nach 1–2 Minuten ist es aus der App verschwunden.";
      if (window.confirm(text)) location.href = "https://github.com/" + D.github + "/delete/main/daten/rezepte/" + id + ".yaml";
    });
  }

  // --- Eigenes Rezept (Formular → YAML → GitHub) ---------------------------------------------
  function slug(name) {
    return name.toLowerCase().replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60);
  }
  function rezeptFormular() {
    var form = document.getElementById("rezept-form");
    if (!form) return;
    var DB = {}; D.zutaten.forEach(function (z) { DB[z[0]] = z; });
    var liste = document.getElementById("zutaten-zeilen"), ausgabe = document.getElementById("rezept-werte");
    var ENTWURF = "rezept-entwurf";
    function zeile(name, g) {
      var li = el("li", { class: "zzeile" }, [
        el("input", { type: "text", list: "zutaten-liste", class: "zname", placeholder: "Zutat suchen …", value: name || "", "aria-label": "Zutat" }),
        el("input", { type: "number", class: "zg", min: "0", step: "1", inputmode: "decimal", placeholder: "g", value: g || "", "aria-label": "Gramm für 2 Portionen" }),
        el("button", { type: "button", class: "zweg", "aria-label": "Zutat entfernen", text: "✕" })]);
      li.querySelector(".zweg").addEventListener("click", function () { li.remove(); aktualisieren(); });
      liste.appendChild(li);
    }
    function lesen() {
      var f = {}; Array.prototype.forEach.call(form.elements, function (e) {
        if (e.name) f[e.name] = e.type === "checkbox" ? e.checked : e.value;
      });
      f.zutaten = Array.prototype.map.call(liste.children, function (li) {
        return { zutat: li.querySelector(".zname").value.trim(), g: parseFloat(li.querySelector(".zg").value) || 0 };
      }).filter(function (z) { return z.zutat || z.g; });
      return f;
    }
    function werte(f) {
      var s = { kcal: 0, protein: 0, fett: 0, kh: 0, zucker: 0 };
      f.zutaten.forEach(function (z) { var w = DB[z.zutat]; if (!w) return;
        s.kcal += w[1] * z.g / 100; s.protein += w[2] * z.g / 100; s.fett += w[3] * z.g / 100; s.kh += w[4] * z.g / 100; s.zucker += w[5] * z.g / 100; });
      Object.keys(s).forEach(function (k) { s[k] /= 2; });
      return s;
    }
    function korridorSchluessel(f, p) {
      if (f.mahlzeit === "Frühstück") return "fruehstueck";
      if (f.mahlzeit === "Snack") return "snack";
      var k = D.korridore.kalorienarm;
      return p.kcal <= k.kcal_max && p.protein >= k.protein_min ? "kalorienarm" : "hauptgericht";
    }
    function kategorien(f, p) {
      var k = [], zeit = (+f.vorbereitung || 0) + (+f.kochen || 0);
      if (p.protein >= 40 || (p.kcal > 0 && p.protein / p.kcal * 100 >= 10)) k.push("High Protein");
      if (zeit <= 25) k.push("Schnelle Rezepte");
      if (f.mahlzeit === "Mittag/Abend" && korridorSchluessel(f, p) === "kalorienarm") k.push("Kalorienarm");
      if (f.mahlzeit !== "Mittag/Abend") k.push("Frühstück & Snacks");
      return k;
    }
    function hauptkategorie(f, kats) {
      if (f.mahlzeit !== "Mittag/Abend") return "fruehstueck-snacks";
      if (kats.indexOf("Kalorienarm") >= 0) return "kalorienarm";
      if (kats.indexOf("High Protein") >= 0) return "high-protein";
      if (kats.indexOf("Schnelle Rezepte") >= 0) return "schnell";
      return "high-protein";
    }
    function schritte(f) {
      return f.schritte.split("\n").map(function (t) { return t.trim(); }).filter(Boolean);
    }
    function ohneKlammern(t) { return t.replace(/[{]/g, "(").replace(/[}]/g, ")"); }
    function yaml(f, p, kats) {
      var q = function (t) { return JSON.stringify(ohneKlammern(String(t))); };
      var tage = Math.max(0, Math.min(4, parseInt(f.tage, 10) || 0));
      var z = f.zutaten.filter(function (x) { return DB[x.zutat] && x.g > 0; });
      var out = ["# Eigenes Rezept aus der App (" + heuteIso() + ")", "id: " + slug(f.name), "name: " + q(f.name),
        "hauptkategorie: " + hauptkategorie(f, kats), "kategorien_manuell: []", "mahlzeit: " + q(f.mahlzeit),
        "geschmack: " + f.geschmack, "kueche: " + q(f.kueche), "herkunft: {art: eigen, quelle: App, datum: " + heuteIso() + "}",
        "schwierigkeit: " + f.schwierigkeit,
        "zeit: {vorbereitung: " + (parseInt(f.vorbereitung, 10) || 0) + ", kochen: " + (parseInt(f.kochen, 10) || 0) +
          ", wartezeit: " + (parseInt(f.wartezeit, 10) || 0) + "}",
        "ausstattung: []", "zutaten:"];
      z.forEach(function (x, i) { out.push("  - {id: z" + (i + 1) + ", zutat: " + q(x.zutat) + ", g: " + Math.round(x.g * 10) / 10 + "}"); });
      out.push("mise_en_place: []", "schritte:");
      schritte(f).forEach(function (t, i) {
        out.push("  - titel: " + q("Schritt " + (i + 1)), "    text: " + q(t), "    timer_min: null");
      });
      var tipps = (f.tipps || "").split("\n").map(function (t) { return t.trim(); }).filter(Boolean);
      out.push("zeitablauf: []", "fehler: []", 'anrichten: ""',
        "aufbewahrung: {kuehlschrank_tage: " + tage + ", einfrierbar: " + (f.einfrierbar ? "true" : "false") + ", aufwaermen: " +
          q(tage ? "Abgedeckt in der Mikrowelle bei 600 W warm machen." : "Frisch essen.") + "}",
        "varianten: []", "tipps: [" + tipps.map(q).join(", ") + "]", "gargewicht_g: null",
        "bewertung: {sterne: null, kommentar: null, datum: null}");
      return out.join("\n") + "\n";
    }
    function aktualisieren() {
      var f = lesen(), p = werte(f), kats = kategorien(f, p), ks = korridorSchluessel(f, p), k = D.korridore[ks];
      try { window.localStorage.setItem(ENTWURF, JSON.stringify(f)); } catch (e) { /* privat */ }
      var unbekannt = f.zutaten.filter(function (z) { return z.zutat && !DB[z.zutat]; }).map(function (z) { return z.zutat; });
      var id = slug(f.name || ""), probleme = [];
      if (!f.name || !f.name.trim()) probleme.push("Name fehlt");
      else if (D.ids.indexOf(id) >= 0 || (D.namen || []).indexOf(f.name.trim().toLowerCase()) >= 0) probleme.push("Ein Rezept mit diesem Namen gibt es schon – bitte anders benennen");
      if (!f.zutaten.some(function (z) { return DB[z.zutat] && z.g > 0; })) probleme.push("Mindestens eine Zutat mit Gramm");
      if (!schritte(f).length) probleme.push("Mindestens ein Schritt");
      if (unbekannt.length) probleme.push("Nicht in der Zutatenliste (werden weggelassen – in Claude ergänzen lassen): " + unbekannt.join(", "));
      var kcalOk = (k.kcal_min == null || p.kcal >= k.kcal_min) && (k.kcal_max == null || p.kcal <= k.kcal_max);
      var pOk = p.protein >= k.protein_min;
      ausgabe.innerHTML = "";
      ausgabe.appendChild(el("div", { class: "fwerte" }, [
        el("div", { html: "<strong>" + zahl(p.kcal, 0) + "</strong><span>kcal</span>" }),
        el("div", { html: "<strong>" + zahl(p.protein, 0) + "</strong><span>g Protein</span>" }),
        el("div", { html: "<strong>" + zahl(p.fett, 0) + "</strong><span>g Fett</span>" }),
        el("div", { html: "<strong>" + zahl(p.kh, 0) + "</strong><span>g KH</span>" })]));
      ausgabe.appendChild(el("p", { class: kcalOk && pOk ? "ok" : "warn", text: (kcalOk && pOk ? "✓ " : "⚠️ ") + "Pro Portion · Ziel " +
        (ks === "hauptgericht" ? "Hauptgericht" : ks === "kalorienarm" ? "Kalorienarm" : ks === "fruehstueck" ? "Frühstück" : "Snack") + ": " +
        (k.kcal_min != null ? zahl(k.kcal_min, 0) + "–" : "bis ") + zahl(k.kcal_max, 0) + " kcal, ab " + k.protein_min + " g Protein" +
        (kcalOk && pOk ? "" : " (Rezept geht trotzdem, der Planer gleicht über die Portion aus)") }));
      ausgabe.appendChild(el("p", { class: "leise", text: "Kategorien: " + (kats.join(" · ") || "–") }));
      var hinweise = document.getElementById("rezept-probleme");
      hinweise.innerHTML = "";
      probleme.forEach(function (t) { hinweise.appendChild(el("li", { text: t })); });
      var bereit = !probleme.some(function (t) { return t.indexOf("Nicht in der Zutatenliste") < 0; });
      var knopf = document.getElementById("rezept-speichern");
      knopf.disabled = !bereit || !D.github;
      knopf.dataset.url = bereit && D.github ? "https://github.com/" + D.github + "/new/main?filename=" +
        encodeURIComponent("daten/rezepte/" + id + ".yaml") + "&value=" + encodeURIComponent(yaml(f, p, kats)) : "";
      document.getElementById("rezept-yaml").textContent = bereit ? yaml(f, p, kats) : "";
    }
    var gespeichert = null;
    try { gespeichert = JSON.parse(window.localStorage.getItem(ENTWURF) || "null"); } catch (e) { gespeichert = null; }
    if (gespeichert) {
      Array.prototype.forEach.call(form.elements, function (e) {
        if (e.name && gespeichert[e.name] !== undefined) { if (e.type === "checkbox") e.checked = gespeichert[e.name]; else e.value = gespeichert[e.name]; }
      });
      (gespeichert.zutaten || []).forEach(function (z) { zeile(z.zutat, z.g); });
    }
    if (!liste.children.length) { zeile(); zeile(); zeile(); }
    document.getElementById("zutat-plus").addEventListener("click", function () { zeile(); });
    form.addEventListener("input", aktualisieren);
    form.addEventListener("change", aktualisieren);
    form.addEventListener("submit", function (e) { e.preventDefault(); });
    document.getElementById("rezept-speichern").addEventListener("click", function () {
      var url = this.dataset.url;
      if (url) location.href = url;
    });
    document.getElementById("rezept-verwerfen").addEventListener("click", function () {
      if (!window.confirm("Entwurf wirklich verwerfen?")) return;
      try { window.localStorage.removeItem(ENTWURF); } catch (e) { /* privat */ }
      form.reset(); liste.innerHTML = ""; zeile(); zeile(); zeile(); aktualisieren();
    });
    aktualisieren();
  }

  tabsAktualisieren(); heute(); rezeptbuch(); rezeptseite(); einkauf(); loeschen(); rezeptFormular();
})();
