"""Import von Rezepten aus Instagram/TikTok (SPEC 9): Eingang sichten, Mengen umrechnen,
ähnliche Rezepte finden, Erledigtes ablegen. Das Lesen und Umschreiben übernimmt Claude im Chat.

CLI: python3 tools/importieren.py                          → Neues in import/ auflisten
     python3 tools/importieren.py --erledigt <name>        → Screenshots/Text nach import/erledigt/
     python3 tools/importieren.py --link <url> --rezept <id> → Link in links.txt als erledigt markieren
     python3 tools/importieren.py --aehnlich <rezept-id>   → ähnliche Rezepte zu einem (neuen) Rezept
"""
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import naehrwerte as nw  # noqa: E402

GRUPPE = re.compile(r"^(.*?)(?:[-_ ](\d+))?$")


# --- Eingang -------------------------------------------------------------------------
def eingang(ordner=config.IMPORT_DIR, links=config.IMPORT_LINKS):
    """{'bilder': {name: [Dateien]}, 'texte': {name: Datei}, 'links': [URLs]} – nur Neues."""
    bilder, texte = {}, {}
    for p in sorted(Path(ordner).iterdir()) if Path(ordner).exists() else []:
        if not p.is_file() or p.name == Path(links).name or p.name.startswith("."):
            continue
        name = GRUPPE.match(p.stem).group(1).lower()
        if p.suffix.lower() in config.BILD_ENDUNGEN:
            bilder.setdefault(name, []).append(p)
        elif p.suffix.lower() == ".txt":
            texte[name] = p
    offen = []
    if Path(links).exists():
        for z in Path(links).read_text(encoding="utf-8").splitlines():
            z = z.strip()
            if z and not z.startswith("#"):
                offen.append(z)
    return {"bilder": bilder, "texte": texte, "links": offen}


def erledigt(name, ordner=config.IMPORT_DIR, ziel=config.IMPORT_ERLEDIGT):
    """Alle Dateien einer Gruppe nach import/erledigt/ verschieben; gibt die neuen Pfade zurück."""
    e = eingang(ordner, Path(ordner) / config.IMPORT_LINKS.name)
    dateien = e["bilder"].get(name.lower(), []) + ([e["texte"][name.lower()]] if name.lower() in e["texte"] else [])
    if not dateien:
        raise FileNotFoundError(f"Keine Import-Dateien „{name}“ gefunden")
    Path(ziel).mkdir(parents=True, exist_ok=True)
    return [Path(shutil.move(str(d), str(Path(ziel) / d.name))) for d in dateien]


def link_erledigt(url, rezept_id, links=config.IMPORT_LINKS, datum=None):
    zeilen = Path(links).read_text(encoding="utf-8").splitlines()
    treffer = [i for i, z in enumerate(zeilen) if z.strip() == url]
    if not treffer:
        raise ValueError(f"Link nicht (mehr) offen: {url}")
    for i in treffer:
        zeilen[i] = f"# erledigt: {(datum or dt.date.today()).isoformat()} → {rezept_id}: {url}"
    Path(links).write_text("\n".join(zeilen) + "\n", encoding="utf-8")


# --- Umrechnen ---------------------------------------------------------------------------
def umrechnen(menge, einheit, zutat):
    """„1 Scoop“ Whey → 30 g, „½ Cup“ Haferflocken → 45 g, „1 Dose“ Kidneybohnen → Abtropfgewicht."""
    e = einheit.lower().strip().rstrip(".")
    e = config.UMRECHNUNG_ALIAS.get(e, e)
    if e == "dose":
        from wochenplan import lade_packungen
        pack = lade_packungen().get(zutat)
        if not pack:
            raise ValueError(f"Keine Packungsgröße für „{zutat}“")
        return menge * pack["packung_g"]
    if e not in config.UMRECHNUNG:
        raise ValueError(f"Unbekannte Einheit „{einheit}“")
    tabelle = config.UMRECHNUNG[e]
    g = next((v for k, v in tabelle.items() if k != "_" and k.lower() in zutat.lower()), tabelle["_"])
    return menge * g


# --- Ähnlichkeit ---------------------------------------------------------------------------
STOPP = {"protein", "high", "mit", "und", "aus", "der", "die", "das", "dem", "&"}


def namenswoerter(name):
    return {w for w in re.findall(r"[a-zäöüß]{4,}", name.lower()) if w not in STOPP}


def anteile(rezept):
    z = [e for e in nw.zutaten_eintraege(rezept) if e["zutat"] not in config.NICHT_EINKAUFEN
         and not e.get("nicht_mitgerechnet")]
    summe = sum(e["g"] for e in z) or 1
    out = {}
    for e in z:
        out[e["zutat"]] = out.get(e["zutat"], 0) + e["g"] / summe
    return out


def aehnlichkeit(a, b):
    """0–1: 40 % Namenswörter (Jaccard), 60 % gewichtete Zutatenüberschneidung."""
    na, nb = namenswoerter(a["name"]), namenswoerter(b["name"])
    name = len(na & nb) / len(na | nb) if na | nb else 0
    aa, ab = anteile(a), anteile(b)
    zutaten = sum(min(aa[k], ab[k]) for k in aa.keys() & ab.keys())
    return 0.4 * name + 0.6 * zutaten


def aehnliche_rezepte(neu, bestand, schwelle=config.AEHNLICH_SCHWELLE):
    werte = [(aehnlichkeit(neu, r), rid) for rid, r in bestand.items() if rid != neu.get("id")]
    return sorted(((round(w, 2), rid) for w, rid in werte if w >= schwelle), reverse=True)


def main(argv):
    if "--erledigt" in argv:
        for p in erledigt(argv[argv.index("--erledigt") + 1]):
            print(f"→ {p.relative_to(config.WURZEL)}")
        return 0
    if "--link" in argv:
        link_erledigt(argv[argv.index("--link") + 1], argv[argv.index("--rezept") + 1])
        print("Link als erledigt markiert.")
        return 0
    if "--aehnlich" in argv:
        rezepte = nw.lade_alle_rezepte()
        neu = rezepte[argv[argv.index("--aehnlich") + 1]]
        treffer = aehnliche_rezepte(neu, rezepte)
        print("\n".join(f"{w:.2f}  {rid}" for w, rid in treffer) or "Keine ähnlichen Rezepte.")
        return 0
    e = eingang()
    if not any(e.values()):
        print("Nichts Neues in import/.")
        return 0
    for name, dateien in e["bilder"].items():
        print(f"Screenshots „{name}“: {', '.join(d.name for d in dateien)}")
    for name, d in e["texte"].items():
        print(f"Text „{name}“: {d.name}")
    for url in e["links"]:
        print(f"Link: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
