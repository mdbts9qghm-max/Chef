# SPEC: Rezeptbuch, Essensplaner und Einkaufsliste

Diese Datei ist die vollständige Vorgabe für mein Rezeptbuch-Projekt. Lies sie komplett, bevor du planst, Rezepte schreibst oder Code erstellst. Wenn etwas unklar oder widersprüchlich ist, frag nach, statt zu raten.

---

## 1. Ziel des Projekts

Ein persönliches, sehr ausführliches **Rezeptbuch mit 50 Rezepten**, ein **Wochenplaner**, der meine Makroziele trifft, und eine **automatisch berechnete Einkaufsliste**. Alles liegt als Dateien in diesem Ordner und ist zusätzlich als **Web-App auf dem iPhone (Safari, zum Home-Bildschirm hinzufügbar)** nutzbar. Rezepte lassen sich per Link in **MacroFactor** importieren.

Leitsatz: **Jedes Rezept muss so genau sein, dass ich es ohne Nachdenken nachkochen kann, und jede Zahl muss gerechnet sein, nicht geschätzt.** Geschmack und Alltagstauglichkeit gehen vor Perfektion bei den Makros, aber Protein hat immer Priorität.

---

## 2. Mein Profil

- **Ziel:** Muskelaufbau bei gleichzeitigem Fettabbau (Body Recomposition)
- **Gewicht:** 82 kg
- **Tagesziele** (aus MacroFactor, Stand 20.10.2026):

| Kalorien | Protein | Fett | Kohlenhydrate |
|---|---|---|---|
| 2.275 kcal | 149 g | 101 g | 191 g |

- **Mahlzeiten pro Tag:** Frühstück, Mittagessen, Abendessen. Snacks nur, um Lücken zu füllen.
- **Haushalt:** 2 Personen. Jedes Rezept ergibt **2 gleich große Portionen**. Die Nährwerte gelten **pro Portion = meine Portion**. Person 2 isst einfach mit, ihre Makros werden nicht gezählt.
- **Tracking:** MacroFactor (iPhone)
- **Vorrat, Ausstattung, Supermarkt, Budget:** im Onboarding abfragen (Abschnitt 13, Phase 1) und in `daten/profil.yaml` speichern.

### 2.1 Vorlieben (harte Regeln)

| Regel | Bedeutung |
|---|---|
| **Frühstück ist süß** | Ich liebe süßes Frühstück: Frühstücks-Brownie, Protein-Joghurt-Bowls, Pancakes, Waffeln, Baked Oats, Overnight Oats, Kaiserschmarrn, Milchreis, Quarkspeisen. **Alle Frühstücke sind süß.** Herzhaftes Frühstück nur, wenn ich es ausdrücklich wünsche. |
| **Süß, aber proteinreich** | Süße kommt aus Obst, Honig, Whey, Kakao, Zimt, Vanille oder Süßstoff. Wenig zugesetzter Zucker (Richtwert: max. 20 g Zucker gesamt pro Frühstücksportion). |
| **Wenig Gemüse** | Gemüse sparsam einsetzen, nie als Hauptbestandteil. Proteinquelle, Sättigungsbeilage und Sauce stehen im Mittelpunkt. Kleine Mengen für Geschmack und Farbe sind okay (Zwiebel, Knoblauch, Tomate, etwas Paprika). |
| **Alltagstauglich** | Zutaten aus normalen deutschen Supermärkten. Exotisches (z. B. Gochujang) nur, wenn es lange haltbar ist und in mehreren Rezepten vorkommt. |
| **Geschmack zählt** | Gute Gewürze, Saucen, Röstaromen und Texturen. Kein „Fitness-Essen“, das nach Verzicht schmeckt. |

Alle Werte dieses Abschnitts sind in `daten/profil.yaml` hinterlegt und änderbar. Wenn ich neue Makroziele nenne, aktualisierst du die Datei und rechnest betroffene Pläne neu.

---

## 3. Zielwerte pro Mahlzeit

Damit drei Mahlzeiten (plus ggf. ein Snack) meine Tagesziele treffen, gelten diese Korridore **pro Portion**:

| Mahlzeit | kcal | Protein | Hinweis |
|---|---|---|---|
| Frühstück (süß) | 500–650 | mind. 35 g | |
| Hauptgericht Mittag/Abend | 600–850 | mind. 45 g | |
| Kalorienarmes Hauptgericht | max. 550 | mind. 35 g | für Auswärtstage und Tage mit Spielraum |
| Snack / Dessert (süß) | 200–350 | mind. 20 g | zum Auffüllen |

Rechenbeispiel: 600 (Frühstück) + 750 + 750 (Hauptgerichte) + 200 (Snack) = 2.300 kcal.

---

## 4. Kategorien und Küchen

### 4.1 Kategorien (werden aus den berechneten Werten vergeben, nicht geschätzt)

| Kategorie | Kriterium |
|---|---|
| **High Protein** | mind. 40 g Protein pro Portion **oder** mind. 10 g Protein pro 100 kcal |
| **Schnelle Rezepte** | Gesamtzeit (Vorbereitung + Kochen) max. 25 Minuten |
| **Meal Prep** | mind. 3 Tage im Kühlschrank haltbar und gut aufwärmbar (bzw. kalt essbar) |
| **Kalorienarm** | Hauptgericht mit max. 550 kcal und mind. 35 g Protein |
| **Frühstück & Snacks** | Mahlzeit ist Frühstück, Snack oder Dessert |

- Ein Rezept hat **eine Hauptkategorie** (bestimmt den Ordner) und beliebig viele weitere.
- „High Protein“, „Schnelle Rezepte“ und „Kalorienarm“ vergibt das Skript automatisch anhand der Kriterien. Ist die Hauptkategorie nicht erfüllt, ist das ein Fehler (Rezept anpassen, nicht Kategorie).
- Neue Kategorien schlage ich vor; du ergänzt sie hier und in der Konfiguration.

### 4.2 Länderküchen

| Küche | Beispiele |
|---|---|
| Deutsch | Schnitzel, Gulasch, Frikadellen, Kartoffelgerichte, Kaiserschmarrn |
| Italienisch | Pasta, Lasagne, Gnocchi, Piccata, Tiramisu |
| Asiatisch | Chinesisch, Japanisch, Koreanisch, Thai, Vietnamesisch |
| Mexikanisch | Burritos, Bowls, Tacos, Quesadillas, Chili |
| Indisch | Curry, Tandoori, Butter Chicken |
| Griechisch & Mediterran | Gyros, Souvlaki, Tzatziki-Bowls |
| Türkisch & Orientalisch | Köfte, Döner-Bowl, Shakshuka |
| Amerikanisch | Burger, BBQ, Pancakes, Waffeln, Brownies |
| International / Fusion | alles, was nicht klar zuzuordnen ist |

Klassiker gern als High-Protein-Version neu interpretieren (z. B. Lasagne mit Magerquark statt Béchamel, Butter Chicken mit Skyr statt Sahne).

### 4.3 Inspiration aus TikTok und Instagram
- **Keine eigene Kategorie**, sondern Inspirationsquelle. Vor allem bei **High Protein** und **Frühstück** Rezepte, wie sie oft auf TikTok und Instagram gepostet werden: Frühstücks-Brownie, Baked Oats, Protein-Pancakes, Cottage-Cheese-Rezepte, Skyr-Desserts, Wrap-Hacks aus der Pfanne, Burrito Bowls, Smash Burger, Marry Me Chicken, High-Protein-Pasta.
- Jedes so inspirierte Rezept hat das Feld **Inspiration**: worauf es basiert und was du für bessere Makros geändert hast (z. B. „Sahne durch Frischkäse light und Milch ersetzt, spart ca. 250 kcal pro Portion“).
- Keine Texte oder Fotos aus Posts übernehmen. Rezepte immer in eigenen Worten nach meiner Vorlage schreiben.

---

## 5. Der Startbestand: 50 Rezepte

### 5.1 Verteilung (exakt so)

| Bereich | Anzahl | Vorgaben |
|---|---|---|
| **Frühstück, süß** | 15 | mind. 4 Meal-Prep-tauglich, mind. 5 schnell (max. 25 min) |
| **Snacks & Desserts, süß** | 5 | auch als Nachtisch geeignet |
| **Hauptgerichte** | 30 | Verteilung auf Küchen siehe 5.2 |
| **Gesamt** | **50** | |

Ideen für Frühstück (fachlich sauber ausbauen, Dopplungen vermeiden): Frühstücks-Brownie (Baked Oats Schoko), Protein-Joghurt-Bowl mit Granola und Beeren, Protein-Pancakes, Protein-Waffeln, Overnight Oats in 2–3 Sorten (z. B. Cheesecake, Apfelstrudel, Erdnuss-Banane), Quark-Auflauf mit Kirschen, Protein-French-Toast, Protein-Kaiserschmarrn, Protein-Milchreis, Protein-Grießbrei, Bananenbrot (Meal Prep), Protein-Muffins (Meal Prep), Protein-Crêpes, Skyr-Tiramisu-Bowl.

Ideen für Snacks: Protein-Mousse au Chocolat, Skyr-Cheesecake im Glas, Protein-Eis aus TK-Beeren („Nice Cream“), Protein-Balls, Quarkcreme mit Obst.

### 5.2 Hauptgerichte nach Küche

| Küche | Anzahl |
|---|---|
| Deutsch | 4 |
| Italienisch | 5 |
| Asiatisch | 5 |
| Mexikanisch | 3 |
| Indisch | 3 |
| Griechisch & Mediterran | 3 |
| Türkisch & Orientalisch | 3 |
| Amerikanisch | 3 |
| International / Fusion | 1 |
| **Summe** | **30** |

### 5.3 Mindestanforderungen über alle 50

| Anforderung | Mindestwert |
|---|---|
| Meal Prep | 12 Rezepte |
| Schnelle Rezepte | 15 Rezepte |
| Kalorienarme Hauptgerichte | 6 |
| High Protein | möglichst alle, mind. 45 |
| Mit TikTok/Instagram-Inspiration | 15 |
| Gleiche Proteinquelle als Hauptprotein | max. 10 Hauptgerichte (Hähnchen, Pute, Rind, Fisch und Garnelen, Eier, Skyr/Quark/Hüttenkäse abwechseln) |

- Keine zwei Rezepte, die sich nur minimal unterscheiden. Varianten gehören in den Abschnitt „Varianten & Austausch“.
- Die Gesamtzutatenliste soll überschaubar bleiben: lieber eine Zutat in mehreren Rezepten nutzen als für jedes Rezept etwas Neues kaufen. Ziel: max. ca. 90 verschiedene Zutaten in `zutaten.csv`.
- Falls beim Start bereits Rezepte im Ordner liegen, zählen sie zu den 50, sofern sie den Regeln entsprechen (herzhafte Frühstücke zählen nicht als Frühstück, sondern werden gefragt: behalten, umbauen oder löschen).

---

## 6. Datenmodell (wichtige Designentscheidung)

**Rezepte, Wochenpläne und Vorrat sind strukturierte Daten (YAML), nicht Freitext.** Markdown-Dateien und die Web-App werden daraus generiert. Nur so können Nährwerte, Kategorien, Einkaufslisten und der MacroFactor-Export zuverlässig berechnet und geprüft werden.

### 6.1 Ordnerstruktur

```
SPEC.md                         ← diese Datei
CLAUDE.md                       ← Arbeitsregeln und Fortschrittsliste (legst du in Phase 1 an)
README.md                       ← Anleitung für mich
daten/
  profil.yaml                   ← Makroziele, Vorlieben, Ausstattung, Supermarkt, Budget
  zutaten.csv                   ← Nährwert-Datenbank pro 100 g
  packungen.csv                 ← Packungsgrößen, Abteilung, Preis (optional)
  vorrat.yaml                   ← was ich zu Hause habe, inkl. Reste der letzten Woche
  rezepte/<id>.yaml             ← ein Rezept pro Datei (Single Source of Truth)
  wochenplaene/KW-XX-JJJJ.yaml  ← Wochenplan als Daten
tools/
  naehrwerte.py                 ← Nährwerte berechnen
  pruefen.py                    ← alle Prüfungen aus Abschnitt 12
  generieren.py                 ← Markdown + Web-App erzeugen
  einkauf.py                    ← Einkaufsliste aus Wochenplan berechnen
  config.py                     ← alle Schwellenwerte und Toleranzen, kommentiert
tests/                          ← pytest
rezepte/<hauptkategorie>/<id>.md   ← generiert, nicht von Hand bearbeiten
rezeptbuch.md                   ← generiertes Inhaltsverzeichnis
wochenplaene/KW-XX-JJJJ.md      ← generiert
einkaufslisten/KW-XX-JJJJ.md    ← generiert
import/                         ← Screenshots, Texte, links.txt (Abschnitt 9)
  erledigt/
web/                            ← generierte Web-App (Abschnitt 10)
```

### 6.2 Zutaten-Datenbank `daten/zutaten.csv`

Spalten: `zutat, kcal, protein, fett, gesaettigt, kh, zucker, ballaststoffe, salz, garfaktor`

- Werte **pro 100 g Rohgewicht** bzw. so, wie die Zutat verwendet wird (z. B. „Basmatireis ungekocht“, „Kidneybohnen abgetropft“, „Ei Gr. M ohne Schale“).
- Quellen: Bundeslebensmittelschlüssel (BLS), USDA oder typische Herstellerangaben deutscher Supermarktprodukte. Bei Markenprodukten mit großer Streuung (z. B. Whey, Protein-Pudding) einen typischen Wert nehmen und in einer Kommentarzeile vermerken.
- `garfaktor`: Gewicht nach dem Garen / Rohgewicht (z. B. Reis 2,8, Hähnchen 0,75, Zwiebel 0,7). Dient der Schätzung des Gargewichts zum Portionieren.
- Namen sind eindeutig und konkret. Keine Zutat ohne Fettstufe, wo es darauf ankommt („Rinderhackfleisch 5 % Fett roh“, nicht „Hackfleisch“).

### 6.3 Packungen `daten/packungen.csv`

Spalten: `zutat, abteilung, packung_g, packung_text, preis_eur (optional), haltbar_tage_offen`

Beispiel: `Magerquark, Kühlregal & Milchprodukte, 250, 250-g-Becher, 0.79, 4`

### 6.4 Rezept-Schema `daten/rezepte/<id>.yaml`

```yaml
id: fruehstuecks-brownie              # kebab-case, eindeutig
name: Frühstücks-Brownie
hauptkategorie: fruehstueck-snacks    # high-protein | schnell | meal-prep | kalorienarm | fruehstueck-snacks
kategorien_manuell: [Meal Prep]       # nur „Meal Prep“, die anderen berechnet das Skript
mahlzeit: Frühstück                   # Frühstück | Mittag/Abend | Snack
geschmack: süß                        # süß | herzhaft
kueche: Amerikanisch
inspiration:                          # optional
  quelle: "TikTok-Trend „Breakfast Brownie“"
  link: null
  aenderungen: "Mehl durch Haferflocken, Zucker durch Banane und Whey ersetzt"
schwierigkeit: leicht                 # leicht | mittel | aufwendig
zeit: {vorbereitung: 10, kochen: 25, wartezeit: 0}   # Minuten
ausstattung: [Ofen, Mixer, "Auflaufform 20 × 20 cm"]
zutaten:
  - gruppe: Teig
  - {id: hafer, zutat: Haferflocken, g: 120, anzeige: null, hinweis: "zarte"}
  - {id: eier, zutat: "Ei Gr. M ohne Schale", g: 120, anzeige: "2 Stück Gr. M", hinweis: ""}
mise_en_place:
  - "Ofen auf 180 °C Ober-/Unterhitze (160 °C Umluft) vorheizen."
schritte:
  - {titel: Mixen, text: "{hafer}, {eier} … 30 Sekunden mixen.", timer_min: null}
  - {titel: Backen, text: "… 22–25 Minuten backen …", timer_min: 25}
zeitablauf: ["Während der Ofen vorheizt: mixen und einfüllen."]
fehler: ["Zu lange gebacken: wird trocken. Lieber 2 Minuten früher raus."]
anrichten: "…"
aufbewahrung: {kuehlschrank_tage: 3, einfrierbar: true, einfrieren_monate: 1, aufwaermen: "Mikrowelle 600 W, 60–90 s"}
varianten: ["**Mehr Protein:** 100 g Skyr extra (+32 kcal, +5,5 g Protein pro Portion)."]
tipps: ["…"]
gargewicht_g: null                    # optional gemessen, sonst aus garfaktor geschätzt
bewertung: {sterne: null, kommentar: null, datum: null}
```

**Platzhalter in Texten:** `{zutat_id}` wird beim Generieren durch Menge + Name ersetzt (z. B. „120 g Haferflocken“, „2 Eier (120 g)“), `{zutat_id:n}` nur durch den Namen. So sind Mengen in Zutatenliste und Schritten **immer identisch**. Jede Zutat muss mindestens einmal in Mise en place, Schritten oder Anrichten vorkommen.

### 6.5 Wochenplan-Schema `daten/wochenplaene/KW-XX-JJJJ.yaml`

```yaml
kw: 44
jahr: 2026
einkauf: [{tag: Sa, datum: 2026-10-31, art: gross}, {tag: Mi, datum: 2026-11-04, art: frisch}]
tage:
  - datum: 2026-11-02
    fruehstueck: {rezept: fruehstuecks-brownie, faktor: 1.0, quelle: "Meal Prep vom So"}
    mittag: {rezept: burrito-bowl, faktor: 1.0, quelle: "Rest vom So-Abend"}
    abend: {rezept: marry-me-chicken, faktor: 1.0, kochen: true}
    snack: null
    auswaerts: null                   # z. B. {mahlzeit: abend, platzhalter_kcal: 950}
```

`faktor` skaliert ein Rezept für diesen Tag (z. B. 1,25). `kochen: true` heißt, an diesem Tag wird gekocht; Reste werden mit `quelle` verknüpft.

---

## 7. Rezept-Qualitätsstandard (harte Regeln)

Jedes generierte Rezept (`rezepte/<kategorie>/<id>.md`) hat genau diese Abschnitte in dieser Reihenfolge:

1. **Kopf:** Name, Bewertung, Kategorien, Küche, Inspiration (falls vorhanden), Mahlzeit, Portionen (2), Schwierigkeit, Zeit (Vorbereitung · Kochen · Wartezeit · Gesamt), Ausstattung
2. **Nährwerte pro Portion:** kcal, Protein, Fett, davon gesättigt, Kohlenhydrate, davon Zucker, Ballaststoffe, Salz; dazu Anteil am Tagesziel in %, Protein pro 100 kcal, Makroverteilung in %, **Gewicht fertig gesamt und pro Portion** (zum Abwiegen)
3. **Zutaten (für 2 Portionen):** Tabelle Zutat | Menge | Hinweis, mit Gruppen (z. B. Teig, Topping). Mengen in Gramm (Rohgewicht/ungekocht), Stückangaben zusätzlich („2 Stück Gr. M (120 g)“)
4. **Mise en place:** alles, was vorab passiert: vorheizen, schneiden (mit Schnittgröße, z. B. „2 cm Würfel“), abwiegen, auftauen, marinieren
5. **Zubereitung:** nummerierte Schritte mit Titel. In jedem Schritt: **Herdstufe** (z. B. „Stufe 6 von 9“), **Ofentemperatur und Modus** (Ober-/Unterhitze und Umluft), Topf- oder Pfannengröße, **Zeit** und **woran man erkennt, dass es fertig ist** (Farbe, Konsistenz, Kerntemperatur)
6. **Zeitablauf:** was parallel läuft („Während der Reis kocht: Sauce anrühren“), wenn sinnvoll
7. **Häufige Fehler:** 2–4 typische Fehler mit Ursache und Lösung
8. **Anrichten:** wie die Portion auf den Teller oder in die Meal-Prep-Box kommt, mit Gramm pro Portion
9. **Meal Prep & Aufbewahrung:** Kühlschrank-Tage, einfrierbar ja/nein und wie lange, Aufwärmen (Gerät, Leistung, Dauer), was separat gelagert wird
10. **Varianten & Austausch:** 2–4 Varianten mit Makro-Änderung pro Portion (andere Proteinquelle, mehr/weniger kcal, andere Beilage)
11. **Tipps:** 1–3 Profi-Tipps für Geschmack und Gelingen
12. **Nährwert-Berechnung:** Tabelle pro Zutat (Menge, kcal, Protein, Fett, KH), Summe, pro Portion, Ergebnis des Plausibilitätschecks, Hinweis „Schätzwerte“

### 7.1 Inhaltliche Regeln
- **Exakte Mengen für alles**, auch Gewürze, Öl, Flüssigkeiten. Kein „etwas“, kein „nach Geschmack“ ohne Richtwert. Salz fürs Kochwasser wird genannt, aber als „nicht mitgerechnet“ markiert.
- **Öl, Butter und Saucen werden vollständig mitgezählt.**
- **Kerntemperaturen:** Geflügel 74 °C, Hackfleisch 72 °C, Schweinefilet 63 °C, Lachs 50–55 °C (glasig) bzw. 60 °C (durch). Bei Schmorgerichten: Garprobe mit der Gabel.
- **Lebensmittelsicherheit bei Meal Prep:** Gerichte mit Fisch und Garnelen max. 2 Tage, alles andere max. 3–4 Tage gekühlt. Reis nach dem Kochen schnell abkühlen und innerhalb von 1 Stunde in den Kühlschrank.
- **Süße Frühstücke:** Textur und Geschmack beschreiben (z. B. „Mitte darf noch saftig sein, dann wird er brownie-artig“). Tipps, wie es noch mehr nach Dessert schmeckt, ohne viel Kalorien (Vanille, Zimt, Prise Salz, Kakao).
- **Realistische Zeiten:** Vorheizen, Quellen, Marinieren und Ruhen werden in der Gesamtzeit berücksichtigt (Marinieren über Nacht als `wartezeit`, nicht in „schnell“ mitzählen, aber deutlich markieren).
- **Selbstcheck vor dem Speichern:** alle Prüfungen aus Abschnitt 12.1 bestanden.

---

## 8. Wochenplanung und Einkaufsliste

### 8.1 Ablauf „Woche planen“
1. Kalenderwoche bestimmen (Standard: kommende Woche, ISO-Kalenderwoche, Montag bis Sonntag).
2. Kurz fragen: Welche Kategorien diesmal (Ja/Nein pro Kategorie)? Welche Küchen (mehrere oder „bunt gemischt“)? Besondere Wünsche? Tage mit wenig Zeit? **Auswärts-Termine?** Meal-Prep-Tag? Einkaufstage?
3. Plan erstellen: Frühstück, Mittag, Abend für Montag bis Sonntag.
4. Mit `tools/` Tagessummen, Einkaufsliste und Prüfungen rechnen. Bei Verstößen gegen 8.2 anpassen und neu rechnen, bis alles passt.
5. Wochenplan und Einkaufsliste speichern, generieren, mir eine kurze Übersicht zeigen.

### 8.2 Planungsregeln (harte Regeln)

| Regel | Wert |
|---|---|
| Protein pro Tag | **mind. 145 g** (Priorität 1) |
| Kalorien pro Tag | 2.275 kcal **± 100** (Priorität 2) |
| Fett pro Tag | 101 g ± 15 g, **nie unter 70 g** |
| Kohlenhydrate pro Tag | 191 g ± 20 g |
| Frühstück | immer süß (außer ich wünsche es anders) |
| Abendessen | nicht zweimal hintereinander dieselbe Küche (außer gewünscht) |
| Proteinquelle | nicht an zwei Tagen hintereinander dieselbe Hauptproteinquelle beim Abendessen |
| Bewertungen | 4–5 Sterne bevorzugt, 3 Sterne höchstens 1× pro Woche, **1–2 Sterne nie** |
| Frische | Fisch, Garnelen und Hackfleisch innerhalb von 2 Tagen nach dem Einkauf (sonst TK kaufen und im Plan „auftauen“ erinnern) |
| Meal Prep | Gericht nur so weit im Voraus, wie `aufbewahrung.kuehlschrank_tage` erlaubt |
| Reste | Wird abends gekocht, kann die zweite Portion-Ladung (Rezept × 2) mittags am Folgetag gegessen werden. Mengen dann im Plan verdoppeln. |

Wenn ein Tag nicht aufgeht, in dieser Reihenfolge anpassen:
1. Beilage oder Portion skalieren (`faktor`, in 0,25er-Schritten, max. 1,5)
2. einen der 5 Snacks ergänzen
3. ein einfaches Extra (z. B. 250 g Skyr mit Honig, Proteinshake mit Milch, 30 g Nüsse für Fett)

### 8.3 Auswärts- und Restaurant-Tage
- Auswärts-Mahlzeit wird nicht geplant, sondern mit **Platzhalter 900–1.000 kcal** (ca. 40 g Protein, 45 g Fett, 90 g KH) gerechnet.
- Die übrigen Mahlzeiten des Tages sind **proteinreich und fettarm** (bevorzugt kalorienarme Hauptgerichte und Skyr-/Quark-Frühstücke), damit ich trotzdem auf ca. 145 g Protein komme.
- Kurze Tipps für die Restaurantwahl (z. B. Steak mit Kartoffeln statt Pasta in Sahnesauce, Sauce extra).
- Keine Zutaten für diese Mahlzeit auf der Einkaufsliste.

### 8.4 Inhalt des Wochenplans (`wochenplaene/KW-XX-JJJJ.md`)
- **Übersichtstabelle:** Tag × Mahlzeit, mit Link zum Rezept, Zeitaufwand, kcal und Protein pro Mahlzeit
- **Pro Tag ein Abschnitt:**
  - Mahlzeiten inkl. Mengenanpassungen („Reis 90 g statt 75 g pro Portion“)
  - Tagessumme kcal / Protein / Fett / KH mit Abweichung zum Ziel in g und %
  - **Zeitplan** für Kochtage (z. B. „18:00 Ofen vorheizen, 18:10 Lachs rein, 18:35 essen“)
  - **Erinnerungen für morgen** (z. B. „Hähnchen aus dem Gefrierfach in den Kühlschrank“, „Overnight Oats ansetzen“, „Marinade ansetzen“)
- **Reste-Übersicht:** welches Gericht wie viele Portionen ergibt, wann welche gegessen wird, wie gelagert
- **Meal-Prep-Plan:** Schritt-für-Schritt-Ablauf für den Prep-Tag mit Reihenfolge (was zuerst in den Ofen, was parallel auf den Herd), Gesamtdauer und welche Box für welchen Tag
- **Wochenbilanz:** Durchschnitt der Makros und ehrliche Einschätzung, wie gut die Ziele getroffen wurden

### 8.5 Einkaufsliste (`einkaufslisten/KW-XX-JJJJ.md`)
Wird von `tools/einkauf.py` aus dem Wochenplan **berechnet**, nicht geschrieben.

- Mengen aller Rezepte der Woche × `faktor` addieren, gleiche Zutaten zusammenfassen.
- **Vorrat abziehen** (`daten/vorrat.yaml`). Bei Unsicherheit vorher fragen.
- Auf **Packungsgrößen** aus `packungen.csv` aufrunden.
- Nach **Abteilungen** sortieren: Obst & Gemüse · Fleisch & Fisch · Kühlregal & Milchprodukte · Brot & Backwaren · Trockenwaren · Konserven & Saucen · Gewürze & Öle · Tiefkühl · Sonstiges. Reihenfolge an meinen Supermarkt anpassbar (`profil.yaml`).
- Pro Zeile: **Produkt mit genauer Angabe** (Sorte, Fettstufe, TK/frisch) · **Bedarf → Kaufmenge** · **wofür** (z. B. „Hähnchenbrustfilet: 1.150 g → 3 × 400 g · Mo Abend, Di Mittag, Do Abend“) · Frische-Hinweis, wenn relevant.
- Als abhakbare Checkliste (`- [ ]`).
- Bei zwei Einkaufsterminen: getrennte Listen.
- Abschnitt **„Vorrat prüfen“** für Gewürze, Öl, Salz, Backpulver usw., die nur in kleinen Mengen gebraucht werden.
- **Reste nach der Woche:** was von angebrochenen Packungen übrig bleibt (z. B. „Feta: 50 g, offen haltbar bis Mi“). Diese Reste werden in `vorrat.yaml` eingetragen und in der nächsten Woche bevorzugt verplant.
- Wenn ein Budget angegeben ist: **Kostenschätzung** pro Abteilung und gesamt, mit Hinweis, wenn das Budget überschritten wird, und Sparvorschlägen.
- **Kontrollrechnung** am Ende: Summe aller Rezeptmengen = Summe Liste + Vorrat (Test in 12.2).

---

## 9. Rezepte importieren (Instagram und TikTok)

Ich will Rezepte, die ich auf Instagram oder TikTok finde, ins Rezeptbuch übernehmen.

### 9.1 Eingangswege
1. **Screenshots** (zuverlässigster Weg): Post und Bildunterschrift als Bilder in `import/`. Mehrere Bilder zu einem Rezept mit gleichem Namen und Nummer (`brownie-1.png`, `brownie-2.png`).
2. **Links:** eine Zeile pro Post in `import/links.txt` oder direkt im Chat.
3. **Text:** kopierte Bildunterschrift als `.txt` in `import/` oder direkt im Chat.

### 9.2 Ablauf bei „Import“
1. Alle neuen Dateien und Links durchgehen.
2. Screenshots ansehen und Zutaten, Mengen und Schritte herauslesen.
3. Links abrufen. **Instagram blockiert das oft** (Anmeldung nötig). Wenn es nicht klappt: kurz sagen und um Screenshot oder Text bitten, nicht raten.
4. Ungenaue Angaben umrechnen („1 Scoop“ → 30 g Whey, „1 Cup“ → Gramm je nach Zutat, „1 Dose“ → Abtropfgewicht). Was sich nicht klären lässt, sammeln und am Ende in **einer** Liste nachfragen.
5. Vollständiges Rezept nach Schema 6.4 und Standard 7 bauen, **in eigenen Worten**, an meine Makros angepasst (z. B. Sahne → Skyr oder Frischkäse light, mehr Protein, weniger Öl). Frühstück süß lassen bzw. machen.
6. Prüfen, ob es schon ein sehr ähnliches Rezept gibt. Wenn ja, fragen: Variante im bestehenden Rezept oder eigenes Rezept?
7. Prüfungen laufen lassen, generieren, Dateien nach `import/erledigt/` verschieben, Link in `links.txt` als erledigt markieren.
8. Kurze Zusammenfassung: importierte Rezepte mit kcal und Protein pro Portion, offene Fragen.

---

## 10. Web-App für Safari (iPhone)

### 10.1 Grundsätze
- **Statische Web-App**, komplett von `tools/generieren.py` aus den YAML-Daten erzeugt. HTML, CSS und Vanilla JavaScript, keine Build-Tools, keine Frameworks, keine externen Abhängigkeiten zur Laufzeit.
- **Mobile-first**, optimiert für iPhone in Safari. Heller und dunkler Modus (folgt dem System).
- **PWA:** Web-App-Manifest, Icons (180 × 180 Apple Touch Icon, 192 und 512), Service Worker für Offline-Nutzung. Über „Teilen → Zum Home-Bildschirm“ startet sie wie eine App (`display: standalone`).
- Große, gut lesbare Schrift, Tap-Flächen mind. 44 × 44 pt.
- Sprache Deutsch, Datumsformat TT.MM.JJJJ, Zeitzone Europe/Berlin, Zahlen mit Komma.

### 10.2 Ansichten
1. **Heute (Startseite):** Datum, die drei Mahlzeiten aus dem aktuellen Wochenplan mit kcal/Protein, Tagessumme gegen Ziel (Balken für kcal, Protein, Fett, KH), Erinnerungen für morgen, Link „Jetzt kochen“.
2. **Rezeptbuch:** Kacheln oder Liste, **Suche**, **Filter** nach Kategorie, Küche, Mahlzeit, Bewertung, max. Zeit; Sortierung nach Name, kcal, Protein, Zeit.
3. **Rezeptseite:** alle Abschnitte aus Standard 7, Portionsrechner (1–6 Portionen, Mengen skalieren live), Buttons „Kochmodus“ und „Für MacroFactor kopieren“.
4. **Kochmodus:** Vollbild, ein Schritt pro Ansicht, sehr große Schrift, Wischen/Tippen für vor und zurück, Zutaten des Schritts mit Mengen eingeblendet, **Timer** bei Schritten mit `timer_min` (mit Ton und Vibration, falls möglich), **Bildschirm bleibt an** (Screen Wake Lock API, mit stillem Fallback, wenn nicht unterstützt).
5. **Wochenplan:** Tage als Karten, Tagesmakros, Reste und Meal-Prep-Plan.
6. **Einkaufsliste:** nach Abteilungen, **Haken werden im Browser gespeichert** (localStorage, mit try/catch und Fallback), Button „Alle Haken zurücksetzen“, abgehakte Artikel wandern nach unten.

### 10.3 Export für MacroFactor
MacroFactor kann Rezepte per Link importieren und liest dabei das Standard-Rezeptformat von Websites.
- Jede Rezeptseite enthält **schema.org/Recipe als JSON-LD**: `name`, `recipeYield` („2 Portionen“), `recipeIngredient` (eine Zeile pro Zutat mit Grammangabe, z. B. „250 g Hähnchenbrustfilet roh“), `recipeInstructions` (HowToStep mit Text), `prepTime`/`cookTime`/`totalTime` (ISO 8601), `recipeCategory`, `recipeCuisine`, `nutrition` (NutritionInformation pro Portion: calories, proteinContent, fatContent, saturatedFatContent, carbohydrateContent, sugarContent, fiberContent, sodiumContent).
- Button **„Für MacroFactor kopieren“**: kopiert die Zutatenliste als einfachen Text (eine Zutat pro Zeile, Gramm + konkreter Name) in die Zwischenablage, als Ausweichlösung.
- Hinweis auf jeder Rezeptseite: „Fertiges Gericht wiegen und als Gesamtgewicht in MacroFactor eintragen, dann kannst du nach Gramm loggen.“ Mit dem geschätzten Gargewicht als Orientierung.
- Der Link-Import funktioniert nur, wenn die Web-App **öffentlich erreichbar** ist (Abschnitt 10.4).

### 10.4 Veröffentlichung
- Vorschlag: **GitHub Pages** (kostenlos), Veröffentlichung des Ordners `web/`.
- **Vorher fragen, ob die Seite öffentlich sein darf.** Die Inhalte sind unkritisch (Rezepte, Pläne), aber Wochenpläne zeigen, wann ich zu Hause koche. Option anbieten: Wochenpläne und Einkaufslisten nicht veröffentlichen, nur das Rezeptbuch.
- Jeden Schritt, den ich selbst auf GitHub machen muss, genau erklären (Repository anlegen, Pages aktivieren, URL).

---

## 11. Zusatzfunktionen

### 11.1 Kühlschrank-Modus („Kühlschrank: Hähnchen, Reis, Skyr …“)
- 2–3 Gerichte vorschlagen, die hauptsächlich diese Zutaten nutzen. Erst passende Rezepte aus dem Rezeptbuch, sonst neue.
- Fragen, was ich heute schon gegessen habe, und die Portion an meine **restlichen Makros des Tages** anpassen.
- Fehlende Zutaten max. 1–2 Basics, klar markiert.
- Gefällt mir ein neues Gericht, kommt es ins Rezeptbuch.

### 11.2 Bewertungen („bewerten [Rezept] [1–5 Sterne] [Kommentar]“)
- Sterne, Kommentar und Datum ins Rezept-YAML schreiben, neu generieren.
- Einfluss auf die Planung: siehe 8.2.
- Kommentare umsetzen: z. B. „zu trocken“ → Rezept anpassen (mehr Sauce, kürzere Garzeit) und mir die Änderung zeigen. „zu wenig süß“ → Süße erhöhen, Makros neu rechnen.
- 1–2 Sterne: Rezept bleibt erhalten, wird im Inhaltsverzeichnis als „aussortiert“ markiert und nicht mehr geplant.

### 11.3 Neue Rezepte und Anpassungen
- **„neue Rezepte“:** Kategorien per Ja/Nein und Küchen abfragen, dann 3–5 Rezepte.
- **„Küche: Italienisch“:** 3–5 neue Rezepte dieser Küche.
- **„anpassen [Rezept]“:** z. B. mehr Protein, weniger Fett, ohne Ofen; Nährwerte neu rechnen, Unterschied zeigen.
- **„trending“:** per Websuche aktuelle High-Protein-Trends von TikTok/Instagram suchen und 5 Ideen vorschlagen, die zu meinen Vorlieben passen.

---

## 12. Prüfungen und Tests (pytest)

### 12.1 Prüfungen pro Rezept (`tools/pruefen.py`, laufen vor jedem Generieren)
- Alle Zutaten existieren in `zutaten.csv`.
- **Plausibilität:** 4 × Protein + 4 × KH + 9 × Fett + 2 × Ballaststoffe weicht max. ±5 % von den kcal ab (pro Zutat und pro Rezept).
- Jede Zutat wird mindestens einmal im Text verwendet; jeder Platzhalter verweist auf eine existierende Zutat.
- Zielwerte der Mahlzeit aus Abschnitt 3 eingehalten.
- Hauptkategorie erfüllt ihr Kriterium; berechnete Kategorien stimmen.
- Frühstück hat `geschmack: süß` (Warnung statt Fehler, wenn bewusst herzhaft).
- Zucker pro Frühstücksportion max. 20 g (Warnung).
- Schritte mit Fleisch oder Fisch enthalten eine Kerntemperatur oder Garprobe.
- Ofenschritte enthalten Temperatur und Modus.
- Pflichtfelder vorhanden, `id` eindeutig, Dateiname = `id`.

### 12.2 Tests
Mindestens diese Szenarien:
- Nährwertberechnung für ein Testrezept mit bekannten Werten (inkl. Rundung)
- Plausibilitätscheck schlägt bei einer manipulierten Zutat an
- Platzhalter-Ersetzung: `{id}` und `{id:n}`, Stückangaben, „1 Prise“
- Kategorien: Grenzfälle (genau 25 min, genau 550 kcal, genau 40 g Protein, 10 g pro 100 kcal)
- Bestand: genau 50 Rezepte, Verteilung aus 5.1 und 5.2, Mindestwerte aus 5.3
- Wochenplan: jeder Tag erfüllt 8.2, Auswärts-Platzhalter wird korrekt gerechnet
- 1–2-Sterne-Rezepte werden nie geplant
- Fisch/Hack nicht später als 2 Tage nach dem Einkauf (ohne TK-Hinweis)
- Meal-Prep-Reste nie älter als die erlaubte Kühlschrankdauer
- Einkaufsliste: Summe Rezeptmengen = Liste + Vorrat (Kontrollrechnung), Aufrundung auf Packungen, Vorratsabzug, Auswärts-Mahlzeit erzeugt keine Zutaten, Reste landen in `vorrat.yaml`
- `faktor` skaliert Mengen und Makros korrekt
- JSON-LD jeder Rezeptseite ist gültiges JSON und enthält alle Felder aus 10.3
- Generierte Markdown-Dateien enthalten alle Abschnitte aus Standard 7 in der richtigen Reihenfolge
- Web-App: jede Seite lädt ohne JavaScript-Fehler im iPhone-Format (Playwright, Viewport 390 × 844), Einkaufsliste merkt sich Haken nach Neuladen, Kochmodus zeigt Schritt 1 bis n

---

## 13. Vorgehen

Arbeite in diesen Phasen. Beginne jede Phase im **Plan-Modus**, warte auf mein OK, prüfe am Ende Prüfungen und Tests, aktualisiere die Fortschrittsliste in der `CLAUDE.md` und schlage einen Git-Commit vor.

1. **Planung und Onboarding:**
   - Frag mich: Küchenausstattung (Ofen, Airfryer, Mixer, Waffeleisen, Reiskocher …), Supermarkt(e), Wochenbudget (optional), bevorzugte Einkaufstage, ob die Web-App öffentlich sein darf.
   - Beschreibe Datenmodell, Ordnerstruktur und Skripte. Noch keine Rezepte.
   - `CLAUDE.md` mit Arbeitsregeln (Kurzfassung dieser SPEC), Befehlen (Abschnitt 14) und Fortschrittsliste anlegen. `daten/profil.yaml` anlegen. Git einrichten.
2. **Grundlagen:** `zutaten.csv` (Startbestand), `packungen.csv`, `config.py`, `naehrwerte.py`, `pruefen.py`, `generieren.py` (nur Markdown) mit Tests. Zwei Beispielrezepte (1 süßes Frühstück, 1 Hauptgericht) zur Abnahme durch mich: Passt Stil und Ausführlichkeit?
3. **Rezeptliste:** `rezeptplan.md` mit allen 50 Gerichten (Name, Bereich, Küche, Hauptprotein, Ziel-kcal, Inspiration ja/nein) und Abgleich gegen 5.1 bis 5.3. **Warte auf mein OK**, ich tausche ggf. einzelne Gerichte.
4. **Rezepte schreiben:** **5 Runden à 10 Rezepten.** Nach jeder Runde: Prüfungen, Generieren, `rezeptbuch.md` aktualisieren, Einzeiler zum Fortschritt („Runde 2/5: 20 Rezepte, alle Prüfungen bestanden“). Verfehlt ein Rezept die Zielwerte: Mengen anpassen, nicht die Zielwerte. Am Ende: Übersicht (Anzahl pro Kategorie und Küche gegen Vorgabe, Durchschnittsmakros pro Mahlzeit, ein Beispieltag, der meine Ziele trifft).
5. **Wochenplanung und Einkauf:** `einkauf.py`, Wochenplan-Generierung, Tests. Dann den **ersten echten Wochenplan** für die kommende Woche mit mir zusammen erstellen (Fragen aus 8.1).
6. **Web-App:** alle Ansichten aus 10.2, JSON-LD, MacroFactor-Button, PWA. Teste selbst im iPhone-Format mit Playwright und zeig mir Screenshots von Heute, Rezeptseite, Kochmodus und Einkaufsliste.
7. **Import und Komfort:** Import (Abschnitt 9) mit einem Test-Screenshot, Kühlschrank-Modus, Bewertungen.
8. **Livegang:** GitHub Pages einrichten (Schritt für Schritt erklären), MacroFactor-Import mit einem Rezept gemeinsam testen, README mit Anleitung für den Alltag.

---

## 14. Befehle im Alltag (nach dem Aufbau)

| Befehl | Was passiert |
|---|---|
| **Woche planen** | Wochenplan + Einkaufsliste (Abschnitt 8) |
| **tauschen [Tag] [Mahlzeit]** | Mahlzeit ersetzen, Makros und Einkaufsliste neu rechnen |
| **was koche ich heute** | heutige Mahlzeiten mit Zeitplan und Link zum Kochmodus |
| **Import** | alles Neue aus `import/` übernehmen (Abschnitt 9) |
| **Import: [Link oder Text]** | einzelnes Rezept direkt aus dem Chat übernehmen |
| **Kühlschrank: [Zutaten]** | Kühlschrank-Modus (11.1) |
| **bewerten [Rezept] [Sterne] [Kommentar]** | Bewertung speichern (11.2) |
| **neue Rezepte** / **Küche: [Name]** / **trending** | neue Rezepte (11.3) |
| **anpassen [Rezept]** | Rezept ändern, Nährwerte neu rechnen |
| **Ziele: [kcal, P, F, KH]** | neue Makroziele aus MacroFactor übernehmen, aktuelle Pläne neu prüfen |
| **Vorrat** | `vorrat.yaml` anzeigen und aktualisieren |
| **Web-App aktualisieren** | generieren, prüfen, veröffentlichen |

Nach jeder Änderung an Daten: `pruefen.py`, `generieren.py`, bei Bedarf veröffentlichen.

---

## 15. Hinweis

In der README und im Footer der Web-App: Nährwerte sind berechnete Schätzwerte auf Basis von Durchschnittswerten und können je nach Produkt abweichen. Die Pläne sind eine Empfehlung und ersetzen keine Ernährungs- oder ärztliche Beratung.

---

## 16. Entscheidungen (ergänzt im Projektverlauf)

| Datum | Thema | Entscheidung |
|---|---|---|
| 22.10.2026 | Plausibilitätscheck pro Zutat (12.1) | Abweichung max. ±5 % **oder** max. ±5 kcal pro 100 g absolut (sonst scheitern Gewürze, Salz, Zitronensaft). Polyole (z. B. Erythrit) sind als Ausnahme in `tools/config.py` geführt. **Pro Rezept gilt streng ±5 %.** |
| 22.10.2026 | Veröffentlichung (10.4) | Alles öffentlich (Rezeptbuch, Wochenpläne, Einkaufslisten). Umstellbar über `veroeffentlichen` in `daten/profil.yaml`. |
| 22.10.2026 | Einkauf (8.2) | Nur 1× pro Woche (Samstag). Fisch, Garnelen und Hack frisch nur für Sa–Mo, danach als TK planen und Auftauen erinnern. |
| 22.10.2026 | Schema-Ergänzungen (Phase 2) | `zutaten.csv` hat zusätzlich die Spalte `typ` (Proteinquelle: haehnchen, pute, rind, schwein, fisch, garnelen, ei, milchprotein, pflanzlich, sonstiges; Suffix `-hack` für Hackfleisch). Rezept-Zutaten haben optional `name` (Anzeigename) und `nicht_mitgerechnet: true` (z. B. Salz fürs Kochwasser). Platzhalter mit `anzeige`: „2 Eier Gr. M (120 g)“; fehlt der Name in der Anzeige, wird er angehängt („1 Prise Salz (0,5 g)“). |
| 22.10.2026 | Rundung | kcal ganzzahlig, Makros auf 1 Nachkommastelle, kaufmännisch (12,5 → 13). |
| 24.10.2026 | Schichtarbeit (8.1) | 5-Tage-Zyklus Tag (7–19) · Nacht (19–7) · frei · frei · frei, Start Tagschicht So 1.11.2026, Mikrowelle auf der Arbeit. Boxen: Tagschicht Frühstück + Mittag, Nachtschicht Abend. Meal Prep am letzten freien Tag vor der Tagschicht. In `profil.yaml` → `schichten`. |
| 24.10.2026 | Frische (8.2, ergänzt) | Zusätzlich zu Fisch/Garnelen/Hack (2 Tage): übriges Frischfleisch max. 4 Tage nach dem Einkauf, sonst am Einkaufstag einfrieren und am Vorabend auftauen. |
| 24.10.2026 | Fettziel (8.2) | Fehlendes Fett über Snacks/Extras (Mandeln, Erdnussbutter) ausgleichen; Rezepte bleiben unverändert. |
| 24.10.2026 | Wochenplan-Schema (6.5, ergänzt) | `ladungen` (Rezept × n für Reste), `rest_von: "JJJJ-MM-TT/slot"`, `gekocht_am` (vorgekocht), `einfrieren`, `extras: [{zutat, g, text}]`. `faktor` skaliert das ganze Rezept. |
