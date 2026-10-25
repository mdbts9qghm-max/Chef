"""„Web-App aktualisieren“ (SPEC 14): prüfen → generieren → bestand → Wochenpläne + Einkaufslisten → Tests,
dann Änderungen in web/ zeigen.

Veröffentlicht wird per Push auf main (Workflow .github/workflows/pages.yml) – committen erst nach OK.
Aufruf: python3 tools/veroeffentlichen.py [--ohne-tests]
        python3 tools/veroeffentlichen.py --live   # nur die Live-Seite prüfen (erreichbar, JSON-LD vollständig)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

LIVE_SEITEN = ["index.html", "rezepte.html", "manifest.webmanifest", "sw.js", "rezept/marry-me-chicken.html"]
LD_PFLICHT = ["name", "recipeYield", "recipeIngredient", "recipeInstructions", "totalTime", "nutrition", "url"]

SCHRITTE = [["tools/pruefen.py"], ["tools/generieren.py"], ["tools/bestand.py"], ["-m", "pytest", "-q"]]


def live_pruefen(basis=config.WEB_URL, laden=None):
    """Live-URLs abrufen; gibt eine Liste von Fehlern zurück (leer = alles gut)."""
    if laden is None:
        import urllib.request
        laden = lambda url: urllib.request.urlopen(url, timeout=20).read().decode("utf-8")
    if not basis:
        return ["Keine web_url in profil.yaml."]
    fehler = []
    for s in LIVE_SEITEN:
        try:
            text = laden(basis + s)
        except Exception as e:                 # HTTP-Fehler, Netz, Zeitüberschreitung
            fehler.append(f"{s}: {e}")
            continue
        if s.startswith("rezept/"):
            m = re.search(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', text, re.S)
            ld = json.loads(m.group(1)) if m else {}
            fehlend = [f for f in LD_PFLICHT if not ld.get(f)]
            if fehlend:
                fehler.append(f"{s}: JSON-LD unvollständig ({', '.join(fehlend)})")
    return fehler


def schritte():
    plaene = sorted(p.stem for p in config.WOCHENPLAENE_DIR.glob("KW-*.yaml"))
    return (SCHRITTE[:3] + [["tools/wochenplan.py", n] for n in plaene] + [["tools/einkauf.py", n] for n in plaene]
            + SCHRITTE[3:])


def main(argv):
    if "--live" in argv:
        fehler = live_pruefen()
        for f in fehler:
            print("✗", f)
        print("Live-Seite in Ordnung:", config.WEB_URL) if not fehler else None
        return 1 if fehler else 0
    for schritt in schritte():
        if "--ohne-tests" in argv and "pytest" in schritt:
            continue
        print(f"→ python3 {' '.join(schritt)}")
        if subprocess.run([sys.executable, *schritt], cwd=config.WURZEL).returncode:
            print("Abgebrochen: bitte zuerst den Fehler beheben, nichts veröffentlicht.")
            return 1
    status = subprocess.run(["git", "status", "--porcelain", "--", "web"], cwd=config.WURZEL,
                            capture_output=True, text=True).stdout.splitlines()
    if not status:
        print("web/ ist unverändert – nichts zu veröffentlichen.")
        return 0
    print(f"{len(status)} Dateien in web/ geändert. Veröffentlichen (nach OK):")
    print('  git add -A && git commit -m "Web-App aktualisiert" && git push origin main')
    if config.WEB_URL:
        print(f"Danach ca. 1 Minute bis {config.WEB_URL} aktualisiert ist (Actions → Pages).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
