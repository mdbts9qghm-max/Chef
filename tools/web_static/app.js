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

  // --- Heute ------------------------------------------------------------------------
  function heute() {
    var ziel = document.getElementById("heute");
    if (!ziel) return;
    var iso = heuteIso(), tag = null, plan = null;
    D.plaene.forEach(function (p) { p.tage.forEach(function (t) { if (t.datum === iso) { tag = t; plan = p; } }); });
    var d = new Date(iso + "T12:00:00");
    ziel.innerHTML = "";
    ziel.appendChild(el("p", { class: "leise", text: WOCHENTAGE[d.getDay()] + ", " + datumDe(iso) +
      (tag ? " · " + (tag.schicht === "frei" ? "frei" : tag.schicht + "schicht " + tag.schichtzeit) : "") }));
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
      var info = m.box ? "📦 " : "";
      var a = el("a", { class: "mahlzeit", href: basis + "rezept/" + m.id + ".html" }, [
        el("span", { class: "slot", text: m.label + (m.zeit ? " · " + m.zeit : "") }),
        el("span", { class: "name", text: info + m.name + (m.rest ? " (Rest)" : "") }),
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

    var bk = el("div", { class: "karte" }, [el("h2", { text: "Tagessumme" })]);
    [["kcal", "Kalorien", "kcal", "--kcal"], ["protein", "Protein", "g", "--p"], ["fett", "Fett", "g", "--f"], ["kh", "Kohlenhydrate", "g", "--kh"]]
      .forEach(function (b) {
        var ist = tag.summe[b[0]], soll = D.ziele[b[0]], pz = Math.min(100, ist / soll * 100);
        bk.appendChild(el("div", { class: "balken" }, [
          el("div", { class: "zeile", html: "<span>" + b[1] + "</span><span>" + zahl(ist, 0) + " / " + zahl(soll, 0) + " " + b[2] + "</span>" }),
          el("div", { class: "spur" }, [el("div", { class: "fuellung", style: "width:" + pz.toFixed(1) + "%;background:var(" + b[3] + ")" })])]));
      });
    ziel.appendChild(bk);

    var kochen = tag.mahlzeiten.filter(function (m) { return m.kochen; });
    if (kochen.length) {
      ziel.appendChild(el("div", { class: "knopfreihe" }, [el("a", { class: "knopf primaer",
        href: basis + "rezept/" + kochen[0].id + ".html#kochmodus", text: "Jetzt kochen: " + kochen[0].name })]));
    }
    if (tag.erinnerungen.length) {
      var ek = el("div", { class: "karte" }, [el("h2", { text: "Erinnerungen für morgen" })]);
      var ul = el("ul", {});
      tag.erinnerungen.forEach(function (t) { ul.appendChild(el("li", { text: t })); });
      ek.appendChild(ul); ziel.appendChild(ek);
    }
    ziel.appendChild(el("p", {}, [el("a", { href: basis + "woche/" + plan.name + ".html", text: "Ganzen Wochenplan ansehen →" })]));
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

  heute(); rezeptbuch(); rezeptseite(); einkauf();
})();
