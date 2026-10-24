"""Nährwerte berechnen: Zutaten-Datenbank laden, Rezepte rechnen, Kategorien vergeben.

CLI: python3 tools/naehrwerte.py <rezept-id> [faktor]
"""
import csv
from decimal import ROUND_HALF_UP, Decimal
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

NAEHRSTOFFE = ["kcal", "protein", "fett", "gesaettigt", "kh", "zucker", "ballaststoffe", "salz"]


# --- Laden -------------------------------------------------------------------
def _csv_zeilen(pfad):
    with open(pfad, encoding="utf-8") as f:
        return list(csv.DictReader(z for z in f if z.strip() and not z.startswith("#")))


def lade_zutaten(pfad=config.ZUTATEN_CSV):
    """Zutaten-Datenbank als {zutat: {kcal: …, …, garfaktor, typ}}."""
    db = {}
    for z in _csv_zeilen(pfad):
        name = z["zutat"].strip()
        werte = {k: float(z[k]) for k in NAEHRSTOFFE}
        werte["garfaktor"] = float(z["garfaktor"])
        werte["typ"] = z.get("typ", "sonstiges").strip() or "sonstiges"
        db[name] = werte
    return db


def lade_rezept(pfad):
    with open(pfad, encoding="utf-8") as f:
        return yaml.safe_load(f)


def lade_alle_rezepte(ordner=config.REZEPTE_DIR):
    return {p.stem: lade_rezept(p) for p in sorted(Path(ordner).glob("*.yaml"))}


def zutaten_eintraege(rezept):
    """Nur echte Zutaten (ohne Gruppen-Überschriften)."""
    return [z for z in rezept.get("zutaten", []) if "id" in z]


# --- Rechnen -----------------------------------------------------------------
def zutat_werte(eintrag, db, faktor=1.0):
    """Nährwerte einer Rezeptzeile für die angegebene Menge (× faktor)."""
    if eintrag.get("nicht_mitgerechnet"):
        return {k: 0.0 for k in NAEHRSTOFFE}
    basis = db[eintrag["zutat"]]
    g = eintrag["g"] * faktor
    return {k: basis[k] * g / 100 for k in NAEHRSTOFFE}


def summe(werte_liste):
    return {k: sum(w[k] for w in werte_liste) for k in NAEHRSTOFFE}


def rezept_naehrwerte(rezept, db, faktor=1.0):
    """Gesamt- und Portionswerte, Zeilen pro Zutat und geschätztes Gargewicht."""
    zeilen = [(e, zutat_werte(e, db, faktor)) for e in zutaten_eintraege(rezept)]
    gesamt = summe([w for _, w in zeilen])
    portion = {k: v / config.PORTIONEN for k, v in gesamt.items()}
    if rezept.get("gargewicht_g"):
        gargewicht = rezept["gargewicht_g"] * faktor
        gemessen = True
    else:
        gargewicht = sum(e["g"] * faktor * db[e["zutat"]]["garfaktor"]
                         for e, _ in zeilen if not e.get("nicht_mitgerechnet"))
        gemessen = False
    return {
        "zeilen": zeilen,
        "gesamt": gesamt,
        "portion": portion,
        "gargewicht_gesamt": gargewicht,
        "gargewicht_portion": gargewicht / config.PORTIONEN,
        "gargewicht_gemessen": gemessen,
    }


def variante_delta(aenderung, db):
    """Änderung pro Portion für {zutat: delta_g} (negativ = weniger/weglassen)."""
    return {k: sum(db[z][k] * g / 100 for z, g in aenderung.items()) / config.PORTIONEN
            for k in NAEHRSTOFFE}


def atwater_kcal(w, polyol_kh=0.0):
    a = config.ATWATER
    return (a["protein"] * w["protein"] + a["kh"] * (w["kh"] - polyol_kh)
            + a["fett"] * w["fett"] + a["ballaststoffe"] * w["ballaststoffe"])


def plausibilitaet(w, abs_toleranz=None, polyol_kh=0.0):
    """Vergleicht kcal mit 4P+4KH+9F+2BS. abs_toleranz nur pro Zutat (kcal/100 g)."""
    berechnet = atwater_kcal(w, polyol_kh)
    diff = berechnet - w["kcal"]
    prozent = (diff / w["kcal"] * 100) if w["kcal"] else (0.0 if abs(diff) < 1e-9 else float("inf"))
    ok = abs(prozent) <= config.PLAUSI_PROZENT
    if not ok and abs_toleranz is not None:
        ok = abs(diff) <= abs_toleranz
    return {"berechnet": berechnet, "diff": diff, "prozent": prozent, "ok": ok}


def plausibilitaet_zutat(name, db):
    if name in config.POLYOLE:
        return {"berechnet": None, "diff": 0.0, "prozent": 0.0, "ok": True, "ausnahme": True}
    return plausibilitaet(db[name], abs_toleranz=config.PLAUSI_ABS_KCAL_ZUTAT)


def plausibilitaet_rezept(rezept, db, gesamt):
    polyol_kh = sum(e["g"] * db[e["zutat"]]["kh"] / 100 for e in zutaten_eintraege(rezept)
                    if e["zutat"] in config.POLYOLE and not e.get("nicht_mitgerechnet"))
    return plausibilitaet(gesamt, polyol_kh=polyol_kh)


# --- Kategorien --------------------------------------------------------------
def gesamtzeit(rezept):
    """Vorbereitung + Kochen (Wartezeit zählt für „schnell“ nicht)."""
    z = rezept["zeit"]
    return z.get("vorbereitung", 0) + z.get("kochen", 0)


def ist_high_protein(portion):
    p, kcal = portion["protein"], portion["kcal"]
    return (p >= config.HIGH_PROTEIN_MIN_G
            or (kcal > 0 and p / kcal * 100 >= config.HIGH_PROTEIN_PRO_100KCAL))


def ist_schnell(rezept):
    return gesamtzeit(rezept) <= config.SCHNELL_MAX_MIN


def ist_kalorienarm(rezept, portion):
    return (rezept["mahlzeit"] == "Mittag/Abend"
            and portion["kcal"] <= config.KALORIENARM_MAX_KCAL
            and portion["protein"] >= config.KALORIENARM_MIN_PROTEIN)


def ist_meal_prep(rezept):
    return "Meal Prep" in (rezept.get("kategorien_manuell") or [])


def kategorien(rezept, portion):
    """Alle zutreffenden Kategorien in fester Reihenfolge."""
    treffer = {
        "High Protein": ist_high_protein(portion),
        "Schnelle Rezepte": ist_schnell(rezept),
        "Meal Prep": ist_meal_prep(rezept),
        "Kalorienarm": ist_kalorienarm(rezept, portion),
        "Frühstück & Snacks": rezept["mahlzeit"] in ("Frühstück", "Snack"),
    }
    return [k for k in config.KATEGORIE_REIHENFOLGE if treffer[k]]


def proteinquellen(rezept, db):
    """Typen der Zutaten, absteigend nach Proteinbeitrag."""
    beitrag = {}
    for e in zutaten_eintraege(rezept):
        typ = db[e["zutat"]]["typ"]
        if typ == "sonstiges" or e.get("nicht_mitgerechnet"):
            continue
        quelle = typ.split("-")[0]
        beitrag[quelle] = beitrag.get(quelle, 0) + e["g"] * db[e["zutat"]]["protein"] / 100
    return sorted(beitrag, key=beitrag.get, reverse=True)


def hauptproteinquelle(rezept, db):
    q = proteinquellen(rezept, db)
    return q[0] if q else None


def enthaelt_typ(rezept, db, quellen):
    return any(db[e["zutat"]]["typ"].split("-")[0] in quellen for e in zutaten_eintraege(rezept))


# --- Formatierung ------------------------------------------------------------
def rund(x, nachkomma=0):
    """Kaufmännisch runden (12,5 → 13), nicht Pythons „Banker's Rounding“."""
    q = Decimal(1).scaleb(-nachkomma)
    r = Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP)
    return int(r) if nachkomma == 0 else float(r)


def runden(w):
    """kcal ganzzahlig, alles andere auf 1 Nachkommastelle."""
    return {k: (rund(v) if k == "kcal" else rund(v, 1)) for k, v in w.items()}


def zahl(x, nachkomma=1):
    """Deutsche Schreibweise: 1.234,5 – überflüssige ,0 entfällt."""
    if nachkomma == 0:
        s = f"{rund(x):,}"
    else:
        s = f"{rund(x, nachkomma):,.{nachkomma}f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def vorzeichen(x, nachkomma=1, einheit=""):
    """„+13 kcal“, „−2,6 g“, „±0 kcal“ (gerundet, mit echtem Minuszeichen)."""
    r = rund(x, nachkomma)
    if r == 0:
        return f"±0{einheit}"
    return ("+" if r > 0 else "−") + zahl(abs(r), nachkomma) + einheit


def gramm(g):
    """Grammangabe: ab 10 g ganzzahlig, darunter mit einer Nachkommastelle."""
    return f"{zahl(g, 0 if g >= 10 else 1)} g"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Aufruf: python3 tools/naehrwerte.py <rezept-id> [faktor]")
    rid = sys.argv[1]
    f = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
    r = lade_rezept(config.REZEPTE_DIR / f"{rid}.yaml")
    datenbank = lade_zutaten()
    erg = rezept_naehrwerte(r, datenbank, f)
    p = runden(erg["portion"])
    print(f"{r['name']} (Faktor {zahl(f, 2)}), pro Portion:")
    for k in NAEHRSTOFFE:
        print(f"  {k:14} {zahl(p[k], 0 if k == 'kcal' else 1)}")
    print("  Kategorien:", ", ".join(kategorien(r, erg["portion"])))
