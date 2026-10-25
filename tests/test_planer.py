"""Planer (tools/planer.py): Struktur aus dem Schichtplan, regelkonforme und günstige Wochen, feste Vorgaben."""
import datetime as dt

import pytest
import yaml

import config
import einkauf as ek
import planer
import wochenplan as wp

D = dt.date


@pytest.fixture(scope="module")
def daten():
    return planer.Daten()


@pytest.fixture
def breite_kcal(monkeypatch):
    """Mechanik-Tests mit wenigen Starts: alte Spanne ±100 kcal (die echte Regel prüfen die echten Pläne)."""
    monkeypatch.setattr(config, "PLAN_KCAL_MAX", config.TAGESZIELE["kcal"] + 100)
    monkeypatch.setattr(config, "PLANER_RAND", {"protein": 1.0, "kcal": 10.0, "fett": 1.0, "kh": 2.0})


def test_woche_und_einkaufstermine():
    kw, jahr, tage = planer.woche("KW-45-2026")
    assert (kw, jahr, tage[0], tage[-1]) == (45, 2026, D(2026, 11, 2), D(2026, 11, 8))
    assert planer.einkaufstermine(tage) == [D(2026, 10, 31), D(2026, 11, 7)]
    with pytest.raises(ValueError):
        planer.woche("Woche 45")


def test_struktur_aus_schichtplan():
    _, _, tage = planer.woche("KW-45-2026")          # Mo Nacht · Di–Do frei · Fr Tag · Sa Nacht · So frei
    st = planer.struktur(tage)
    rest = {(a.isoformat(), s): (b.isoformat(), t) for (a, s), (b, t) in st["rest"].items()}
    assert rest[("2026-11-03", "mittag")] == ("2026-11-02", "abend")          # Abendessen → Mittag am Folgetag
    assert rest[("2026-11-06", "mittag")] == ("2026-11-05", "abend")          # Box für die Tagschicht
    assert rest[("2026-11-06", "abend")] == ("2026-11-05", "mittag")          # Meal Prep → Abend nach der Schicht
    assert (D(2026, 11, 5), "mittag") in st["koch"] and (D(2026, 11, 4), "abend") in st["koch"]
    assert ("2026-11-05", "mittag") not in rest                                # wird für Fr gekocht, kein Rest
    assert planer.kochtag(D(2026, 11, 6), st["schicht"]) == D(2026, 11, 5)


def test_planer_liefert_regelkonformen_guenstigen_plan(daten, breite_kcal):
    p = planer.Planer("KW-45-2026", daten=daten, budget=100)
    fehler, kosten, _, plan, k, pr = p.planen(starts=10, seed=3)
    assert fehler == 0 and pr.fehler == []
    assert all(not t.get("extras") for t in plan["tage"])
    alt = wp.lade_plan(config.WURZEL / "tests" / "daten" / "KW-45-2026.yaml")
    alt_kosten = ek.kosten(ek.berechne(alt, daten.rz, daten.db, daten.pk, daten.vorrat)[0])["woche"]
    assert kosten < alt_kosten                                                  # günstiger als der Plan von vorher
    # geschriebenes YAML ist gültig und ergibt denselben Plan
    neu = yaml.safe_load(p.yaml_text(plan, kosten))
    neu["name"] = "KW-45-2026"
    assert wp.pruefe_plan(neu, daten.rz, daten.db, daten.pk).fehler == []


def test_gleiches_fruehstueck_wird_einmal_gebacken(daten):
    p = planer.Planer("KW-45-2026", daten=daten)
    w = p.start(__import__("random").Random(1))
    w["fr"] = {d: "fruehstuecks-brownie" if d in (D(2026, 11, 3), D(2026, 11, 4)) else "protein-pancakes" for d in p.tage}
    w["ff"] = {d: 1.0 for d in p.tage}
    m = p.mahlzeiten(w)
    assert m[(D(2026, 11, 3), "fruehstueck")]["ladungen"] == 2
    assert m[(D(2026, 11, 4), "fruehstueck")]["rest_von"] == (D(2026, 11, 3), "fruehstueck")


def test_feste_vorgaben_bleiben(daten):
    fest = {(D(2026, 11, 8), "abend"): "marry-me-chicken", (D(2026, 11, 3), "fruehstueck"): "protein-waffeln"}
    p = planer.Planer("KW-45-2026", daten=daten, fest=fest)
    _, _, _, plan, _, _ = p.planen(starts=2, seed=1)
    tage = {t["datum"]: t for t in plan["tage"]}
    assert tage[D(2026, 11, 8)]["abend"]["rezept"] == "marry-me-chicken" and tage[D(2026, 11, 8)]["abend"]["fest"]
    assert tage[D(2026, 11, 3)]["fruehstueck"]["rezept"] == "protein-waffeln"


def test_wiederholungsregeln_in_der_pruefung(daten):
    plan = wp.lade_plan(config.WURZEL / "tests" / "daten" / "KW-45-2026.yaml")
    tag = next(t for t in plan["tage"] if str(t["datum"]) == "2026-11-08")
    tag["abend"] = {"rezept": "lachs-reis-bowl", "kochen": True}        # schon Mo gekocht
    assert any("2× gekocht" in f for f in wp.pruefe_plan(plan, daten.rz, daten.db, daten.pk).fehler)


def test_starteinkauf_statt_samstag(daten, breite_kcal):
    p = planer.Planer("KW-44-2026", daten=daten, termine=[D(2026, 10, 26)])
    fehler, _, _, plan, _, pr = p.planen(starts=4, seed=2)
    assert plan["einkauf"] == [{"tag": "Mo", "datum": D(2026, 10, 26), "art": "start"}]
    assert fehler == 0, pr.fehler
    # Hack/Fisch/Fleisch ab Mittwoch: eingefroren (Frische ab Montagseinkauf)
    for t in plan["tage"]:
        for slot in ("mittag", "abend"):
            e = t[slot]
            if e and e.get("kochen") and (t["datum"] - D(2026, 10, 26)).days > 4:
                quellen = {wp.frische_typen(daten.rz[e["rezept"]], daten.db, daten.pk)[i][1]
                           for i in range(len(wp.frische_typen(daten.rz[e["rezept"]], daten.db, daten.pk)))}
                if "frisch" in quellen:
                    assert e.get("einfrieren"), (t["datum"], e)


def test_eigenes_minimalrezept_nur_warnungen(daten):
    import pruefen
    r = {"id": "mein-test", "name": "Mein Test", "hauptkategorie": "high-protein", "kategorien_manuell": [],
         "mahlzeit": "Mittag/Abend", "geschmack": "herzhaft", "kueche": "Deutsch",
         "herkunft": {"art": "eigen", "quelle": "App", "datum": D(2026, 10, 26)}, "schwierigkeit": "leicht",
         "zeit": {"vorbereitung": 5, "kochen": 10, "wartezeit": 0}, "ausstattung": [],
         "zutaten": [{"id": "z1", "zutat": "Magerquark", "g": 250}], "mise_en_place": [],
         "schritte": [{"titel": "Schritt 1", "text": "Verrühren.", "timer_min": None}], "zeitablauf": [], "fehler": [],
         "anrichten": "", "aufbewahrung": {"kuehlschrank_tage": 1, "einfrierbar": False, "aufwaermen": "Frisch essen."},
         "varianten": [], "tipps": [], "gargewicht_g": None, "bewertung": {"sterne": None, "kommentar": None, "datum": None}}
    e = pruefen.pruefe_rezept(r, daten.db, "mein-test")
    assert e.ok and e.warnungen                                   # Korridor, Platzhalter, Umfang → nur Warnungen
    r["herkunft"]["art"] = "neu"
    assert not pruefen.pruefe_rezept(r, daten.db, "mein-test").ok  # für normale Rezepte bleiben es Fehler
