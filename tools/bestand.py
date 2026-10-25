"""Bestands-Abgleich gegen SPEC 5.1–5.3 und Generierung von rezeptplan.md.

CLI: python3 tools/bestand.py   → Soll/Ist für Plan und echte Rezepte, schreibt rezeptplan.md
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import naehrwerte as nw  # noqa: E402

BEREICH_AUS_MAHLZEIT = {"Frühstück": "Frühstück", "Snack": "Snack", "Mittag/Abend": "Hauptgericht"}
TAG_KATEGORIE = {"MP": "Meal Prep", "S": "Schnelle Rezepte", "KA": "Kalorienarm"}


def startbestand(plan, rezepte):
    """Nur die Rezepte aus dem Rezeptplan (SPEC 5 gilt für den Startbestand, nicht für spätere Importe)."""
    ids = {p["id"] for p in plan}
    return {rid: r for rid, r in rezepte.items() if rid in ids}


def lade_plan(pfad=config.REZEPTPLAN_YAML):
    with open(pfad, encoding="utf-8") as f:
        return yaml.safe_load(f)["rezepte"]


# --- Einheitliche Einträge ---------------------------------------------------------
# Ein Eintrag: {id, name, bereich, kueche, protein, kategorien: set, inspiration: bool}

def eintrag_aus_plan(p):
    kats = {TAG_KATEGORIE[t] for t in p.get("tags", [])}
    kats.add("High Protein")   # Planziel: alle High Protein
    return {"id": p["id"], "name": p["name"], "bereich": p["bereich"], "kueche": p["kueche"],
            "protein": p["protein"], "kategorien": kats, "inspiration": bool(p["inspiration"])}


def eintrag_aus_rezept(r, db):
    portion = nw.rezept_naehrwerte(r, db)["portion"]
    return {"id": r["id"], "name": r["name"], "bereich": BEREICH_AUS_MAHLZEIT[r["mahlzeit"]],
            "kueche": r["kueche"], "protein": nw.hauptproteinquelle(r, db),
            "kategorien": set(nw.kategorien(r, portion)), "inspiration": bool(r.get("inspiration"))}


# --- Auswertung -------------------------------------------------------------------
def auswerten(eintraege, vollstaendig=True):
    """Liste von (Anforderung, Soll, Ist, ok). vollstaendig=False: exakte Sollwerte
    werden als Obergrenze geprüft (Zwischenstand während Phase 4)."""
    zeilen = []

    def exakt(name, soll, ist):
        ok = ist == soll if vollstaendig else ist <= soll
        zeilen.append((name, f"{soll}", f"{ist}", ok))

    def mindestens(name, soll, ist):
        # Zwischenstand: noch nicht erreichte Mindestwerte sind „offen“ (None), kein Verstoß
        ok = True if ist >= soll else (False if vollstaendig else None)
        zeilen.append((name, f"≥ {soll}", f"{ist}", ok))

    exakt("Rezepte gesamt", config.BESTAND_GESAMT, len(eintraege))
    for bereich, soll in config.BEREICHE_SOLL.items():
        exakt(f"Bereich {bereich}", soll, sum(e["bereich"] == bereich for e in eintraege))
    fr = [e for e in eintraege if e["bereich"] == "Frühstück"]
    for kat, soll in config.FRUEHSTUECK_MIN.items():
        mindestens(f"Frühstück {kat}", soll, sum(kat in e["kategorien"] for e in fr))
    haupt = [e for e in eintraege if e["bereich"] == "Hauptgericht"]
    for kueche, soll in config.KUECHEN_SOLL.items():
        exakt(f"Küche {kueche}", soll, sum(e["kueche"] == kueche for e in haupt))
    for kat, soll in config.BESTAND_MIN.items():
        if kat == "Inspiration":
            ist = sum(e["inspiration"] for e in eintraege)
        elif kat == "Kalorienarm":
            ist = sum(kat in e["kategorien"] for e in haupt)
        else:
            ist = sum(kat in e["kategorien"] for e in eintraege)
        mindestens(kat if kat != "Kalorienarm" else "Kalorienarme Hauptgerichte", soll, ist)
    for gruppe, n in sorted(proteingruppen(haupt).items(), key=lambda x: -x[1]):
        zeilen.append((f"Hauptprotein {gruppe}", f"≤ {config.PROTEINQUELLE_MAX_HAUPTGERICHTE}", f"{n}",
                       n <= config.PROTEINQUELLE_MAX_HAUPTGERICHTE))
    return zeilen


def proteingruppen(haupt):
    zaehler = {}
    for e in haupt:
        g = config.PROTEIN_GRUPPEN.get(e["protein"], e["protein"] or "?")
        zaehler[g] = zaehler.get(g, 0) + 1
    return zaehler


def tabelle(zeilen):
    out = ["| Anforderung | Soll | Ist | |", "|---|---:|---:|---|"]
    symbol = {True: "✓", False: "✗", None: "offen"}
    out += [f"| {a} | {s} | {i} | {symbol[ok]} |" for a, s, i, ok in zeilen]
    return out


# --- rezeptplan.md --------------------------------------------------------------------
def rezeptplan_markdown(plan, rezepte, db):
    vorhanden = {r["id"] for r in rezepte.values()}
    out = ["<!-- Generiert aus daten/rezeptplan.yaml – nicht von Hand bearbeiten. -->",
           "# Rezeptplan: Startbestand mit 50 Rezepten", "",
           f"Stand: {len(vorhanden & {p['id'] for p in plan})} von {len(plan)} Rezepten geschrieben. "
           "Tags sind Planwerte (MP = Meal Prep, S = schnell, KA = kalorienarm); verbindlich sind die "
           "von `pruefen.py` berechneten Kategorien.", ""]
    for bereich, titel in [("Frühstück", "Frühstück, süß"), ("Snack", "Snacks & Desserts, süß"),
                           ("Hauptgericht", "Hauptgerichte")]:
        auswahl = [p for p in plan if p["bereich"] == bereich]
        out += [f"## {titel} ({len(auswahl)})", "",
                "| Nr. | Gericht | id | Küche | Hauptprotein | Ziel-kcal | Inspiration | Tags | Status |",
                "|---:|---|---|---|---|---:|---|---|---|"]
        for p in auswahl:
            protein = p.get("protein_text") or config.PROTEIN_GRUPPEN.get(p["protein"], p["protein"])
            if p["id"] in vorhanden:
                kcal = nw.rund(nw.rezept_naehrwerte(rezepte[p["id"]], db)["portion"]["kcal"])
                status = f"✓ geschrieben ({kcal} kcal)"
            else:
                status = "offen"
            out.append(f"| {p['nr']} | {p['name']} | `{p['id']}` | {p['kueche']} | {protein} | {p['ziel_kcal']} | "
                       f"{'ja' if p['inspiration'] else 'nein'} | {', '.join(p.get('tags', [])) or '–'} | {status} |")
        out.append("")
    out += ["## Abgleich des Plans mit SPEC 5.1–5.3", ""]
    out += tabelle(auswerten([eintrag_aus_plan(p) for p in plan]))
    ist = [eintrag_aus_rezept(r, db) for r in startbestand(plan, rezepte).values()]
    vollstaendig = len(ist) >= config.BESTAND_GESAMT
    hinweis = ("Bestand vollständig: alle Vorgaben werden exakt geprüft." if vollstaendig else
               "Zwischenstand: exakte Sollwerte gelten hier als Obergrenze, Mindestwerte erst bei 50 Rezepten.")
    out += ["", f"## Ist-Stand des Startbestands ({len(ist)})", "", hinweis, ""]
    out += tabelle(auswerten(ist, vollstaendig=vollstaendig))
    plan_ids = {p["id"] for p in plan}
    extra = sorted(vorhanden - plan_ids)
    if extra:
        out += ["", f"## Weitere Rezepte (Import und neue Rezepte, {len(extra)})", "",
                "Zählen nicht zum Startbestand aus SPEC 5.", ""]
        for rid in extra:
            r = rezepte[rid]
            h = (r.get("herkunft") or {})
            out.append(f"- {r['name']} (`{rid}`, {r['mahlzeit']}, {r['kueche']})" + (f" – {h.get('art')}: {h.get('quelle')}" if h else ""))
    return "\n".join(out) + "\n"


def fett_gruppen(rezepte, db):
    """Ø Fett pro Portion je Gruppe → {gruppe: (Ø, (min, max), ok)}."""
    gruppen = {}
    for r in rezepte.values():
        g = "Kalorienarm" if r["hauptkategorie"] == "kalorienarm" else r["mahlzeit"]
        gruppen.setdefault(g, []).append(nw.rezept_naehrwerte(r, db)["portion"]["fett"])
    out = {}
    for g, werte in gruppen.items():
        lo, hi = config.FETT_ZIEL_PRO_MAHLZEIT[g]
        mittel = sum(werte) / len(werte)
        out[g] = (mittel, (lo, hi), lo <= mittel <= hi)
    return out


def main():
    db = nw.lade_zutaten()
    plan = lade_plan()
    rezepte = nw.lade_alle_rezepte()
    plan_zeilen = auswerten([eintrag_aus_plan(p) for p in plan])
    ist = [eintrag_aus_rezept(r, db) for r in startbestand(plan, rezepte).values()]
    ist_zeilen = auswerten(ist, vollstaendig=len(ist) >= config.BESTAND_GESAMT)
    print("Plan:", "alle Vorgaben erfüllt" if all(z[3] is not False for z in plan_zeilen) else "VERSTÖSSE")
    for z in plan_zeilen:
        if z[3] is False:
            print(f"  ✗ {z[0]}: Soll {z[1]}, Ist {z[2]}")
    print(f"Ist: {len(ist)} Rezepte,", "keine Verstöße" if all(z[3] is not False for z in ist_zeilen) else "VERSTÖSSE")
    for z in ist_zeilen:
        if z[3] is False:
            print(f"  ✗ {z[0]}: Soll {z[1]}, Ist {z[2]}")
    fett = fett_gruppen(startbestand(plan, rezepte), db)
    print("Fett Ø pro Portion:", " · ".join(f"{g} {nw.zahl(m)} g{'' if ok else f' ⚠️ Ziel {lo}–{hi} g'}"
                                           for g, (m, (lo, hi), ok) in fett.items()))
    config.REZEPTPLAN_MD.write_text(rezeptplan_markdown(plan, rezepte, db), encoding="utf-8")
    print("rezeptplan.md aktualisiert.")
    return 0 if all(z[3] is not False for z in plan_zeilen + ist_zeilen) else 1


if __name__ == "__main__":
    sys.exit(main())
