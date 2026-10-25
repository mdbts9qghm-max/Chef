"""Kühlschrank-Modus (SPEC 11.1): Gerichte vorschlagen, die hauptsächlich vorhandene Zutaten nutzen,
und die Portion an die restlichen Makros des Tages anpassen.

CLI: python3 tools/kuehlschrank.py "Hähnchen, Reis, Skyr" [--gegessen kcal,P,F,KH] [--mahlzeit Mittag/Abend]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import einkauf as ek  # noqa: E402
import naehrwerte as nw  # noqa: E402
import wochenplan as wp  # noqa: E402

zahl = nw.zahl


def woerter(text):
    return [w.strip().lower() for w in re.split(r",|;|\bund\b|\n", text) if w.strip()]


def zuordnen(wort, db):
    """Alltagswort → passende Zutaten der Datenbank (unscharf, z. B. „Reis“ → Basmati- und Milchreis)."""
    such = config.KUEHLSCHRANK_SYNONYME.get(wort, wort)
    # Wortstämme (Eier → Eie, Kartoffeln → Kartoffel) nur, wenn sie lang genug bleiben
    kandidaten = {such} | {k for k in (such.rstrip("n"), such.rstrip("e"), such.rstrip("s")) if len(k) >= 4}
    return sorted(z for z in db if any(k in z.lower() for k in kandidaten))


def zutatenmengen(rezept):
    """{Zutat: g} ohne Wasser und Kochwasser-Salz."""
    out = {}
    for e in nw.zutaten_eintraege(rezept):
        if not (e.get("nicht_mitgerechnet") or e["zutat"] in config.NICHT_EINKAUFEN):
            out[e["zutat"]] = out.get(e["zutat"], 0) + e["g"]
    return out


def ist_grundvorrat(zutat, packungen, vorrat_namen):
    pack = packungen.get(zutat) or {}
    return (zutat in vorrat_namen or zutat in config.KUEHLSCHRANK_GRUNDVORRAT
            or pack.get("abteilung") in config.KUEHLSCHRANK_GRUNDVORRAT_ABTEILUNGEN
            or pack.get("haltbar_tage_offen", 0) >= config.VORRATSKAUF_AB_TAGEN)


def faktor_fuer(portion, rest):
    """Portionsfaktor (0,25er-Schritte, 0,5–1,5), der die Rest-kcal am besten trifft;
    Protein unter dem Rest wird bestraft (Protein hat Priorität)."""
    def kosten(f):
        k = abs(portion["kcal"] * f - rest["kcal"])
        if portion["protein"] * f < rest["protein"]:
            k += (rest["protein"] - portion["protein"] * f) * 10
        return k
    return min(config.KUEHLSCHRANK_FAKTOREN, key=kosten)


def vorschlaege(text, rezepte, db, packungen=None, vorrat=None, gegessen=None, mahlzeit=None, anzahl=3):
    packungen = packungen if packungen is not None else wp.lade_packungen()
    vorrat = vorrat if vorrat is not None else ek.lade_vorrat()
    kuehl = {}
    for w in woerter(text):
        for z in zuordnen(w, db):
            kuehl[z] = w
    vorrat_namen = {v["zutat"] for v in vorrat}
    rest = None
    if gegessen:
        rest = {k: config.TAGESZIELE[k] - gegessen[k] for k in ("kcal", "protein", "fett", "kh")}
    out = []
    for rid, r in rezepte.items():
        sterne = (r.get("bewertung") or {}).get("sterne")
        if (sterne is not None and sterne <= 2) or (mahlzeit and r["mahlzeit"] != mahlzeit):
            continue
        mengen = zutatenmengen(r)
        summe = sum(mengen.values()) or 1
        aus_kuehl = sum(g for z, g in mengen.items() if z in kuehl)
        if not aus_kuehl:
            continue
        frisch_fehlt = [z for z in mengen if z not in kuehl and not ist_grundvorrat(z, packungen, vorrat_namen)]
        optional = sorted((z for z in frisch_fehlt if mengen[z] / summe < config.KUEHLSCHRANK_OPTIONAL_ANTEIL),
                          key=lambda z: -mengen[z])
        fehlend = sorted((z for z in frisch_fehlt if z not in optional), key=lambda z: -mengen[z])
        if len(fehlend) > config.KUEHLSCHRANK_MAX_FEHLEND:
            continue
        portion = nw.rezept_naehrwerte(r, db)["portion"]
        f = faktor_fuer(portion, rest) if rest else 1.0
        out.append({"id": rid, "name": r["name"], "anteil": aus_kuehl / summe, "fehlend": fehlend, "optional": optional,
                    "genutzt": sorted({kuehl[z] for z in mengen if z in kuehl}), "faktor": f,
                    "werte": {k: portion[k] * f for k in ("kcal", "protein", "fett", "kh")}, "rest": rest})
    # zuerst: nutzt möglichst viele deiner Zutaten, dann wenig Fehlendes, dann hoher Kühlschrank-Anteil
    out.sort(key=lambda v: (-len(v["genutzt"]), len(v["fehlend"]), -v["anteil"]))
    return out[:anzahl]


def main(argv):
    if not argv:
        sys.exit('Aufruf: python3 tools/kuehlschrank.py "Hähnchen, Reis, Skyr" [--gegessen kcal,P,F,KH] [--mahlzeit Mittag/Abend]')
    gegessen = None
    if "--gegessen" in argv:
        k, p, f, kh = (float(x) for x in argv[argv.index("--gegessen") + 1].split(","))
        gegessen = {"kcal": k, "protein": p, "fett": f, "kh": kh}
    mahlzeit = argv[argv.index("--mahlzeit") + 1] if "--mahlzeit" in argv else None
    db = nw.lade_zutaten()
    vs = vorschlaege(argv[0], nw.lade_alle_rezepte(), db, gegessen=gegessen, mahlzeit=mahlzeit)
    if not vs:
        print("Nichts im Rezeptbuch passt gut – Claude schlägt ein neues Gericht vor.")
        return 0
    if gegessen:
        r = vs[0]["rest"]
        print(f"Heute noch offen: {zahl(r['kcal'], 0)} kcal · {zahl(r['protein'], 0)} g P · {zahl(r['fett'], 0)} g F · {zahl(r['kh'], 0)} g KH\n")
    for v in vs:
        w = v["werte"]
        fehlt = f" · fehlt: {', '.join(v['fehlend'])}" if v["fehlend"] else " · nichts Wichtiges fehlt"
        print(f"{v['name']} ({zahl(v['anteil'] * 100, 0)} % aus deinem Kühlschrank: {', '.join(v['genutzt'])}){fehlt}")
        if v["optional"]:
            print(f"   optional (kann weg): {', '.join(v['optional'])}")
        print(f"   Portion × {zahl(v['faktor'], 2)}: {zahl(w['kcal'], 0)} kcal · {zahl(w['protein'])} g P · "
              f"{zahl(w['fett'])} g F · {zahl(w['kh'])} g KH → web/rezept/{v['id']}.html")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
