"""Bewertung speichern (SPEC 11.2): Sterne, Kommentar und Datum in die bewertung-Zeile des Rezept-YAML.

CLI: python3 tools/bewerten.py <rezept-id> <1–5> ["Kommentar"]
Nur die Zeile „bewertung: {...}“ wird ersetzt, der Rest der Datei bleibt unverändert.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ZEILE = re.compile(r"^bewertung:.*$", re.M)


def heute():
    return dt.datetime.now(ZoneInfo(config.PROFIL["region"]["zeitzone"])).date()


def bewerten(rezept_id, sterne, kommentar=None, datum=None, ordner=config.REZEPTE_DIR):
    if sterne not in (1, 2, 3, 4, 5):
        raise ValueError(f"Sterne müssen 1–5 sein, nicht {sterne}")
    pfad = Path(ordner) / f"{rezept_id}.yaml"
    if not pfad.exists():
        raise FileNotFoundError(f"Rezept „{rezept_id}“ gibt es nicht")
    text = pfad.read_text(encoding="utf-8")
    if len(ZEILE.findall(text)) != 1:
        raise ValueError(f"{pfad.name}: genau eine Zeile „bewertung:“ erwartet")
    k = json.dumps(kommentar, ensure_ascii=False) if kommentar else "null"   # JSON-String ist gültiges YAML
    neu = f"bewertung: {{sterne: {sterne}, kommentar: {k}, datum: {(datum or heute()).isoformat()}}}"
    pfad.write_text(ZEILE.sub(lambda _: neu, text), encoding="utf-8")
    return neu


def main(argv):
    if len(argv) < 2:
        sys.exit("Aufruf: python3 tools/bewerten.py <rezept-id> <1–5> [\"Kommentar\"]")
    zeile = bewerten(argv[0], int(argv[1]), argv[2] if len(argv) > 2 else None)
    print(f"{argv[0]}: {zeile}")
    if int(argv[1]) <= 2:
        print("→ aussortiert: bleibt im Rezeptbuch, wird aber nicht mehr geplant.")
    print("Jetzt: python3 tools/pruefen.py && python3 tools/generieren.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
