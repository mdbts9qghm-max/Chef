"""Automatische Wochenplanung (tools/woche_auto.py) – mit tmp-Ordnern und wenigen Starts."""
import datetime as dt
import shutil

import pytest
import yaml

import config
import einkauf as ek
import woche_auto as wa
import wochenplan as wp

D = dt.date


def test_naechste_woche():
    assert wa.naechste_woche(D(2026, 10, 30)) == "KW-45-2026"       # Freitag → ab Mo 2.11.
    assert wa.naechste_woche(D(2026, 11, 2)) == "KW-46-2026"        # Montag → die Woche danach
    assert wa.naechste_woche(D(2026, 12, 25)) == "KW-53-2026"
    assert wa.kw_name(D(2027, 1, 4)) == "KW-01-2027"


@pytest.fixture
def ordner(tmp_path, monkeypatch):
    plaene = tmp_path / "wochenplaene"
    plaene.mkdir()
    shutil.copy(config.WURZEL / "tests" / "daten" / "KW-45-2026.yaml", plaene / "KW-45-2026.yaml")
    vorrat = tmp_path / "vorrat.yaml"
    vorrat.write_text(yaml.safe_dump({"vorrat": [{"zutat": "Rapsöl", "g": None}]}), encoding="utf-8")
    # breite kcal-Spanne: Mechanik testen, nicht die Enge der echten Regel
    monkeypatch.setattr(config, "PLAN_KCAL_MAX", config.TAGESZIELE["kcal"] + 100)
    monkeypatch.setattr(config, "PLANER_RAND", {"protein": 1.0, "kcal": 10.0, "fett": 1.0, "kh": 2.0})
    return plaene, vorrat


def test_vorhandener_plan_bleibt(ordner):
    plaene, vorrat = ordner
    vorher = (plaene / "KW-45-2026.yaml").read_text(encoding="utf-8")
    status, name, _ = wa.planen(D(2026, 10, 30), plaene, vorrat, starts=2, seeds=(1,), ausgabe=lambda *_: None)
    assert (status, name) == ("vorhanden", "KW-45-2026")
    assert (plaene / "KW-45-2026.yaml").read_text(encoding="utf-8") == vorher


def test_plant_naechste_woche_und_uebernimmt_reste_einmal(ordner):
    plaene, vorrat = ordner
    # Freitag in KW 45 → plant KW 46, Reste aus KW 45 in den Vorrat
    status, name, info = wa.planen(D(2026, 11, 6), plaene, vorrat, starts=6, seeds=(1, 2), ausgabe=lambda *_: None)
    assert (status, name) == ("geplant", "KW-46-2026")
    plan = wp.lade_plan(plaene / "KW-46-2026.yaml")
    assert len(plan["einkauf"]) == 1 and str(plan["einkauf"][0]["datum"]) == "2026-11-07"
    assert wp.pruefe_plan(plan, *_daten()).fehler == []
    d = ek.lade_vorrat_datei(vorrat)
    assert d["reste_uebernommen"] == ["KW-45-2026"]
    assert any(v.get("aus") == "KW-45-2026" for v in d["vorrat"])
    # zweiter Lauf: Reste nicht doppelt
    vorher = vorrat.read_text(encoding="utf-8")
    assert wa.reste_uebernehmen("KW-45-2026", plaene, vorrat, *_rz_db()) == 0
    assert vorrat.read_text(encoding="utf-8") == vorher


def test_reste_nur_fuer_spaetere_wochen_und_nicht_abgelaufen():
    vorrat = [{"zutat": "Skyr natur", "g": 200, "haltbar_bis": "2026-11-01", "aus": "KW-44-2026"},
              {"zutat": "Butter", "g": 100, "haltbar_bis": "2027-01-01", "aus": "KW-44-2026"},
              {"zutat": "Rapsöl", "g": None}]
    namen = lambda v: [x["zutat"] for x in v]
    assert namen(ek.gueltiger_vorrat(vorrat, D(2026, 11, 2), "KW-45-2026")) == ["Butter", "Rapsöl"]   # Skyr abgelaufen
    assert namen(ek.gueltiger_vorrat(vorrat, D(2026, 10, 26), "KW-44-2026")) == ["Rapsöl"]           # eigene Reste nicht


def _rz_db():
    import naehrwerte as nw
    return nw.lade_alle_rezepte(), nw.lade_zutaten()


def _daten():
    rz, db = _rz_db()
    return rz, db, wp.lade_packungen()
