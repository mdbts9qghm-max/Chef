import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import config  # noqa: E402
import naehrwerte as nw  # noqa: E402

MINI_CSV = """\
# Testdatenbank mit runden Werten
zutat,kcal,protein,fett,gesaettigt,kh,zucker,ballaststoffe,salz,garfaktor,typ
Testhuhn,100,20,2,0.5,1,0,0,0.2,0.75,haehnchen
Testreis,350,8,1,0.2,77,0,0,0,2.8,sonstiges
Testgewürz,40,1,1,0,5,0,2,0,1.0,sonstiges
Testfalsch,200,5,1,0,10,0,0,0,1.0,sonstiges
Salz,0,0,0,0,0,0,0,100,1.0,sonstiges
Ei Gr. M ohne Schale,140,12.6,9.9,3.1,0.7,0.4,0,0.35,1.0,ei
"""


@pytest.fixture
def mini_db(tmp_path):
    pfad = tmp_path / "zutaten.csv"
    pfad.write_text(MINI_CSV, encoding="utf-8")
    return nw.lade_zutaten(pfad)


@pytest.fixture(scope="session")
def db():
    return nw.lade_zutaten()


@pytest.fixture
def testrezept():
    """Kleines Rezept auf Basis der Mini-Datenbank."""
    return {
        "id": "testgericht",
        "name": "Testgericht",
        "hauptkategorie": "high-protein",
        "mahlzeit": "Mittag/Abend",
        "geschmack": "herzhaft",
        "kueche": "Deutsch",
        "schwierigkeit": "leicht",
        "zeit": {"vorbereitung": 10, "kochen": 15, "wartezeit": 0},
        "zutaten": [
            {"gruppe": "Alles"},
            {"id": "huhn", "zutat": "Testhuhn", "g": 300},
            {"id": "reis", "zutat": "Testreis", "g": 150},
            {"id": "salz", "zutat": "Salz", "g": 0.5, "anzeige": "1 Prise"},
            {"id": "eier", "zutat": "Ei Gr. M ohne Schale", "name": "Eier", "g": 120, "anzeige": "2 Eier Gr. M"},
            {"id": "wasser_salz", "zutat": "Salz", "g": 10, "nicht_mitgerechnet": True},
        ],
    }


@pytest.fixture(scope="session")
def echte_rezepte():
    return nw.lade_alle_rezepte()


@pytest.fixture
def chicken(echte_rezepte):
    return copy.deepcopy(echte_rezepte["marry-me-chicken"])


@pytest.fixture
def brownie(echte_rezepte):
    return copy.deepcopy(echte_rezepte["fruehstuecks-brownie"])
