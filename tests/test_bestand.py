import bestand
import config
import naehrwerte as nw


def eintrag(bereich="Hauptgericht", kueche="Deutsch", protein="rind", kategorien=("High Protein",), insp=False):
    return {"id": "x", "name": "x", "bereich": bereich, "kueche": kueche, "protein": protein,
            "kategorien": set(kategorien), "inspiration": insp}


def zeile(zeilen, name):
    return next(z for z in zeilen if z[0] == name)


def test_auswertung_zaehlt_kuechen_nur_bei_hauptgerichten():
    zeilen = bestand.auswerten([eintrag(), eintrag(bereich="Frühstück", kueche="Deutsch")], vollstaendig=False)
    assert zeile(zeilen, "Küche Deutsch")[2] == "1"


def test_auswertung_proteinquelle_ueber_maximum():
    zeilen = bestand.auswerten([eintrag(protein="haehnchen")] * 11, vollstaendig=False)
    assert zeile(zeilen, "Hauptprotein Hähnchen")[3] is False


def test_fisch_und_garnelen_sind_eine_gruppe():
    zeilen = bestand.auswerten([eintrag(protein="fisch")] * 6 + [eintrag(protein="garnelen")] * 5,
                               vollstaendig=False)
    assert zeile(zeilen, "Hauptprotein Fisch & Garnelen")[2:] == ("11", False)


def test_zwischenstand_mindestwerte_offen_exakte_als_obergrenze():
    zeilen = bestand.auswerten([eintrag()] * 5, vollstaendig=False)
    assert zeile(zeilen, "Meal Prep")[3] is None          # noch offen, kein Verstoß
    assert zeile(zeilen, "Küche Deutsch")[3] is False     # 5 > 4: schon jetzt ein Verstoß


def test_vollstaendig_exakte_werte_verlangt():
    zeilen = bestand.auswerten([eintrag()] * 4, vollstaendig=True)
    assert zeile(zeilen, "Rezepte gesamt")[3] is False
    assert zeile(zeilen, "Küche Deutsch")[3] is True


def test_rezeptplan_erfuellt_spec():
    plan = bestand.lade_plan()
    zeilen = bestand.auswerten([bestand.eintrag_aus_plan(p) for p in plan])
    assert [z for z in zeilen if z[3] is not True] == []
    ids = [p["id"] for p in plan]
    assert len(ids) == len(set(ids)) == config.BESTAND_GESAMT


def test_echte_rezepte_im_plan_und_passend(echte_rezepte, db):
    """Jedes geschriebene Rezept steht im Plan und hat dort Bereich und Küche."""
    plan = {p["id"]: p for p in bestand.lade_plan()}
    for r in echte_rezepte.values():
        assert r["id"] in plan, r["id"]
        e = bestand.eintrag_aus_rezept(r, db)
        assert e["bereich"] == plan[r["id"]]["bereich"]
        assert e["kueche"] == plan[r["id"]]["kueche"]
        assert e["protein"] == plan[r["id"]]["protein"] or e["bereich"] != "Hauptgericht"


def test_bestand_gegen_spec(echte_rezepte, db):
    """Zwischenstand: keine Verstöße. Sobald 50 Rezepte existieren: alle Vorgaben aus 5.1–5.3 exakt."""
    ist = [bestand.eintrag_aus_rezept(r, db) for r in echte_rezepte.values()]
    vollstaendig = len(ist) >= config.BESTAND_GESAMT
    zeilen = bestand.auswerten(ist, vollstaendig=vollstaendig)
    assert [z for z in zeilen if z[3] is False] == []
    if vollstaendig:
        assert all(z[3] is True for z in zeilen)


def test_zutaten_der_rezepte_existieren_und_limit(echte_rezepte, db):
    """SPEC 5.3: max. ca. 90 verschiedene Zutaten (Wasser wird nicht eingekauft, zählt nicht)."""
    genutzt = {z["zutat"] for r in echte_rezepte.values() for z in nw.zutaten_eintraege(r)}
    assert genutzt <= set(db)
    assert len(genutzt - config.NICHT_EINKAUFEN) <= config.ZUTATEN_MAX
