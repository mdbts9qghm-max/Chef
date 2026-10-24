"""Prüfungen pro Rezept (SPEC 12.1). Läuft vor jedem Generieren.

CLI: python3 tools/pruefen.py [rezept-id …]   → Exit-Code 1 bei Fehlern
"""
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import naehrwerte as nw  # noqa: E402

PLATZHALTER = re.compile(r"\{([a-z0-9_]+)(:n)?\}")


@dataclass
class Ergebnis:
    rezept_id: str
    fehler: list = field(default_factory=list)
    warnungen: list = field(default_factory=list)

    @property
    def ok(self):
        return not self.fehler


def texte(rezept):
    """Alle Texte, in denen Platzhalter vorkommen dürfen."""
    t = list(rezept.get("mise_en_place") or [])
    t += [s.get("text", "") for s in rezept.get("schritte") or []]
    t.append(rezept.get("anrichten") or "")
    return t


def korridor_schluessel(rezept):
    if rezept["mahlzeit"] == "Frühstück":
        return "fruehstueck"
    if rezept["mahlzeit"] == "Snack":
        return "snack"
    return "kalorienarm" if rezept["hauptkategorie"] == "kalorienarm" else "hauptgericht"


def pruefe_rezept(rezept, db, dateiname=None):
    rid = rezept.get("id", dateiname or "?")
    e = Ergebnis(rid)

    # Pflichtfelder, id, Dateiname
    fehlend = [f for f in config.PFLICHTFELDER if f not in rezept]
    if fehlend:
        e.fehler.append(f"Pflichtfelder fehlen: {', '.join(fehlend)}")
        return e
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", rid):
        e.fehler.append(f"id „{rid}“ ist nicht kebab-case")
    if dateiname and dateiname != rid:
        e.fehler.append(f"Dateiname „{dateiname}“ ≠ id „{rid}“")

    # Aufzählungsfelder
    for feld, erlaubt in [("hauptkategorie", config.HAUPTKATEGORIEN), ("mahlzeit", config.MAHLZEITEN),
                          ("geschmack", config.GESCHMACK), ("kueche", config.KUECHEN),
                          ("schwierigkeit", config.SCHWIERIGKEIT)]:
        if rezept[feld] not in erlaubt:
            e.fehler.append(f"{feld}: „{rezept[feld]}“ ist nicht erlaubt")
    if e.fehler:
        return e

    # Zutaten existieren, ids eindeutig
    eintraege = nw.zutaten_eintraege(rezept)
    ids = [z["id"] for z in eintraege]
    doppelt = {i for i in ids if ids.count(i) > 1}
    if doppelt:
        e.fehler.append(f"Zutaten-ids doppelt: {', '.join(sorted(doppelt))}")
    unbekannt = [z["zutat"] for z in eintraege if z["zutat"] not in db]
    if unbekannt:
        e.fehler.append(f"Zutaten nicht in zutaten.csv: {', '.join(unbekannt)}")
        return e
    for z in eintraege:
        if not isinstance(z.get("g"), (int, float)) or z["g"] <= 0:
            e.fehler.append(f"Zutat {z['id']}: Menge g fehlt oder ≤ 0")

    # Plausibilität pro Zutat und Rezept
    for name in sorted({z["zutat"] for z in eintraege}):
        p = nw.plausibilitaet_zutat(name, db)
        if not p["ok"]:
            e.fehler.append(f"Plausibilität Zutat „{name}“: {p['prozent']:+.1f} % ({p['diff']:+.1f} kcal/100 g)")
    erg = nw.rezept_naehrwerte(rezept, db)
    p = nw.plausibilitaet_rezept(rezept, db, erg["gesamt"])
    if not p["ok"]:
        e.fehler.append(f"Plausibilität Rezept: {p['prozent']:+.1f} %")

    # Platzhalter
    benutzt = set()
    for t in texte(rezept):
        for m in PLATZHALTER.finditer(t):
            if m.group(1) in config.SONDER_PLATZHALTER:
                continue
            if m.group(1) not in ids:
                e.fehler.append(f"Platzhalter {{{m.group(1)}}} verweist auf keine Zutat")
            benutzt.add(m.group(1))
    for i in ids:
        if i not in benutzt:
            e.fehler.append(f"Zutat {{{i}}} wird in keinem Text verwendet")

    # Zielwerte der Mahlzeit (SPEC 3)
    portion = erg["portion"]
    k = config.KORRIDORE[korridor_schluessel(rezept)]
    kcal, prot = nw.rund(portion["kcal"]), nw.rund(portion["protein"], 1)
    if k.get("kcal_min") is not None and kcal < k["kcal_min"]:
        e.fehler.append(f"{kcal} kcal pro Portion < Minimum {k['kcal_min']}")
    if k.get("kcal_max") is not None and kcal > k["kcal_max"]:
        e.fehler.append(f"{kcal} kcal pro Portion > Maximum {k['kcal_max']}")
    if prot < k["protein_min"]:
        e.fehler.append(f"{prot} g Protein pro Portion < Minimum {k['protein_min']}")

    # Hauptkategorie erfüllt
    kats = nw.kategorien(rezept, portion)
    haupt = config.HAUPTKATEGORIEN[rezept["hauptkategorie"]]
    if haupt not in kats:
        e.fehler.append(f"Hauptkategorie „{haupt}“ ist nicht erfüllt (berechnet: {', '.join(kats) or '–'})")
    manuell = set(rezept.get("kategorien_manuell") or []) - {"Meal Prep"}
    if manuell:
        e.fehler.append(f"kategorien_manuell darf nur „Meal Prep“ enthalten, nicht {', '.join(manuell)}")

    # Aufbewahrung / Meal Prep / Fisch
    auf = rezept["aufbewahrung"]
    tage = auf.get("kuehlschrank_tage") or 0
    fisch = nw.enthaelt_typ(rezept, db, config.FISCH_GARNELEN)
    if fisch and tage > config.FISCH_MAX_KUEHLSCHRANK_TAGE:
        e.fehler.append(f"Fisch/Garnelen: max. {config.FISCH_MAX_KUEHLSCHRANK_TAGE} Tage Kühlschrank (angegeben {tage})")
    if tage > config.MAX_KUEHLSCHRANK_TAGE:
        e.fehler.append(f"Kühlschrank max. {config.MAX_KUEHLSCHRANK_TAGE} Tage (angegeben {tage})")
    if nw.ist_meal_prep(rezept) and tage < config.MEAL_PREP_MIN_TAGE:
        e.fehler.append(f"Meal Prep braucht mind. {config.MEAL_PREP_MIN_TAGE} Tage Haltbarkeit (angegeben {tage})")
    for f in ("einfrierbar", "aufwaermen"):
        if f not in auf:
            e.fehler.append(f"aufbewahrung.{f} fehlt")

    # Geschmack / Zucker beim Frühstück (Warnungen)
    if rezept["mahlzeit"] == "Frühstück":
        if rezept["geschmack"] != "süß":
            e.warnungen.append("Frühstück ist nicht süß (nur auf ausdrücklichen Wunsch)")
        if portion["zucker"] > config.FRUEHSTUECK_ZUCKER_MAX_G:
            e.warnungen.append(f"Zucker {portion['zucker']:.1f} g pro Portion > {config.FRUEHSTUECK_ZUCKER_MAX_G} g")

    # Kerntemperatur / Garprobe
    schritte = rezept["schritte"] or []
    alle_schritte = " ".join(s.get("text", "") for s in schritte)
    if nw.enthaelt_typ(rezept, db, config.FLEISCH_FISCH):
        if not any(w in alle_schritte for w in config.GARPROBE_WOERTER):
            e.fehler.append("Fleisch/Fisch ohne Kerntemperatur oder Garprobe in den Schritten")

    # Ofen-, Airfryer- und Herdschritte
    for n, s in enumerate(schritte, 1):
        t = s.get("text", "")
        if not s.get("titel"):
            e.fehler.append(f"Schritt {n} ohne Titel")
        if any(w in t for w in config.OFEN_WOERTER):
            fehlt = [w for w in config.OFEN_PFLICHT if w not in t]
            if fehlt:
                e.fehler.append(f"Schritt {n} (Ofen): es fehlt {', '.join(fehlt)}")
        if any(w in t for w in config.AIRFRYER_WOERTER) and "°C" not in t:
            e.fehler.append(f"Schritt {n} (Airfryer): Temperatur fehlt")
        if any(w in t for w in config.HERD_WOERTER) and "Stufe" not in t and "°C" not in t:
            e.warnungen.append(f"Schritt {n}: Pfanne/Topf ohne Herdstufe")
        if s.get("timer_min") is not None and not isinstance(s["timer_min"], (int, float)):
            e.fehler.append(f"Schritt {n}: timer_min ist keine Zahl")

    # Umfang der Abschnitte (SPEC 7)
    for feld, (lo, hi) in [("fehler", config.FEHLER_ANZAHL), ("varianten", config.VARIANTEN_ANZAHL),
                           ("tipps", config.TIPPS_ANZAHL)]:
        n = len(rezept[feld] or [])
        if not lo <= n <= hi:
            e.fehler.append(f"{feld}: {n} Einträge, erlaubt {lo}–{hi}")
    if not rezept["mise_en_place"]:
        e.fehler.append("Mise en place ist leer")
    if not schritte:
        e.fehler.append("Keine Zubereitungsschritte")

    # Varianten: strukturierte brauchen titel/text, Zutaten der Änderung müssen existieren
    for v in rezept["varianten"] or []:
        if isinstance(v, dict):
            if not (v.get("titel") and v.get("text")):
                e.fehler.append("Variante braucht titel und text")
            fremd = [z for z in (v.get("aenderung") or {}) if z not in db]
            if fremd:
                e.fehler.append(f"Variante „{v.get('titel')}“: Zutaten nicht in zutaten.csv: {', '.join(fremd)}")

    # Inspiration vollständig
    insp = rezept.get("inspiration")
    if insp and not (insp.get("quelle") and insp.get("aenderungen")):
        e.fehler.append("inspiration braucht quelle und aenderungen")

    # Bewertung
    sterne = (rezept.get("bewertung") or {}).get("sterne")
    if sterne is not None and sterne not in (1, 2, 3, 4, 5):
        e.fehler.append(f"Bewertung {sterne} ist nicht 1–5")
    return e


def pruefe_alle(rezepte=None, db=None):
    db = db or nw.lade_zutaten()
    if rezepte is None:
        rezepte = nw.lade_alle_rezepte()
    ergebnisse = [pruefe_rezept(r, db, dateiname) for dateiname, r in rezepte.items()]
    # id eindeutig über alle Rezepte
    ids = [r.get("id") for r in rezepte.values()]
    for erg, r in zip(ergebnisse, rezepte.values()):
        if ids.count(r.get("id")) > 1:
            erg.fehler.append(f"id „{r.get('id')}“ ist nicht eindeutig")
    return ergebnisse


def bericht(ergebnisse):
    zeilen = []
    for e in ergebnisse:
        status = "OK" if e.ok else "FEHLER"
        zeilen.append(f"[{status}] {e.rezept_id}")
        zeilen += [f"    ✗ {f}" for f in e.fehler]
        zeilen += [f"    ! {w}" for w in e.warnungen]
    n_f = sum(not e.ok for e in ergebnisse)
    zeilen.append(f"\n{len(ergebnisse)} Rezepte geprüft, {n_f} mit Fehlern, "
                  f"{sum(len(e.warnungen) for e in ergebnisse)} Warnungen.")
    return "\n".join(zeilen)


def main(argv):
    rezepte = nw.lade_alle_rezepte()
    if argv:
        rezepte = {k: v for k, v in rezepte.items() if k in argv}
    ergebnisse = pruefe_alle(rezepte)
    print(bericht(ergebnisse))
    return 0 if all(e.ok for e in ergebnisse) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
