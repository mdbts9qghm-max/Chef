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

# --- Startbestand (SPEC 5) -----------------------------------------------------
REZEPTPLAN_YAML = DATEN / "rezeptplan.yaml"
REZEPTPLAN_MD = WURZEL / "rezeptplan.md"
BESTAND_GESAMT = 50
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

HINWEIS_SCHAETZWERTE = (
    "Nährwerte sind berechnete Schätzwerte auf Basis von Durchschnittswerten "
    "und können je nach Produkt abweichen."
)
