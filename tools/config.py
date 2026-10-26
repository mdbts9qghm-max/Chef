"""Zentrale Konfiguration: alle Schwellenwerte, Toleranzen und Pfade.

Persönliche Ziele kommen aus daten/profil.yaml; hier stehen nur Regeln aus der
SPEC, damit sie an genau einer Stelle geändert werden können.
"""
from pathlib import Path

import yaml

# --- Pfade -------------------------------------------------------------------
WURZEL = Path(__file__).resolve().parent.parent
DATEN = WURZEL / "daten"
PROFIL_YAML = DATEN / "profil.yaml"
ZUTATEN_CSV = DATEN / "zutaten.csv"
PACKUNGEN_CSV = DATEN / "packungen.csv"
REZEPTE_DIR = DATEN / "rezepte"
AUSGABE_REZEPTE = WURZEL / "rezepte"
REZEPTBUCH_MD = WURZEL / "rezeptbuch.md"


def lade_profil(pfad=PROFIL_YAML):
    with open(pfad, encoding="utf-8") as f:
        return yaml.safe_load(f)


PROFIL = lade_profil()

# --- Tagesziele (SPEC 2) -------------------------------------------------------
TAGESZIELE = {
    "kcal": PROFIL["tagesziele"]["kcal"],
    "protein": PROFIL["tagesziele"]["protein_g"],
    "fett": PROFIL["tagesziele"]["fett_g"],
    "kh": PROFIL["tagesziele"]["kh_g"],
}
PORTIONEN = PROFIL["haushalt"]["portionen_pro_rezept"]

# --- Korridore pro Portion (SPEC 3) --------------------------------------------
# Schlüssel: fruehstueck | hauptgericht | kalorienarm | snack
KORRIDORE = PROFIL["mahlzeit_korridore"]

# --- Kategorien (SPEC 4.1) -----------------------------------------------------
HIGH_PROTEIN_MIN_G = 40           # mind. 40 g Protein pro Portion …
HIGH_PROTEIN_PRO_100KCAL = 10     # … oder mind. 10 g Protein pro 100 kcal
SCHNELL_MAX_MIN = 25              # Vorbereitung + Kochen (Wartezeit zählt nicht)
KALORIENARM_MAX_KCAL = 550
KALORIENARM_MIN_PROTEIN = 35
MEAL_PREP_MIN_TAGE = 3

# Hauptkategorie-Slug → Anzeigename (bestimmt den Ausgabeordner rezepte/<slug>/)
HAUPTKATEGORIEN = {
    "high-protein": "High Protein",
    "schnell": "Schnelle Rezepte",
    "meal-prep": "Meal Prep",
    "kalorienarm": "Kalorienarm",
    "fruehstueck-snacks": "Frühstück & Snacks",
}
KATEGORIE_REIHENFOLGE = list(HAUPTKATEGORIEN.values())

MAHLZEITEN = ["Frühstück", "Mittag/Abend", "Snack"]
GESCHMACK = ["süß", "herzhaft"]
SCHWIERIGKEIT = ["leicht", "mittel", "aufwendig"]
KUECHEN = [
    "Deutsch", "Italienisch", "Asiatisch", "Mexikanisch", "Indisch",
    "Griechisch & Mediterran", "Türkisch & Orientalisch", "Amerikanisch",
    "International / Fusion",
]

# --- Wochenplanung (SPEC 8) ------------------------------------------------------
WOCHENPLAENE_DIR = DATEN / "wochenplaene"
VORRAT_YAML = DATEN / "vorrat.yaml"
AUSGABE_WOCHENPLAENE = WURZEL / "wochenplaene"
AUSGABE_EINKAUF = WURZEL / "einkaufslisten"

_PL = PROFIL["planung"]
PLAN_PROTEIN_MIN = _PL["protein_min_g"]             # Priorität 1
PLAN_KCAL_MIN = TAGESZIELE["kcal"] - _PL["kcal_unter_ziel_max"]   # Priorität 2: 2.175 …
PLAN_KCAL_MAX = TAGESZIELE["kcal"] + _PL["kcal_ueber_ziel_max"]    # … bis 2.275 (nie über dem Ziel)
PLAN_FETT_TOLERANZ = _PL["fett_toleranz_g"]
PLAN_FETT_MIN = _PL["fett_min_g"]                   # nie darunter
PLAN_KH_TOLERANZ = _PL["kh_toleranz_g"]
FAKTOR_SCHRITT = _PL["faktor_schritt"]
FAKTOR_MAX = _PL["faktor_max"]
FRISCH_MAX_TAGE = _PL["frisch_max_tage_nach_einkauf"]   # Fisch, Garnelen, Hack
# Übriges Frischfleisch (Hähnchen, Pute, Rind, Schwein am Stück): Entscheidung 16, sonst einfrieren
FLEISCH_FRISCH_MAX_TAGE = 4
DREI_STERNE_MAX = _PL["drei_sterne_max_pro_woche"]

# --- Planer (tools/planer.py, Entscheidung 25.10.2026: günstiger planen) --------------
PLANER_FAKTOREN = [0.75, 1.0, 1.25, 1.5]          # 0,25er-Schritte, max. FAKTOR_MAX
PLANER_FRUEHSTUECK_MAX_TAGE = 2                   # gleiches Frühstück an max. 2 Tagen (1× backen, 2 Ladungen)
PLANER_SNACK_MAX_TAGE = 2                         # gleicher Snack an max. 2 Tagen
PLANER_HAUPT_MAX_KOCHEN = 1                       # jedes Hauptgericht max. 1 Kochvorgang (= max. 2 Mahlzeiten)
# Sicherheitsabstand zu den harten Grenzen aus 8.2 (Rundung, Gewichtsschwankung)
# klein gehalten, seit kcal nie über dem Ziel liegen dürfen (Entscheidung 26.10.2026) – sonst kaum lösbar
PLANER_RAND = {"protein": 0.2, "kcal": 2.0, "fett": 0.2, "kh": 0.5}
PLANER_STARTS = 300                                # Neustarts der lokalen Suche
PLANER_SEED = 45
# Gewichte der Zielfunktion: harte Regeln ≫ Kosten ≫ Bequemlichkeit
PLANER_GEWICHT = {"regel": 1000.0, "makro": 400.0, "kosten": 1.0, "ueber_budget": 6.0, "faktor": 0.8, "snack": 0.4}
AUSWAERTS = {"kcal": _PL["auswaerts_platzhalter"]["kcal"], "protein": _PL["auswaerts_platzhalter"]["protein_g"],
             "fett": _PL["auswaerts_platzhalter"]["fett_g"], "kh": _PL["auswaerts_platzhalter"]["kh_g"]}
AUSWAERTS_TIPPS = [
    "Steak, Fisch oder Hähnchen mit Kartoffeln oder Reis statt Pasta in Sahnesauce.",
    "Sauce und Dressing extra bestellen und nur die Hälfte nehmen.",
    "Beim Griechen/Türken: Grillteller mit Tzatziki und Salat statt Pommes-Platte.",
    "Ein Getränk ohne Zucker; Dessert lieber zu Hause (z. B. Protein-Mousse).",
]

SLOTS = ["fruehstueck", "mittag", "abend", "snack"]
SLOT_NAMEN = {"fruehstueck": "Frühstück", "mittag": "Mittag", "abend": "Abend", "snack": "Snack"}
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
WOCHENTAGE_LANG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

SCHICHTEN = PROFIL.get("schichten") or {}
ESSENSZEITEN = PROFIL.get("essenszeiten") or {}
MEAL_PREP_START = "15:00"
BOX_FERTIG_VOR_SCHICHT_MIN = 30     # Box-Mahlzeiten am Schichttag so früh fertig           # Beginn eines Meal-Prep-Blocks am Kochtag
WARTEZEIT_VORABEND_MIN = 240        # ab 4 h Wartezeit (Overnight Oats, Marinade über Nacht) am Vorabend ansetzen

# Fehlendes Fett/Protein über einfache Extras ausgleichen (SPEC 8.2, Schritt 3)
EXTRAS_KATALOG = {
    "mandeln": {"zutat": "Mandeln gehobelt", "g": 30, "text": "30 g Mandeln (pur oder über das Frühstück)"},
    "erdnussbutter": {"zutat": "Erdnussbutter 100 % Erdnüsse", "g": 20, "text": "1 gehäufter EL Erdnussbutter"},
    "skyr_honig": {"zutat": "Skyr natur", "g": 250, "text": "250 g Skyr (mit 1 TL Honig)"},
}

# Einkauf: lange haltbare Produkte zählen als Vorratskauf (nicht ins Wochenbudget)
VORRATSKAUF_AB_TAGEN = 180
EINKAUF_PRO_WOCHE = PROFIL["einkauf"].get("pro_woche", 1)   # 1 = nur der Einkaufstag vor Wochenbeginn
TK_ABTEILUNG = "Tiefkühl"

# --- Startbestand (SPEC 5) -----------------------------------------------------
REZEPTPLAN_YAML = DATEN / "rezeptplan.yaml"
REZEPTPLAN_MD = WURZEL / "rezeptplan.md"
BESTAND_GESAMT = 50
# Fettstrategie „rezepte“ (Entscheidung 25.10.2026): Ø Fett pro Portion je Gruppe, damit Pläne ohne Nüsse-Extras
# das Fettziel erreichen. Gruppe = Hauptkategorie „kalorienarm“, sonst Mahlzeit. Wird von bestand.py geprüft.
# Protein moderat (Entscheidung 26.10.2026): Tage bei ca. 160–175 g statt ~190 g, damit bei max. 2.275 kcal
# Platz für Fett bleibt. Ø Protein pro Portion je Gruppe, geprüft in bestand.py.
PROTEIN_ZIEL_PRO_MAHLZEIT = {"Frühstück": (40, 47), "Mittag/Abend": (50, 62), "Kalorienarm": (40, 55), "Snack": (20, 35)}
FETT_ZIEL_PRO_MAHLZEIT = {"Frühstück": (19, 24), "Mittag/Abend": (24, 30), "Kalorienarm": (14, 20), "Snack": (7, 12)}
BEREICHE_SOLL = {"Frühstück": 15, "Snack": 5, "Hauptgericht": 30}       # exakt (5.1)
FRUEHSTUECK_MIN = {"Meal Prep": 4, "Schnelle Rezepte": 5}               # 5.1
KUECHEN_SOLL = {                                                        # exakt, nur Hauptgerichte (5.2)
    "Deutsch": 4, "Italienisch": 5, "Asiatisch": 5, "Mexikanisch": 3, "Indisch": 3,
    "Griechisch & Mediterran": 3, "Türkisch & Orientalisch": 3, "Amerikanisch": 3,
    "International / Fusion": 1,
}
BESTAND_MIN = {                                                         # Mindestwerte (5.3)
    "Meal Prep": 12, "Schnelle Rezepte": 15, "Kalorienarm": 6, "High Protein": 45, "Inspiration": 15,
}
PROTEINQUELLE_MAX_HAUPTGERICHTE = 10
# 5.3 zählt „Fisch und Garnelen“ und „Skyr/Quark/Hüttenkäse“ als je eine Quelle
PROTEIN_GRUPPEN = {
    "haehnchen": "Hähnchen", "pute": "Pute", "rind": "Rind", "schwein": "Schwein",
    "fisch": "Fisch & Garnelen", "garnelen": "Fisch & Garnelen", "ei": "Eier",
    "milchprotein": "Skyr/Quark/Hüttenkäse", "pflanzlich": "Pflanzlich",
}
ZUTATEN_MAX = 90

# --- Import (SPEC 9) -----------------------------------------------------------
IMPORT_DIR = WURZEL / "import"
IMPORT_ERLEDIGT = IMPORT_DIR / "erledigt"
IMPORT_LINKS = IMPORT_DIR / "links.txt"
BILD_ENDUNGEN = {".png", ".jpg", ".jpeg", ".heic", ".webp"}
AEHNLICH_SCHWELLE = 0.65         # ab hier fragen: Variante oder eigenes Rezept? (Bestand max. 0,52, Dubletten ≥ 0,8)
# Ungenaue Mengenangaben → Gramm. Schlüssel: Einheit → {Teil des Zutatennamens: g pro Einheit}; "_" = Standard.
# Quellen: übliche Messlöffel (Whey 30 g), US-Cup 240 ml, Löffelmaße nach Dichte der Zutat.
UMRECHNUNG = {
    "scoop": {"Whey": 30, "_": 30},
    "messlöffel": {"Whey": 30, "_": 30},
    "cup": {"Haferflocken": 90, "Mehl": 125, "Grieß": 170, "Reis": 185, "Milch": 245, "Skyr": 245, "Quark": 245,
            "Frischkäse": 230, "Erdnussbutter": 250, "Beeren": 140, "Heidelbeeren": 140, "Himbeeren": 125,
            "Mandeln": 95, "Honig": 340, "Erythrit": 190, "Kakao": 85, "Schokolade": 170, "_": 240},
    "el": {"Öl": 13, "Honig": 21, "Erdnussbutter": 16, "Kakao": 7, "Mehl": 10, "Haferflocken": 8, "Whey": 7,
           "Skyr": 15, "Quark": 15, "Sojasauce": 16, "Tomatenmark": 15, "Erythrit": 10, "Mandeln": 8, "_": 15},
    "tl": {"Öl": 4.5, "Honig": 7, "Backpulver": 4, "Zimt": 2.5, "Salz": 6, "Paprikapulver": 2, "Kreuzkümmel": 2,
           "Oregano": 1, "Pfeffer": 2, "Senf": 5, "Vanille": 4, "_": 5},
    "prise": {"_": 0.5},
    "ei": {"_": 60},
}
UMRECHNUNG_ALIAS = {"scoops": "scoop", "cups": "cup", "tasse": "cup", "tassen": "cup", "esslöffel": "el",
                    "tbsp": "el", "teelöffel": "tl", "tsp": "tl", "prisen": "prise", "eier": "ei", "egg": "ei", "eggs": "ei"}

# --- Formular „Eigenes Rezept“ (App) --------------------------------------------------
# Stückgewichte (essbarer Anteil) für Zeilen wie „2 Eier“, „1 Zwiebel“, „3 Zehen Knoblauch“; Brot/Wraps aus packungen.csv
STUECK_G = {"Ei Gr. M ohne Schale": 60, "Banane geschält": 120, "Apfel": 150, "Zwiebel": 80, "Knoblauch": 4,
            "Paprika rot": 160, "Tomaten": 80, "Salatgurke": 400, "Frühlingszwiebeln": 15, "Mozzarella light": 125,
            "Weizen-Tortilla-Wraps": 62, "Burger-Brötchen": 75, "Vollkorntoast": 28}
# Alltagswörter → Zutat (ergänzt KUEHLSCHRANK_SYNONYME; gesucht wird danach in den Zutatennamen)
FORMULAR_SYNONYME = {"öl": "olivenöl", "reis": "basmatireis", "nudeln": "hartweizennudeln", "spaghetti": "hartweizennudeln",
                     "pasta": "hartweizennudeln", "quark": "magerquark", "whey": "whey protein",
                     "proteinpulver": "whey protein vanille", "eiweißpulver": "whey protein vanille", "milch": "milch 1",
                     "mehl": "weizenmehl", "ei": "ei gr", "eier": "ei gr", "eiweiß": "eiklar", "joghurt": "skyr",
                     "hähnchen": "hähnchenbrust", "hühnchen": "hähnchenbrust", "chicken": "hähnchenbrust",
                     "hackfleisch": "rinderhackfleisch 5", "hack": "rinderhackfleisch 5", "lachs": "lachsfilet",
                     "kartoffel": "kartoffeln", "tomate": "tomaten", "paprika": "paprika rot", "spinat": "babyspinat",
                     "banane": "banane", "bananen": "banane", "zucker": "erythrit", "süßstoff": "erythrit",
                     "brühe": "gemüsebrühe", "currypaste": "rote currypaste", "kokosmilch": "kokosmilch",
                     "wrap": "tortilla", "wraps": "tortilla", "toast": "vollkorntoast", "brötchen": "burger-brötchen",
                     "zehe": "knoblauch", "zehen": "knoblauch", "knoblauchzehe": "knoblauch", "knoblauchzehen": "knoblauch"}
FORMULAR_EINHEITEN_STUECK = ["stück", "stk", "zehe", "zehen", "scheibe", "scheiben"]
FORMULAR_EINHEITEN_PACKUNG = ["dose", "dosen", "packung", "packungen", "pck", "pkg", "becher", "glas", "beutel", "kugel"]
FORMULAR_STANDARD = {"zeit_min": 30, "vorbereitung_min": 10, "kueche": "International / Fusion", "schwierigkeit": "leicht",
                     "kuehlschrank_tage": 3, "kuehlschrank_tage_fisch": 2, "snack_suess_ab_zucker_g": 8}

# --- Kühlschrank-Modus (SPEC 11.1) ------------------------------------------------
# Grundvorrat (zählt als vorhanden, wird aber als „aus dem Vorrat“ angezeigt): lange haltbare Produkte
# (haltbar offen ≥ VORRATSKAUF_AB_TAGEN), alles aus vorrat.yaml und diese frischen Standards:
KUEHLSCHRANK_GRUNDVORRAT = {"Zwiebel", "Knoblauch", "Salz"}
KUEHLSCHRANK_GRUNDVORRAT_ABTEILUNGEN = {"Trockenwaren", "Konserven & Saucen", "Gewürze & Öle"}   # ungeöffnet lange haltbar
KUEHLSCHRANK_OPTIONAL_ANTEIL = 0.05   # frische Kleinigkeiten unter 5 % des Gewichts: optional, zählen nicht als „fehlt“
KUEHLSCHRANK_MAX_FEHLEND = 2          # max. 1–2 fehlende Hauptzutaten (SPEC 11.1)
KUEHLSCHRANK_FAKTOREN = [0.5, 0.75, 1.0, 1.25, 1.5]
# Alltagswörter → Suchbegriff in den Zutatennamen
KUEHLSCHRANK_SYNONYME = {
    "pasta": "nudeln", "spaghetti": "nudeln", "penne": "nudeln", "makkaroni": "nudeln", "nudel": "nudeln",
    "ei": "ei gr", "eier": "ei gr", "hack": "hackfleisch", "hühnchen": "hähnchen", "huhn": "hähnchen",
    "chicken": "hähnchen", "cottage cheese": "körniger", "hüttenkäse": "körniger", "joghurt": "skyr",
    "pute": "puten", "truthahn": "puten", "rind": "rind", "kartoffel": "kartoffeln", "tomate": "tomaten",
    "beeren": "beeren", "wraps": "tortilla", "wrap": "tortilla", "käse": "käse", "frischkäse": "frischkäse",
}

# --- Plausibilität (SPEC 12.1 + Entscheidung 16) -------------------------------
ATWATER = {"protein": 4, "kh": 4, "fett": 9, "ballaststoffe": 2}
PLAUSI_PROZENT = 5.0              # max. Abweichung in %
PLAUSI_ABS_KCAL_ZUTAT = 5.0       # pro Zutat alternativ max. 5 kcal/100 g absolut
# Polyole liefern KH ohne nennenswerte kcal – Prüfung pro Zutat entfällt,
# im Rezept werden ihre KH aus der Plausibilitätsrechnung herausgenommen.
POLYOLE = {"Erythrit"}

# --- Zutatentypen (Zusatzspalte typ in zutaten.csv) ------------------------------
# Form: <quelle> oder <quelle>-hack, z. B. "rind-hack".
PROTEINQUELLEN = ["haehnchen", "pute", "rind", "schwein", "fisch", "garnelen",
                  "ei", "milchprotein", "pflanzlich"]
FLEISCH_FISCH = {"haehnchen", "pute", "rind", "schwein", "fisch", "garnelen"}
FISCH_GARNELEN = {"fisch", "garnelen"}

# --- Lebensmittelsicherheit (SPEC 7.1) ----------------------------------------
KERNTEMPERATUREN = {          # °C, nur zur Info in Texten/Prüfungen
    "Geflügel": 74, "Hackfleisch": 72, "Schweinefilet": 63,
    "Lachs glasig": "50–55", "Lachs durch": 60,
}
GARPROBE_WOERTER = ["Kerntemperatur", "Garprobe"]
FISCH_MAX_KUEHLSCHRANK_TAGE = 2
MAX_KUEHLSCHRANK_TAGE = 4

# Ofenschritte müssen Temperatur und beide Modi nennen. Erkannt wird ein Ofenschritt an
# diesen Wörtern; Ofenschritte nennen daher immer die Schiene. „backen“ allein zählt nicht
# (Pfanne, Waffeleisen), „aus dem Ofen nehmen“ ebenfalls nicht.
OFEN_WOERTER = ["Schiene", "Backofen", "in den Ofen", "im Ofen"]
OFEN_PFLICHT = ["°C", "Ober-/Unterhitze", "Umluft"]
AIRFRYER_WOERTER = ["Airfryer"]
HERD_WOERTER = ["Pfanne", "Topf"]   # Schritt am Herd → Herdstufe „Stufe X von 9“ erwartet (Warnung)

# --- Zucker (SPEC 2.1) --------------------------------------------------------
FRUEHSTUECK_ZUCKER_MAX_G = PROFIL["vorlieben"]["fruehstueck_zucker_max_g"]

# --- Abschnittsumfang (SPEC 7) ------------------------------------------------
FEHLER_ANZAHL = (2, 4)
VARIANTEN_ANZAHL = (2, 4)
TIPPS_ANZAHL = (1, 3)

PFLICHTFELDER = [
    "id", "name", "hauptkategorie", "mahlzeit", "geschmack", "kueche",
    "schwierigkeit", "zeit", "ausstattung", "zutaten", "mise_en_place",
    "schritte", "fehler", "anrichten", "aufbewahrung", "varianten", "tipps",
    "bewertung",
]

# Abschnitte des generierten Rezept-Markdowns in fester Reihenfolge (SPEC 7)
MD_ABSCHNITTE = [
    "Nährwerte pro Portion",
    "Zutaten (für 2 Portionen)",
    "Mise en place",
    "Zubereitung",
    "Zeitablauf",
    "Häufige Fehler",
    "Anrichten",
    "Meal Prep & Aufbewahrung",
    "Varianten & Austausch",
    "Tipps",
    "Nährwert-Berechnung",
]

# Sonder-Platzhalter, die keine Zutat sind: {portion_g} = berechnetes Gewicht pro Portion
SONDER_PLATZHALTER = {"portion_g"}
# Zutaten, die nie auf die Einkaufsliste kommen
NICHT_EINKAUFEN = {"Wasser"}

# Öffentliche Adresse der Web-App (SPEC 10.4); leer = nur relative Links
WEB_URL = (PROFIL.get("web_url") or "").rstrip("/") + "/" if PROFIL.get("web_url") else ""

HINWEIS_SCHAETZWERTE = (
    "Nährwerte sind berechnete Schätzwerte auf Basis von Durchschnittswerten "
    "und können je nach Produkt abweichen."
)
