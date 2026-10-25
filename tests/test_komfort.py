"""Phase 7: Import (SPEC 9), Kühlschrank-Modus (11.1), Bewertungen (11.2)."""
import copy
import datetime as dt
import shutil

import pytest

import bewerten
import config
import generieren as gen
import importieren as im
import kuehlschrank as ks
import naehrwerte as nw
import pruefen


# --- Import -------------------------------------------------------------------------
@pytest.fixture
def eingang(tmp_path):
    (tmp_path / "brownie-1.png").write_bytes(b"x")
    (tmp_path / "brownie-2.png").write_bytes(b"x")
    (tmp_path / "wrap hack.jpg").write_bytes(b"x")
    (tmp_path / "suppe.txt").write_text("1 cup Brühe", encoding="utf-8")
    (tmp_path / "links.txt").write_text("# Kommentar\nhttps://example.org/a\n\n# erledigt: 2026-10-01 → x: https://example.org/b\n",
                                        encoding="utf-8")
    (tmp_path / "erledigt").mkdir()
    return tmp_path


def test_eingang_gruppiert_screenshots(eingang):
    e = im.eingang(eingang, eingang / "links.txt")
    assert sorted(p.name for p in e["bilder"]["brownie"]) == ["brownie-1.png", "brownie-2.png"]
    assert "wrap hack" in e["bilder"]
    assert e["texte"]["suppe"].name == "suppe.txt"
    assert e["links"] == ["https://example.org/a"]


def test_erledigt_verschiebt_dateien(eingang):
    neu = im.erledigt("brownie", eingang, eingang / "erledigt")
    assert sorted(p.name for p in neu) == ["brownie-1.png", "brownie-2.png"]
    assert not (eingang / "brownie-1.png").exists() and (eingang / "erledigt" / "brownie-2.png").exists()
    with pytest.raises(FileNotFoundError):
        im.erledigt("gibtsnicht", eingang, eingang / "erledigt")


def test_link_als_erledigt_markiert(eingang):
    im.link_erledigt("https://example.org/a", "neues-rezept", eingang / "links.txt", dt.date(2026, 10, 25))
    assert im.eingang(eingang, eingang / "links.txt")["links"] == []
    assert "# erledigt: 2026-10-25 → neues-rezept: https://example.org/a" in (eingang / "links.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize("menge,einheit,zutat,g", [
    (1, "Scoop", "Whey Protein Vanille", 30), (0.5, "cup", "Haferflocken zart", 45), (1, "Cup", "Skyr natur", 245),
    (2, "tbsp", "Erdnussbutter 100 % Erdnüsse", 32), (1, "TL", "Backpulver", 4), (1, "Prise", "Salz", 0.5),
    (2, "Eier", "Ei Gr. M ohne Schale", 120), (1, "Dose", "Kidneybohnen abgetropft", 250),
])
def test_umrechnung(menge, einheit, zutat, g):
    assert im.umrechnen(menge, einheit, zutat) == pytest.approx(g)


def test_umrechnung_unbekannte_einheit():
    with pytest.raises(ValueError):
        im.umrechnen(1, "Handvoll", "Mandeln gehobelt")


def test_aehnlichkeit_erkennt_dublette(echte_rezepte):
    kopie = copy.deepcopy(echte_rezepte["fruehstuecks-brownie"])
    kopie["id"], kopie["name"] = "brownie-kopie", "Schoko-Frühstücks-Brownie"
    for z in kopie["zutaten"]:
        if z.get("id") == "pb":
            z["g"] = 30
    treffer = im.aehnliche_rezepte(kopie, echte_rezepte)
    assert treffer and treffer[0][1] == "fruehstuecks-brownie" and treffer[0][0] >= 0.8


def test_bestand_ohne_dubletten(echte_rezepte):
    for rid, r in echte_rezepte.items():
        assert im.aehnliche_rezepte(r, echte_rezepte) == [], rid


def test_importiertes_rezept_vollstaendig(echte_rezepte, db):
    r = echte_rezepte["cookie-dough-protein-dip"]
    assert r["herkunft"]["art"] == "import" and r["inspiration"]["aenderungen"]
    assert pruefen.pruefe_rezept(r, db, r["id"]).ok
    assert (config.IMPORT_ERLEDIGT / "cookie-dough-dip-2.png").exists()


# --- Kühlschrank ------------------------------------------------------------------------
def test_kuehlschrank_findet_passende_gerichte(echte_rezepte, db):
    vs = ks.vorschlaege("Hähnchen, Reis, Skyr", echte_rezepte, db, vorrat=[], mahlzeit="Mittag/Abend")
    assert vs
    assert all(len(v["fehlend"]) <= config.KUEHLSCHRANK_MAX_FEHLEND for v in vs)
    assert all("hähnchen" in v["genutzt"] for v in vs)
    assert vs[0]["id"] in {"butter-chicken", "teriyaki-haehnchen-bowl", "haehnchen-burrito-bowl", "marry-me-chicken"}


def test_kuehlschrank_wortzuordnung(db):
    assert "Basmatireis ungekocht" in ks.zuordnen("reis", db)
    assert "Kaffee zubereitet" not in ks.zuordnen("reis", db)
    assert ks.zuordnen("eier", db) == ["Ei Gr. M ohne Schale"]
    assert "Hartweizennudeln ungekocht" in ks.zuordnen("pasta", db)


def test_kuehlschrank_faktor_an_restmakros(echte_rezepte, db):
    gegessen = {"kcal": 1700, "protein": 110, "fett": 70, "kh": 150}       # ca. 575 kcal offen
    vs = ks.vorschlaege("Hähnchen, Reis", echte_rezepte, db, vorrat=[], gegessen=gegessen, mahlzeit="Mittag/Abend")
    rest = config.TAGESZIELE["kcal"] - 1700
    for v in vs:
        assert v["faktor"] in config.KUEHLSCHRANK_FAKTOREN
        p = nw.rezept_naehrwerte(echte_rezepte[v["id"]], db)["portion"]
        besser = min(config.KUEHLSCHRANK_FAKTOREN, key=lambda f: abs(p["kcal"] * f - rest))
        assert abs(v["werte"]["kcal"] - rest) <= abs(p["kcal"] * besser - rest) + 0.25 * p["kcal"]


def test_kuehlschrank_ignoriert_aussortierte(echte_rezepte, db):
    r = copy.deepcopy(echte_rezepte)
    r["butter-chicken"]["bewertung"] = {"sterne": 1, "kommentar": "nein", "datum": "2026-10-25"}
    vs = ks.vorschlaege("Hähnchen, Reis, Skyr", r, db, vorrat=[], mahlzeit="Mittag/Abend", anzahl=50)
    assert "butter-chicken" not in {v["id"] for v in vs}


# --- Bewerten ----------------------------------------------------------------------------
@pytest.fixture
def rezeptordner(tmp_path):
    ziel = tmp_path / "rezepte"
    ziel.mkdir()
    shutil.copy(config.REZEPTE_DIR / "marry-me-chicken.yaml", ziel)
    return ziel


def test_bewerten_aendert_nur_eine_zeile(rezeptordner):
    pfad = rezeptordner / "marry-me-chicken.yaml"
    vorher = pfad.read_text(encoding="utf-8").splitlines()
    bewerten.bewerten("marry-me-chicken", 4, 'etwas mehr Sauce, "super"', dt.date(2026, 11, 8), rezeptordner)
    nachher = pfad.read_text(encoding="utf-8").splitlines()
    unterschiede = [(a, b) for a, b in zip(vorher, nachher) if a != b]
    assert len(vorher) == len(nachher) and len(unterschiede) == 1
    r = nw.lade_rezept(pfad)
    assert r["bewertung"] == {"sterne": 4, "kommentar": 'etwas mehr Sauce, "super"', "datum": dt.date(2026, 11, 8)}


@pytest.mark.parametrize("sterne", [0, 6, 3.5])
def test_bewerten_ungueltige_sterne(rezeptordner, sterne):
    with pytest.raises(ValueError):
        bewerten.bewerten("marry-me-chicken", sterne, None, None, rezeptordner)


def test_schlechte_bewertung_aussortiert(rezeptordner, db):
    bewerten.bewerten("marry-me-chicken", 2, "zu trocken", dt.date(2026, 11, 8), rezeptordner)
    r = nw.lade_rezept(rezeptordner / "marry-me-chicken.yaml")
    assert "(aussortiert)" in gen.rezeptbuch_markdown([r], db)
    assert pruefen.pruefe_rezept(r, db, r["id"]).ok
