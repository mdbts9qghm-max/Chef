# CLAUDE.md – Arbeitsregeln für das Rezeptbuch

Vollständige Vorgabe: `SPEC.md` (bei Unklarheit dort nachlesen; bei Widersprüchen **fragen, nicht raten**). Persönliche Werte: `daten/profil.yaml`.

## Leitsatz
Jedes Rezept so genau, dass man es ohne Nachdenken nachkochen kann. **Jede Zahl wird gerechnet, nie geschätzt.** Geschmack und Alltag vor perfekten Makros, aber **Protein hat immer Priorität**.

## Datenmodell
- **Single Source of Truth:** `daten/` (YAML/CSV). Rezepte in `daten/rezepte/<id>.yaml`, Pläne in `daten/wochenplaene/KW-XX-JJJJ.yaml`, Vorrat in `daten/vorrat.yaml`.
- **Generiert, nie von Hand bearbeiten:** `rezepte/`, `rezeptbuch.md`, `wochenplaene/*.md`, `einkaufslisten/`, `web/`.
- Mengen in Texten nur über Platzhalter: `{zutat_id}` = Menge + Name, `{zutat_id:n}` = nur Name. Jede Zutat kommt mindestens einmal im Text vor.
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
- **Planung (8.2):** P ≥ 145 g · kcal ± 100 · F ± 15 (nie < 70) · KH ± 20. Abends keine gleiche Küche/Proteinquelle an Folgetagen. 1–2 Sterne nie, 3 Sterne max. 1×/Woche. Einkauf nur **Samstag** ⇒ Fisch/Garnelen/Hack frisch nur Sa–Mo, danach TK + Auftau-Erinnerung. Anpassen: `faktor` (0,25er-Schritte, max. 1,5) → Snack → einfaches Extra.
- **Auswärts:** Platzhalter 950 kcal / 40 P / 45 F / 90 KH, Rest des Tages proteinreich + fettarm, keine Zutaten auf der Liste.
- **Einkaufsliste:** berechnet (nie geschrieben), Vorrat abziehen, auf Packungen runden, nach Abteilungen, Kosten vs. Budget 100 €, Reste → `vorrat.yaml`, Kontrollrechnung.
- **Import:** eigene Worte, keine Texte/Fotos aus Posts übernehmen; Unklares gesammelt in einer Liste nachfragen.

## Arbeitsweise
- Jede Phase im **Plan-Modus** starten, OK abwarten. Am Ende: Prüfungen + Tests, Fortschrittsliste aktualisieren, Git-Commit vorschlagen (erst nach OK committen/pushen).
- Nach jeder Datenänderung: `python3 tools/pruefen.py` → `python3 tools/generieren.py` → ggf. veröffentlichen.

## Befehle (Entwicklung)
```bash
pip install -r requirements.txt          # pyyaml, pytest, playwright (Chromium ist vorinstalliert)
python3 tools/pruefen.py                 # alle Prüfungen (SPEC 12.1)
python3 tools/generieren.py              # Markdown + Web-App erzeugen
python3 tools/einkauf.py KW-44-2026      # Einkaufsliste aus Wochenplan
python3 -m pytest                        # Tests (SPEC 12.2)
```

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
| **Web-App aktualisieren** | generieren, prüfen, veröffentlichen |

## Fortschritt
- [x] **Phase 1 – Planung & Onboarding** (22.10.2026): Onboarding, SPEC.md, CLAUDE.md, profil.yaml, Ordnergerüst, Git
- [ ] **Phase 2 – Grundlagen:** zutaten.csv, packungen.csv, config.py, naehrwerte.py, pruefen.py, generieren.py (Markdown), Tests, 2 Beispielrezepte zur Abnahme
- [ ] **Phase 3 – Rezeptliste:** rezeptplan.md mit 50 Gerichten, Abgleich 5.1–5.3, OK abwarten
- [ ] **Phase 4 – Rezepte schreiben:** Runde 1/5 · 2/5 · 3/5 · 4/5 · 5/5, Abschlussübersicht
- [ ] **Phase 5 – Wochenplanung & Einkauf:** einkauf.py, Wochenplan-Generierung, Tests, erster echter Wochenplan
- [ ] **Phase 6 – Web-App:** Ansichten 10.2, JSON-LD, MacroFactor-Button, PWA, Playwright-Screenshots
- [ ] **Phase 7 – Import & Komfort:** Import, Kühlschrank-Modus, Bewertungen
- [ ] **Phase 8 – Livegang:** GitHub Pages (Achtung: privates Repo braucht bezahlten Plan, sonst Repo öffentlich), MacroFactor-Test, README

## Entscheidungen
Siehe `SPEC.md`, Abschnitt 16.
