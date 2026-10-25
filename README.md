# Rezeptbuch, Essensplaner und Einkaufsliste

Persönliches High-Protein-Rezeptbuch, Wochenplaner auf Basis der MacroFactor-Ziele und automatisch berechnete Einkaufsliste – als Dateien in diesem Ordner und als iPhone-Web-App.

**Web-App:** <https://mdbts9qghm-max.github.io/Chef/>

- Vorgabe: [`SPEC.md`](SPEC.md) · Arbeitsregeln und Fortschritt: [`CLAUDE.md`](CLAUDE.md) · Persönliche Werte: [`daten/profil.yaml`](daten/profil.yaml)
- Rezeptbuch als Datei: [`rezeptbuch.md`](rezeptbuch.md) · Wochenpläne: [`wochenplaene/`](wochenplaene/) · Einkaufslisten: [`einkaufslisten/`](einkaufslisten/)

## Was ist was
| Ordner / Datei | Inhalt | Von Hand ändern? |
|---|---|---|
| `daten/` | Quelle für alles: Rezepte (YAML), Wochenpläne, Zutaten, Packungen, Vorrat, Profil | ja (am besten über Claude) |
| `import/` | Screenshots, Texte und `links.txt` für neue Rezepte | ja, Dateien hineinlegen |
| `rezepte/`, `rezeptbuch.md`, `wochenplaene/`, `einkaufslisten/`, `web/` | generiert | **nein**, wird überschrieben |
| `tools/`, `tests/` | Programme und Tests | nur bei Entwicklung |

## Web-App auf dem iPhone
1. <https://mdbts9qghm-max.github.io/Chef/> in **Safari** öffnen.
2. **Teilen** (Quadrat mit Pfeil) → **Zum Home-Bildschirm** → **Hinzufügen**.
3. Die App funktioniert danach auch offline (einmal online öffnen, dann ist alles gespeichert).

| Ansicht | Was du dort machst |
|---|---|
| **Heute** | Schicht-Banner (☀️ Tag · 🌙 Nacht · 🏠 frei, 🛒 Einkauf, 🍱 Meal Prep), Mahlzeiten mit Uhrzeit, **4 Makro-Ringe** (grauer Bogen = Zielbereich, ✓ = im Ziel), Erinnerungen (z. B. Auftauen) |
| **Rezepte** | Suchen („lachs“), filtern (Mahlzeit, Kategorie, Küche), sortieren; Makro-Streifen und farbige Kategorien; **＋ Eigenes Rezept** |
| **Rezeptseite** | alle Abschnitte, Makro-Ring (Anteil Protein/Fett/KH), Anteil am Tagesziel, Portionsrechner (1–6), Varianten; **🗑 Rezept löschen** |
| **Kochmodus** | Schritt für Schritt groß, Timer mit Ton, Bildschirm bleibt an |
| **Woche** | Wochenleiste in Schichtfarben, Diagramme kcal/Protein/Fett pro Tag mit Zielbereich, Tageskarten mit 📦 Box · ↻ Rest · ❄️ Auftauen |
| **Einkauf** | Liste nach Abteilungen, Haken bleiben gespeichert, „Zurücksetzen“ für die nächste Woche; **Budget** direkt eintragen, die App zeigt sofort, ob die Woche hineinpasst |

## Eigene Rezepte hinzufügen und löschen
1. **Rezepte → ＋ Eigenes Rezept:** Name, Mahlzeit, Küche, Zeiten; Zutaten aus der Liste wählen und Gramm (für 2 Portionen) eintragen; ein Schritt pro Zeile. Die App rechnet die Nährwerte pro Portion sofort und zeigt, ob das Gericht in den Korridor passt.
2. **Auf GitHub speichern** → GitHub öffnet sich mit der fertigen Rezeptdatei → **„Commit changes“** tippen (einmalig bei GitHub angemeldet sein).
3. GitHub prüft das Rezept und baut die App neu – nach 1–2 Minuten ist es im Rezeptbuch und steht dem Planer zur Verfügung. Der Entwurf bleibt bis dahin auf dem iPhone gespeichert.
4. **Löschen:** auf der Rezeptseite „🗑 Rezept löschen“ → bei GitHub „Commit changes“. Steht das Rezept in einem aktuellen Plan, warnt die App – dann erst „tauschen“.
Zutat fehlt in der Liste? In Claude „Neue Zutat: …“ schreiben (dafür braucht es Nährwerte).

## MacroFactor
- **Link-Import:** In MacroFactor ein neues Rezept über den Import per Link anlegen und die Adresse der Rezeptseite einfügen (z. B. `https://mdbts9qghm-max.github.io/Chef/rezept/marry-me-chicken.html`). Die Seite enthält das Standard-Rezeptformat (schema.org/Recipe) mit Zutaten in Gramm, 2 Portionen und Nährwerten.
- **Ausweichlösung:** Auf der Rezeptseite **„Für MacroFactor kopieren“** tippen – kopiert eine Zutat pro Zeile (Gramm + Name) – und in MacroFactor einfügen.
- **Nach Gramm loggen:** Fertiges Gericht wiegen und als Gesamtgewicht eintragen. Die Rezeptseite nennt das geschätzte Gargewicht als Orientierung.

## Wochenrhythmus
1. **Samstag:** „Woche planen“ → der Planer stellt eine regelkonforme, möglichst günstige Woche zusammen (gleiches Frühstück/gleicher Snack darf 2× vorkommen, Reste werden mitgeplant) → Einkaufsliste → einkaufen (nur samstags).
   Wünsche (z. B. „Sonntag Marry Me Chicken“) bleiben fest stehen, der Rest wird darum herum geplant.
2. **Meal Prep** am letzten freien Tag vor der Tagschicht (steht im Plan, mit Zeitplan).
3. **Tagschicht (7–19 Uhr):** Boxen für Frühstück + Mittag · **Nachtschicht (19–7 Uhr):** Box für das Abendessen (Mikrowelle).
4. Eingefrorenes Fleisch/Fisch: Auftau-Erinnerung erscheint am Vortag unter **Heute**.
5. Nach dem Kochen bewerten, damit der Planer lernt, was gut ankommt.
6. **Reste übernehmen:** Angebrochene Packungen wandern in den Vorrat und werden in der nächsten Woche zuerst verplant – so sinkt der Einkauf Richtung Verbrauch. Die Einkaufsliste zeigt beides: *Einkauf* und *davon verbraucht*.

## Befehle im Alltag (einfach an Claude schreiben)
| Befehl | Beispiel | Was passiert |
|---|---|---|
| **Woche planen** | „Woche planen KW 46“ | Wochenplan + Einkaufsliste |
| **tauschen [Tag] [Mahlzeit]** | „tauschen Mittwoch Abend“ | Mahlzeit ersetzen, Makros + Einkaufsliste neu |
| **was koche ich heute** | | heutige Mahlzeiten mit Zeitplan und Link zum Kochmodus |
| **Import** | Screenshots nach `import/` legen, dann „Import“ | Rezepte in eigenen Worten übernehmen, an Makros angepasst |
| **Import: [Link oder Text]** | „Import: https://…“ | einzelnes Rezept direkt übernehmen |
| **Kühlschrank: [Zutaten]** | „Kühlschrank: Hähnchen, Reis, Skyr“ | 3 passende Gerichte mit Portionsfaktor für den Rest des Tages |
| **bewerten [Rezept] [Sterne] [Kommentar]** | „bewerten Marry Me Chicken 4 etwas mehr Sauce“ | Bewertung speichern, Rezept ggf. anpassen; 1–2 Sterne = aussortiert |
| **neue Rezepte** / **Küche: [Name]** / **trending** | „Küche: Koreanisch“ | neue Rezeptvorschläge |
| **anpassen [Rezept]** | „anpassen Bananenbrot süßer“ | Rezept ändern, Nährwerte neu |
| **Ziele: [kcal, P, F, KH]** | „Ziele: 2200, 150, 95, 185“ | neue Ziele aus MacroFactor, Pläne neu prüfen |
| **Vorrat** | „Vorrat: Olivenöl leer“ | `vorrat.yaml` anzeigen/aktualisieren |
| **Budget: [€]** | „Budget: 150“ | Budget für die Planung setzen (in der App änderst du es nur für die Anzeige auf deinem iPhone) |
| **Web-App aktualisieren** | | prüfen, generieren, testen, veröffentlichen |

## Veröffentlichen (GitHub Pages)
**Einmalig einrichten:**
1. Auf github.com das Repository **Chef** öffnen → **Settings** → links **Pages**.
2. Unter **Build and deployment** bei **Source** **GitHub Actions** auswählen (kein Speichern nötig).
3. Oben auf **Actions** → Workflow **Pages** → **Run workflow** → **Run workflow** (oder auf den nächsten Push warten).
4. Nach ca. 1 Minute (grüner Haken) ist die Seite unter <https://mdbts9qghm-max.github.io/Chef/> erreichbar.

**Danach automatisch:** Jeder Push auf `main`, der `web/` ändert, veröffentlicht neu (Workflow `.github/workflows/pages.yml`).
Was veröffentlicht wird, steht in `daten/profil.yaml` unter `veroeffentlichen` (z. B. `wochenplaene: false`, wenn Pläne nicht öffentlich sein sollen). Hinweis: Das Repository selbst ist öffentlich, also auch `daten/`.

## Für Entwicklung
```bash
pip install -r requirements.txt               # pyyaml, pytest, playwright
python3 tools/veroeffentlichen.py             # „Web-App aktualisieren“: prüfen → generieren → bestand → Tests
python3 tools/veroeffentlichen.py --live      # Live-Seite prüfen (erreichbar, JSON-LD vollständig)
python3 tools/pruefen.py                      # alle Prüfungen
python3 tools/generieren.py                   # Markdown + Web-App
python3 tools/wochenplan.py KW-45-2026        # Wochenplan prüfen + Markdown
python3 tools/planer.py KW-46-2026 --budget 100   # Woche automatisch planen (--behalten: „fest: true“-Einträge bleiben)
python3 tools/einkauf.py KW-45-2026           # Einkaufsliste (--reste-uebernehmen)
python3 tools/importieren.py                  # Neues in import/
python3 tools/kuehlschrank.py "Hähnchen, Reis" --gegessen 1150,85,45,110
python3 tools/bewerten.py marry-me-chicken 4 "etwas mehr Sauce"
python3 -m pytest                             # Tests
```

## Hinweis
Nährwerte sind berechnete Schätzwerte auf Basis von Durchschnittswerten und können je nach Produkt abweichen. Die Pläne sind eine Empfehlung und ersetzen keine Ernährungs- oder ärztliche Beratung.
