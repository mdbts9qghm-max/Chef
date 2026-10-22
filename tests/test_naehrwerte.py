import pytest

import config
import naehrwerte as nw


def test_naehrwerte_bekanntes_rezept(mini_db, testrezept):
    erg = nw.rezept_naehrwerte(testrezept, mini_db)
    # 300 g Testhuhn = 300 kcal, 60 P; 150 g Testreis = 525 kcal, 12 P; Ei 120 g = 168 kcal, 15,12 P
    assert erg["gesamt"]["kcal"] == pytest.approx(300 + 525 + 168)
    assert erg["gesamt"]["protein"] == pytest.approx(60 + 12 + 15.12)
    assert erg["portion"]["kcal"] == pytest.approx(496.5)
    # Salz: 0,5 g gezählt, Kochwasser-Salz (nicht_mitgerechnet) nicht; Ei 0,42 g
    assert erg["gesamt"]["salz"] == pytest.approx(0.6 + 0.5 + 0.42)
    # Gargewicht: 300*0,75 + 150*2,8 + 0,5 + 120 (ohne Kochwasser-Salz)
    assert erg["gargewicht_gesamt"] == pytest.approx(225 + 420 + 0.5 + 120)


def test_rundung_kaufmaennisch(mini_db, testrezept):
    p = nw.runden(nw.rezept_naehrwerte(testrezept, mini_db)["portion"])
    assert p["kcal"] == 497          # 496,5 → 497 (nicht 496)
    assert p["protein"] == 43.6      # 43,56 → 43,6
    assert nw.rund(12.5) == 13
    assert nw.rund(0.25, 1) == 0.3


def test_zahlformat():
    assert nw.zahl(1234.56) == "1.234,6"
    assert nw.zahl(1482.5, 0) == "1.483"
    assert nw.zahl(12.0) == "12"
    assert nw.gramm(0.5) == "0,5 g"
    assert nw.gramm(120) == "120 g"


def test_faktor_skaliert(mini_db, testrezept):
    basis = nw.rezept_naehrwerte(testrezept, mini_db)
    skaliert = nw.rezept_naehrwerte(testrezept, mini_db, faktor=1.25)
    for k in nw.NAEHRSTOFFE:
        assert skaliert["portion"][k] == pytest.approx(basis["portion"][k] * 1.25)
    assert skaliert["gargewicht_gesamt"] == pytest.approx(basis["gargewicht_gesamt"] * 1.25)


def test_plausibilitaet_manipulierte_zutat(mini_db):
    assert not nw.plausibilitaet_zutat("Testfalsch", mini_db)["ok"]   # 200 kcal vs. 69 berechnet
    assert nw.plausibilitaet_zutat("Testhuhn", mini_db)["ok"]


def test_plausibilitaet_kleine_kcal_absolute_toleranz(mini_db):
    # Testgewürz: 4+20+9+4 = 37 statt 40 kcal → −7,5 %, aber nur 3 kcal → bestanden
    p = nw.plausibilitaet_zutat("Testgewürz", mini_db)
    assert abs(p["prozent"]) > config.PLAUSI_PROZENT
    assert p["ok"]


def test_plausibilitaet_rezept_streng(mini_db, testrezept):
    assert nw.plausibilitaet_rezept(testrezept, mini_db, nw.rezept_naehrwerte(testrezept, mini_db)["gesamt"])["ok"]
    testrezept["zutaten"].append({"id": "falsch", "zutat": "Testfalsch", "g": 400})
    gesamt = nw.rezept_naehrwerte(testrezept, mini_db)["gesamt"]
    assert not nw.plausibilitaet_rezept(testrezept, mini_db, gesamt)["ok"]


def test_polyol_ausnahme(db):
    assert nw.plausibilitaet_zutat("Erythrit", db)["ok"]


def test_alle_zutaten_der_datenbank_plausibel(db):
    falsch = [n for n in db if not nw.plausibilitaet_zutat(n, db)["ok"]]
    assert falsch == []


@pytest.mark.parametrize("vorb,kochen,warte,erwartet", [(10, 15, 0, True), (10, 16, 0, False), (5, 20, 480, True)])
def test_kategorie_schnell_grenze(testrezept, vorb, kochen, warte, erwartet):
    testrezept["zeit"] = {"vorbereitung": vorb, "kochen": kochen, "wartezeit": warte}
    assert nw.ist_schnell(testrezept) is erwartet


@pytest.mark.parametrize("kcal,protein,erwartet", [(550, 35, True), (551, 35, False), (550, 34.9, False)])
def test_kategorie_kalorienarm_grenze(testrezept, kcal, protein, erwartet):
    assert nw.ist_kalorienarm(testrezept, {"kcal": kcal, "protein": protein}) is erwartet


def test_kalorienarm_nur_hauptgericht(testrezept):
    testrezept["mahlzeit"] = "Snack"
    assert not nw.ist_kalorienarm(testrezept, {"kcal": 300, "protein": 40})


@pytest.mark.parametrize("kcal,protein,erwartet", [
    (800, 40, True),     # genau 40 g
    (800, 39.9, False),
    (300, 30, True),     # genau 10 g pro 100 kcal
    (300, 29.9, False),
])
def test_kategorie_high_protein_grenze(kcal, protein, erwartet):
    assert nw.ist_high_protein({"kcal": kcal, "protein": protein}) is erwartet


def test_kategorien_reihenfolge(testrezept, mini_db):
    testrezept["kategorien_manuell"] = ["Meal Prep"]
    kats = nw.kategorien(testrezept, nw.rezept_naehrwerte(testrezept, mini_db)["portion"])
    assert kats == ["High Protein", "Schnelle Rezepte", "Meal Prep", "Kalorienarm"]


def test_hauptproteinquelle(mini_db, testrezept):
    assert nw.hauptproteinquelle(testrezept, mini_db) == "haehnchen"
    assert nw.proteinquellen(testrezept, mini_db) == ["haehnchen", "ei"]
