"""Eingang aus der App übernehmen (läuft im Pages-Workflow vor dem Prüfen, siehe .github/workflows/pages.yml).

1. Baukasten: daten/baukasten/KW-XX-JJJJ-<Zeitstempel>.yaml (in der App zusammengestellt) wird geprüft und als
   daten/wochenplaene/KW-XX-JJJJ.yaml übernommen (je Woche gewinnt die neueste Datei, ein vorhandener Plan wird
   ersetzt). Beginnt die Woche erst in der Zukunft, gehen die Reste der Vorwoche laut Plan in den Vorrat
   (wie woche_auto). Danach Wochenplan- und Einkaufs-Markdown erzeugen.
2. Vorschläge: daten/vorschlaege/<id>.ok („✓ Aufnehmen“ in der App) → Rezept nach daten/rezepte/<id>.yaml
   (herkunft art: neu); Vorschläge, die schon im Rezeptbuch stehen oder älter als 4 Wochen sind, werden gelöscht.

Aufruf: python3 tools/eingang.py [--heute JJJJ-MM-TT]
Exit-Code 1, wenn ein Plan Strukturfehler hat (die Datei bleibt dann im Eingang liegen).
"""
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import einkauf as ek  # noqa: E402
import naehrwerte as nw  # noqa: E402
import wochenplan as wp  # noqa: E402
import woche_auto  # noqa: E402

DATEI = re.compile(r"(KW-\d{2}-\d{4})(?:-.*)?\.yaml")


def baukasten_uebernehmen(heute, eingang=None, plaene_dir=None, vorrat_pfad=None, ausgabe=print):
    """→ (übernommene Wochen, Fehlertexte)"""
    eingang = Path(eingang or config.BAUKASTEN_DIR)
    plaene_dir = Path(plaene_dir or config.WOCHENPLAENE_DIR)
    vorrat_pfad = Path(vorrat_pfad or config.VORRAT_YAML)
    je_woche = {}
    for p in sorted(eingang.glob("KW-*.yaml")):          # Zeitstempel im Namen → sortiert = chronologisch
        m = DATEI.fullmatch(p.name)
        if m:
            je_woche.setdefault(m.group(1), []).append(p)
    if not je_woche:
        return [], []
    rezepte, db = nw.lade_alle_rezepte(), nw.lade_zutaten()
    uebernommen, fehler = [], []
    for name, dateien in sorted(je_woche.items(), key=lambda x: ek.kw_schluessel(x[0])):
        neueste = dateien[-1]
        text = neueste.read_text(encoding="utf-8")
        plan = yaml.safe_load(text)
        plan["name"] = name
        pr = wp.pruefe_plan(plan, rezepte, db)
        if pr.fehler:
            fehler += [f"{neueste.name}: {f}" for f in pr.fehler]
            continue
        start = wp.datum(plan["tage"][0]["datum"])
        if start > heute:
            vorname = woche_auto.kw_name(start - dt.timedelta(days=7))
            n = woche_auto.reste_uebernehmen(vorname, plaene_dir, vorrat_pfad, rezepte, db)
            if n:
                ausgabe(f"Reste aus {vorname}: {n} Zutaten in den Vorrat")
        plaene_dir.mkdir(parents=True, exist_ok=True)
        (plaene_dir / f"{name}.yaml").write_text(text, encoding="utf-8")
        for p in dateien:
            p.unlink()
        uebernommen.append(name)
        ausgabe(f"{name}: aus dem Baukasten übernommen ({len(pr.warnungen)} Hinweise)")
    return uebernommen, fehler


def vorschlaege_aufraeumen(heute, ordner=None, rezepte_dir=None, ausgabe=print):
    """✓-Markierungen übernehmen, Erledigtes und Abgelaufenes löschen. → Liste aufgenommener ids"""
    ordner = Path(ordner or config.VORSCHLAEGE_DIR)
    rezepte_dir = Path(rezepte_dir or config.REZEPTE_DIR)
    if not ordner.exists():
        return []
    aufgenommen = []
    for ok in sorted(ordner.glob("*.ok")):
        quelle = ordner / f"{ok.stem}.yaml"
        ziel = rezepte_dir / f"{ok.stem}.yaml"
        if quelle.exists() and not ziel.exists():
            text = re.sub(r"(herkunft:\s*\{\s*art:\s*)vorschlag", r"\1neu", quelle.read_text(encoding="utf-8"), count=1)
            ziel.write_text(text, encoding="utf-8")
            aufgenommen.append(ok.stem)
            ausgabe(f"Vorschlag „{ok.stem}“ ins Rezeptbuch aufgenommen")
        ok.unlink()
    for p in sorted(ordner.glob("*.yaml")):
        if p.name == config.VORSCHLAEGE_VERLAUF.name:
            continue
        if (rezepte_dir / p.name).exists():
            p.unlink()
            continue
        datum = ((yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("herkunft") or {}).get("datum")
        if datum and (heute - wp.datum(datum)).days > config.VORSCHLAEGE_MAX_ALTER_TAGE:
            p.unlink()
            ausgabe(f"Vorschlag „{p.stem}“ nach {config.VORSCHLAEGE_MAX_ALTER_TAGE} Tagen ohne Entscheidung entfernt")
    return aufgenommen


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--heute", type=dt.date.fromisoformat, default=None)
    args = a.parse_args(argv)
    heute = args.heute or woche_auto.heute_berlin()
    vorschlaege_aufraeumen(heute)
    wochen, fehler = baukasten_uebernehmen(heute)
    for name in wochen:
        wp.main([name])
        ek.main([name])
    for f in fehler:
        print("✗", f)
    if not wochen and not fehler:
        print("Eingang leer.")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
