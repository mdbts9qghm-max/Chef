"""Automatische Wochenplanung (läuft jeden Freitag auf GitHub, siehe .github/workflows/woche-planen.yml).

1. nächste Woche bestimmen (Mo–So ab dem kommenden Montag)
2. gibt es den Plan schon (z. B. mit Claude abgestimmt) → nichts tun
3. Reste der laufenden Woche laut Plan in vorrat.yaml übernehmen (je Woche nur einmal)
4. mit tools/planer.py planen (mehrere Seeds, günstigster fehlerfreier Plan)
5. Plan schreiben; Markdown für Wochenplan und Einkaufsliste erzeugen

Aufruf: python3 tools/woche_auto.py [--heute JJJJ-MM-TT] [--starts 200] [--seeds 1,2,3,4]
Exit-Code 0 = geplant oder schon vorhanden, 1 = kein regelkonformer Plan gefunden.
"""
import argparse
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import einkauf as ek  # noqa: E402
import naehrwerte as nw  # noqa: E402
import planer  # noqa: E402
import wochenplan as wp  # noqa: E402


def heute_berlin():
    return dt.datetime.now(ZoneInfo(config.PROFIL["region"]["zeitzone"])).date()


def kw_name(d):
    jahr, kw, _ = d.isocalendar()
    return f"KW-{kw:02d}-{jahr}"


def naechste_woche(heute):
    """Name der Woche, die am nächsten Montag nach `heute` beginnt."""
    return kw_name(heute + dt.timedelta(days=7 - heute.weekday()))


def reste_uebernehmen(name, plaene_dir, vorrat_pfad, rezepte, db):
    """Reste der Woche `name` (laut Plan) in den Vorrat – je Woche nur einmal. → Anzahl oder None."""
    pfad = plaene_dir / f"{name}.yaml"
    if not pfad.exists():
        return None
    plan = wp.lade_plan(pfad)
    _, reste = ek.berechne(plan, rezepte, db, vorrat=ek.lade_vorrat(vorrat_pfad))
    return len(reste) if ek.reste_uebernehmen(reste, vorrat_pfad, woche=name) else 0


def planen(heute=None, plaene_dir=None, vorrat_pfad=None, starts=None, seeds=(1, 2, 3, 4), ausgabe=print):
    """Ein kompletter Automatik-Lauf. → (status, name, plan_info); status: vorhanden | geplant | fehlgeschlagen"""
    heute = heute or heute_berlin()
    plaene_dir = Path(plaene_dir or config.WOCHENPLAENE_DIR)
    vorrat_pfad = Path(vorrat_pfad or config.VORRAT_YAML)
    name = naechste_woche(heute)
    ziel = plaene_dir / f"{name}.yaml"
    if ziel.exists():
        ausgabe(f"{name}: Plan existiert schon – wird nicht überschrieben.")
        return "vorhanden", name, None
    rezepte, db = nw.lade_alle_rezepte(), nw.lade_zutaten()
    n = reste_uebernehmen(kw_name(heute), plaene_dir, vorrat_pfad, rezepte, db)
    if n is not None:
        ausgabe(f"Reste aus {kw_name(heute)}: {'schon übernommen' if n == 0 else f'{n} Zutaten in den Vorrat'}")
    daten = planer.Daten(rezepte=rezepte, db=db, vorrat=ek.lade_vorrat(vorrat_pfad))
    p = planer.Planer(name, daten=daten)
    beste = None
    for seed in seeds:
        r = p.planen(starts=starts, seed=seed)
        ausgabe(f"{name} Seed {seed}: {r[0]} Fehler, Einkauf {nw.zahl(r[1], 2)} €")
        if r[0] == 0 and (beste is None or r[1] < beste[1]):
            beste = r
    if beste is None:
        ausgabe(f"{name}: kein regelkonformer Plan gefunden – bitte in Claude „Woche planen“.")
        return "fehlgeschlagen", name, None
    plaene_dir.mkdir(parents=True, exist_ok=True)
    ziel.write_text(p.yaml_text(beste[3], beste[1]), encoding="utf-8")
    ausgabe(f"{name} geschrieben · Einkauf ca. {nw.zahl(beste[4]['woche'], 2)} € am "
            f"{beste[3]['einkauf'][0]['datum'].strftime('%d.%m.%Y')}")
    return "geplant", name, {"kosten": beste[4]["woche"]}


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("--heute", type=dt.date.fromisoformat, default=None)
    a.add_argument("--starts", type=int, default=None)
    a.add_argument("--seeds", default="1,2,3,4")
    args = a.parse_args(argv)
    status, name, _ = planen(args.heute, starts=args.starts, seeds=[int(s) for s in args.seeds.split(",")])
    if status == "geplant":
        wp.main([name])
        ek.main([name])
    return 1 if status == "fehlgeschlagen" else 0


if __name__ == "__main__":
    sys.exit(main())
