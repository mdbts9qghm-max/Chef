# CLAUDE.md – Arbeitsregeln für das Rezeptbuch

Vollständige Vorgabe: `SPEC.md` (bei Unklarheit dort nachlesen; bei Widersprüchen **fragen, nicht raten**). Persönliche Werte: `daten/profil.yaml`.

## Leitsatz
Jedes Rezept so genau, dass man es ohne Nachdenken nachkochen kann. **Jede Zahl wird gerechnet, nie geschätzt.** Geschmack und Alltag vor perfekten Makros, aber **Protein hat immer Priorität**.

## Datenmodell
- **Single Source of Truth:** `daten/` (YAML/CSV). Rezepte in `daten/rezepte/<id>.yaml`, Pläne in `daten/wochenplaene/KW-XX-JJJJ.yaml`, Vorrat in `daten/vorrat.yaml`.
- **Generiert, nie von Hand bearbeiten:** `rezepte/`, `rezeptbuch.md`, `wochenplaene/*.md`, `einkaufslisten/`, `web/`.
- Mengen in Texten nur über Platzhalter: `{zutat_id}` = Menge + Name, `{zutat_id:n}` = nur Name, `{portion_g}` = berechnetes Gewicht pro Portion (in „Anrichten“ statt geschätzter Gramm). Jede Zutat kommt mindestens einmal im Text vor.
- Varianten strukturiert mit `aenderung: {Zutat: ±g}`; die Makro-Änderung rechnet der Generator. Ofenschritte nennen immer die Schiene (daran erkennt die Prüfung sie).
- Schwellenwerte/Toleranzen nur in `tools/config.py` (liest Ziele aus `profil.yaml`), nie hart im Code verteilt.

## Harte Regeln (Kurzfassung)
- **Profil:** 2.275 kcal · 149 g P · 101 g F · 191 g KH. 2 Portionen pro Rezept, Nährwerte pro Portion.
- **Frühstück immer süß**, proteinreich, max. ~20 g Zucker/Portion. **Wenig Gemüse.** Supermarkt-Zutaten (REWE, Lidl/Aldi). Max. ~90 Zutaten gesamt.
- **Korridore pro Portion:** Frühstück 500–650 kcal / ≥ 35 g P · Hauptgericht 600–850 / ≥ 45 g · Kalorienarm ≤ 550 / ≥ 35 g · Snack 200–350 / ≥ 20 g.
- **Kategorien (automatisch):** High Protein ≥ 40 g P oder ≥ 10 g P/100 kcal · Schnell ≤ 25 min (Vorb. + Kochen) · Kalorienarm (s. o.) · Meal Prep manuell (≥ 3 Tage haltbar). Hauptkategorie nicht erfüllt ⇒ Rezept anpassen.
- **Rezept-Markdown:** 12 Abschnitte in fester Reihenfolge (SPEC 7). Exakte Mengen für alles, Öl/Butter/Saucen voll gezählt, Kochwasser-Salz „nicht mitgerechnet“.
- **Ausstattung:** Ceranherd „Stufe X von 9“, Ofen immer O/U **und** Umluft, Pfannen 28/24 cm, Formen 20×20 und ca. 30×20, Airfryer, Standmixer, Waffeleisen, Mikrowelle.
- **Kerntemperaturen:** Geflügel 74 °C · Hack 72 °C · Schweinefilet 63 °C · Lachs 50–55 °C glasig / 60 °C durch · Schmorgerichte Gabelprobe.
- **Haltbarkeit:** Fisch/Garnelen max. 2 Tage gekühlt, sonst max. 3–4 Tage. Reis binnen 1 h kühlen.
- **Plausibilität:** 4P + 4KH + 9F + 2Ballast vs. kcal: pro Zutat ±5 % **oder** ±5 kcal/100 g (Polyole ausgenommen), pro Rezept streng ±5 %.
- **Schichten:** 5-Tage-Zyklus Tag 7–19 · Nacht 19–7 · 3× frei (Start Tag So 1.11.2026, `profil.yaml`). Boxen: Tag → Frühstück + Mittag, Nacht → Abend (Mikrowelle vorhanden). Meal Prep am letzten freien Tag vor der Tagschicht.
- **Planung (8.2):** P ≥ 145 g · kcal 2.175–2.275 (**nie über dem Ziel**) · F ± 15 (nie < 70) · KH ± 20. Abends keine gleiche Küche/Proteinquelle an Folgetagen. Wiederholungen: Hauptgericht max. 1× gekocht (= max. 2 Mahlzeiten), gleiches Frühstück/Snack max. 2 Tage (dann 1× mit 2 Ladungen). 1–2 Sterne nie, 3 Sterne max. 1×/Woche. Einkauf nur **Samstag** ⇒ Fisch/Garnelen/Hack frisch nur Sa–Mo, übriges Frischfleisch max. 4 Tage, sonst einfrieren (`einfrieren: true`) + Auftau-Erinnerung. Fett kommt aus den Rezepten (`fett_strategie: rezepte`, Ø-Ziele je Gruppe in `config.FETT_ZIEL_PRO_MAHLZEIT`); Extras (Mandeln/Erdnussbutter) nur als Notlösung. Anpassen: `faktor` (0,25er-Schritte, 0,75–1,5) → Snack → Rezept tauschen → einfaches Extra.
- **Auswärts:** Platzhalter 950 kcal / 40 P / 45 F / 90 KH, Rest des Tages proteinreich + fettarm, keine Zutaten auf der Liste.
- **Einkaufsliste:** berechnet (nie geschrieben), Vorrat abziehen, auf Packungen runden, nach Abteilungen, Kosten vs. Budget (`profil.yaml`, in der App pro Gerät änderbar), Reste → `vorrat.yaml`, Kontrollrechnung.
- **Import:** eigene Worte, keine Texte/Fotos aus Posts übernehmen; Unklares gesammelt in einer Liste nachfragen.

## Arbeitsweise
- Jede Phase im **Plan-Modus** starten, OK abwarten. Am Ende: Prüfungen + Tests, Fortschrittsliste aktualisieren, Git-Commit vorschlagen (erst nach OK committen/pushen).
- Nach jeder Datenänderung: `python3 tools/pruefen.py` → `python3 tools/generieren.py` → `python3 tools/bestand.py` → ggf. veröffentlichen.
- Phase 4: Rezepte in der Reihenfolge von `daten/rezeptplan.yaml`, id und Küche wie im Plan (Test prüft das).

## Befehle (Entwicklung)
```bash
pip install -r requirements.txt          # pyyaml, pytest, playwright (Chromium ist vorinstalliert)
python3 tools/pruefen.py                 # alle Prüfungen (SPEC 12.1)
python3 tools/generieren.py              # Markdown + Web-App erzeugen
python3 tools/bestand.py                 # Soll/Ist gegen SPEC 5.1–5.3, schreibt rezeptplan.md
python3 tools/planer.py KW-46-2026 [--budget 100] [--starts 24] [--behalten] [--einkauf JJJJ-MM-TT …]   # Woche automatisch planen (günstig, regelkonform; --einkauf z. B. für einen Starteinkauf)
python3 tools/woche_auto.py [--heute JJJJ-MM-TT]   # Automatik (läuft Fr auf GitHub): nächste Woche planen, Reste übernehmen
python3 tools/wochenplan.py KW-45-2026   # Wochenplan prüfen + wochenplaene/KW-45-2026.md erzeugen
python3 tools/einkauf.py KW-45-2026      # Einkaufsliste (--reste-uebernehmen: Reste → vorrat.yaml)
python3 -m pytest                        # Tests (SPEC 12.2), Playwright nutzt /opt/pw-browsers/chromium
python3 tools/web.py                     # nur die Web-App neu erzeugen (macht generieren.py automatisch)
python3 tools/veroeffentlichen.py        # „Web-App aktualisieren“: pruefen → generieren → bestand → Pläne + Einkauf → pytest, zeigt Änderungen in web/
python3 tools/veroeffentlichen.py --live # Live-Seite prüfen (github.io ist im Container gesperrt → WebFetch nutzen)
python3 tools/importieren.py             # Neues in import/ auflisten (--erledigt <name>, --link <url> --rezept <id>, --aehnlich <id>)
python3 tools/kuehlschrank.py "Hähnchen, Reis" [--gegessen kcal,P,F,KH] [--mahlzeit Mittag/Abend]
python3 tools/bewerten.py <id> <1–5> ["Kommentar"]   # nur die bewertung-Zeile wird ersetzt
```

## Arbeitsabläufe (Phase 7)
- **Import:** `importieren.py` → Screenshots ansehen / Text lesen / Link abrufen (Instagram blockiert oft → um Screenshot bitten, nicht raten) → Mengen mit `importieren.umrechnen` (Tabelle `config.UMRECHNUNG`) → Rezept nach Schema 6.4 + Standard 7 **in eigenen Worten**, an Makros angepasst, mit `inspiration` und `herkunft: {art: import, quelle, datum}` → `importieren.py --aehnlich <id>` (ab 0,65: fragen „Variante oder eigenes Rezept?“) → Unklares in **einer** Liste nachfragen → prüfen, generieren, `--erledigt`/`--link` → Zusammenfassung (kcal/Protein, offene Fragen).
- **Kühlschrank:** fragen, was heute schon gegessen wurde → `kuehlschrank.py … --gegessen …` → Top 3 mit Faktor zeigen; nichts Passendes → neues Gericht vorschlagen; gefällt es, als Rezept mit `herkunft: {art: neu}` aufnehmen.
- **Bewerten:** `bewerten.py` → bei Kommentaren („zu trocken“, „zu wenig süß“) Rezept anpassen und Makro-Unterschied vorher/nachher zeigen → prüfen, generieren.
- **Automatik:** Workflow `woche-planen.yml` (Fr ~17–18 Uhr) → `woche_auto.py`: plant die nächste Woche (nur wenn noch kein Plan existiert), übernimmt die Reste der laufenden Woche in `vorrat.yaml` (`reste_uebernommen`, Reste mit `aus: KW-…` zählen nur für spätere Wochen, abgelaufene gar nicht), committet und veröffentlicht. **Vor jeder Änderung `git pull`** (GitHub committet selbst). Ein Einkauf pro Woche: Samstag vor Wochenbeginn (`einkauf.pro_woche: 1`).
- **Woche planen:** Kurzfragen aus 8.1 (Wünsche, Auswärts-Termine) → Wünsche als `fest: true` bzw. `auswaerts` in die Plandatei → `planer.py KW-XX-JJJJ --behalten` (mehr `--starts` = günstiger, ca. 0,4 s pro Start) → Übersicht mit Tageswerten, Einkauf/Verbrauch/Reste → nach dem Einkauf `einkauf.py … --reste-uebernehmen`.
- **Eigene Rezepte (App):** Formular `rezept-neu.html` → YAML mit `herkunft: {art: eigen}` → GitHub „new file“ → Workflow prüft (`pruefen.py`) und baut (`generieren.py`). Für `eigen` sind Text-/Umfangs-/Korridorregeln nur Warnungen (`pruefen.weich`), leere Abschnitte werden weggelassen. Löschen über GitHub „delete“. Kommt ein eigenes Rezept dazu, lokal `git pull` vor der nächsten Änderung.
- **Startbestand:** SPEC 5 (genau 50, Verteilung) gilt nur für die Rezepte aus `rezeptplan.yaml`; Importe/neue Rezepte kommen dazu.

## Befehle im Alltag (SPEC 14)
| Befehl | Was passiert |
|---|---|
| **Woche planen** | Wochenplan + Einkaufsliste (SPEC 8) |
| **tauschen [Tag] [Mahlzeit]** | Mahlzeit ersetzen, Makros und Einkaufsliste neu rechnen |
| **was koche ich heute** | heutige Mahlzeiten mit Zeitplan und Link zum Kochmodus |
| **Import** | alles Neue aus `import/` übernehmen (SPEC 9) |
| **Import: [Link oder Text]** | einzelnes Rezept direkt aus dem Chat übernehmen |
| **Kühlschrank: [Zutaten]** | Kühlschrank-Modus (SPEC 11.1) |
| **bewerten [Rezept] [Sterne] [Kommentar]** | Bewertung speichern (SPEC 11.2) |
| **neue Rezepte** / **Küche: [Name]** / **trending** | neue Rezepte (SPEC 11.3) |
| **anpassen [Rezept]** | Rezept ändern, Nährwerte neu rechnen |
| **Ziele: [kcal, P, F, KH]** | `profil.yaml` aktualisieren, aktuelle Pläne neu prüfen |
| **Vorrat** | `vorrat.yaml` anzeigen und aktualisieren |
| **Budget: [€]** | `einkauf.budget_eur_pro_woche` in `profil.yaml` setzen (Planung + Standardwert der App), Einkaufsliste neu rechnen |
| **Web-App aktualisieren** | generieren, prüfen, veröffentlichen |

## Fortschritt
- [x] **Phase 1 – Planung & Onboarding** (22.10.2026): Onboarding, SPEC.md, CLAUDE.md, profil.yaml, Ordnergerüst, Git
- [x] **Phase 2 – Grundlagen** (22.10.2026, Beispielrezepte abgenommen 24.10.2026): ✓ zutaten.csv (91 Zutaten, alle plausibel), ✓ packungen.csv, ✓ config.py, ✓ naehrwerte.py, ✓ pruefen.py, ✓ generieren.py (Markdown), ✓ 44 Tests, ✓ Beispielrezepte `fruehstuecks-brownie` + `marry-me-chicken`. Zutatenbestand nach Phase 4 getrimmt (✓).
- [x] **Phase 3 – Rezeptliste** (24.10.2026): 50 Gerichte in `daten/rezeptplan.yaml` → `rezeptplan.md`, Abgleich 5.1–5.3 per `tools/bestand.py` (Plan erfüllt alle Vorgaben), „Spaghetti“ → „Hartweizennudeln ungekocht“, „Rote Currypaste“ neu
- [x] **Phase 4 – Rezepte schreiben** (24.10.2026): alle 50 Rezepte, 0 Fehler/Warnungen, alle 26 Vorgaben aus SPEC 5 erfüllt (50/50 High Protein), 90 genutzte Zutaten (89 ohne Wasser). Befund für Phase 5: Rezepte eher fettarm (Ø 17–20 g Fett/Mahlzeit) → Fettziel 86–116 g braucht oft Snack/Extra (z. B. Nüsse).
- [x] **Phase 5 – Wochenplanung & Einkauf** (24.10.2026): `wochenplan.py` (Schichtzyklus, Tagessummen, Regeln 8.2, Markdown), `einkauf.py` (Vorrat, Packungen, Abteilungen, Kosten, Reste, Kontrollrechnung, 2 Einkaufstermine), 86 Tests, erster Plan KW 45 (7/7 Tage regelkonform, Ø 2.271 kcal / 177 g P / 87 g F / 185 g KH). Offen: Wochenkosten ca. 154 € > Budget 100 €; zweiter Samstagseinkauf überschneidet sich künftig mit dem Einkauf der Folgewoche (zusammenführen).
- [x] **Phase 6 – Web-App** (25.10.2026): `tools/web.py` (von `generieren.py` aufgerufen) erzeugt `web/` – Heute, Rezeptbuch (Suche/Filter/Sortierung), 50 Rezeptseiten (JSON-LD, Portionsrechner, Kochmodus mit Timer/Wake Lock, MacroFactor-Kopie), Wochenplan als Tageskarten, Einkaufsliste mit gespeicherten Haken, PWA (Manifest, Icons, Service Worker). 97 Tests inkl. Playwright (390 × 844).
- [x] **Phase 7 – Import & Komfort** (25.10.2026): `importieren.py` (Eingang, Umrechnung, Ähnlichkeit, Ablage), `kuehlschrank.py` (Abgleich mit Grundvorrat/optional, Faktor nach Restmakros), `bewerten.py`; Test-Import eines fiktiven TikTok-Screenshots durchgespielt (Rezept danach auf Wunsch wieder gelöscht); Bestand trennt Startbestand und Importe; 122 Tests.
- [x] **Phase 8 – Livegang** (25.10.2026): Repo ist öffentlich → Pages kostenlos; Workflow `.github/workflows/pages.yml` veröffentlicht `web/` bei jedem Push auf main (einmalig Settings → Pages → Source „GitHub Actions“); `web_url` in `profil.yaml` → Canonical, JSON-LD `url`/`image`, Open Graph; `veroeffentlichen.py` (+ `--live`); README mit Alltagsanleitung; 126 Tests. MacroFactor-Link-Import am 26.10.2026 mit dir getestet: klappt (✓).
- [x] **Nachbesserung** (25.10.2026): Rezept 51 gelöscht; Budget in der App änderbar (Einkaufsseite, localStorage) + Befehl „Budget: [€]“; alle 50 Rezepte fettreicher bei gleichem Protein (Ø Fett Frühstück 17→21 g, Hauptgericht 20→26 g, kalorienarm 13→17 g, Snack 6→9 g; weniger Reis/Nudeln/Kartoffeln); KW 45 neu: 7/7 Tage regelkonform **ohne Extras** (Ø 2.326 kcal / 194 g P / 89 g F / 180 g KH, Wochenkosten ca. 161 €); 130 Tests. Befund: Pläne liegen bei ~180–210 g Protein, deshalb ist Fett ≥ 86 g nur knapp erreichbar.
- [x] **Günstiger planen** (25.10.2026): `tools/planer.py` (Struktur aus Schichtplan, lokale Suche mit echten Packungskosten, Wiederholungsregeln, `--behalten`); Wiederholungsregeln auch in `pruefe_plan`; Einkaufsliste/App zeigen Einkauf, Verbrauch und Reste; Tests nutzen einen eingefrorenen Plan (`tests/daten/`); KW 45 neu: Einkauf 146,85 € (vorher 161 €), Verbrauch 97,82 €, Reste 49 €; 138 Tests. Befund: 100 € **Einkauf** sind mit Rezepten/Packungen/Protein ~190 g nicht erreichbar (Untergrenze ~145 €), der **Verbrauch** liegt unter 100 €.

- [x] **Start & visuell** (25.10.2026): Plan KW 44 (26.10.–1.11.) mit einmaligem Starteinkauf Mo 26.10. (`planer.py --einkauf`, art: start), Einkauf ca. 142 €; App: Makro-Ringe (Heute), Makro-Ring + Zielbalken (Rezept), Wochenkalender mit Schichtfarben und Diagrammen, Icons/Farben (Kategorien, Küchen, Abteilungen), Kostenbalken und Budget-Balken; Farben mit dataviz-Validator geprüft (hell/dunkel); eigene Rezepte per App-Formular über GitHub anlegen/löschen, Workflow prüft und baut vor dem Veröffentlichen; Tabs zeigen auf die aktuelle Woche; 146 Tests. **Am Sa 31.10.:** Reste aus KW 44 eintragen (`einkauf.py KW-44-2026 --reste-uebernehmen`), dann KW 45 neu planen.

- [x] **kcal-Obergrenze** (26.10.2026): pro Tag nie mehr als 2.275 kcal (Profil `kcal_ueber_ziel_max: 0`, `config.PLAN_KCAL_MIN/MAX`); Planer-Sicherheitsabstände verkleinert, 300 Starts; KW 44 (Einkauf ca. 153 €) und KW 45 (ca. 146 €) neu geplant; Faktor aus dem Plan auf Heute/Woche/Rezeptseite sichtbar; 148 Tests.

- [x] **Protein moderat & Meal Prep deutlich** (26.10.2026): Protein über Whey/Quark/Skyr gesenkt (max. halbe Menge, Fleischpackungen gleich), Ausgleich mit Fett bei gleichen kcal; Ø Frühstück 49→44 g P / 20,5→23,4 g F, Hauptgericht 62→60 g P / 26,3→27,5 g F; `config.PROTEIN_ZIEL_PRO_MAHLZEIT`; App: Karte „Heute für später vorkochen“ bzw. „Heute nichts vorkochen“, Hinweise je Mahlzeit (doppelt kochen → 2. Portion …, ↻ Rest von …, vorbereitet am …); KW 44 (Brownie Mo fest, ca. 139 €) und KW 45 (ca. 129 €) neu; 150 Tests. **Regel:** laufende/vergangene Tage nur auf ausdrücklichen Wunsch umplanen.

- [x] **Automatische Wochenplanung** (26.10.2026): `tools/woche_auto.py` + Workflow `woche-planen.yml` (freitags, auch manuell); ein Einkauf pro Woche (Sa davor); Reste automatisch in den Vorrat (einmal je Woche, mit Herkunftswoche, Ablauf beachtet); App: Einkauf-Tab = nächste anstehende Liste, „Heute einkaufen für KW …“ am Einkaufstag; KW 45 neu mit Resten aus KW 44 (Einkauf ca. 116 €); 157 Tests.

## Entscheidungen
Siehe `SPEC.md`, Abschnitt 16.
