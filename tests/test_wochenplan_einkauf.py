import copy
import datetime as dt
import math

import pytest
import yaml

import config
import einkauf as ek
import naehrwerte as nw
import wochenplan as wp


@pytest.fixture(scope="module")
def rezepte():
    return nw.lade_alle_rezepte()


@pytest.fixture(scope="module")
def packungen():
    return wp.lade_packungen()


@pytest.fixture
def plan():
    return wp.lade_plan("KW-45-2026")


def tag_von(plan, iso):
    return next(t for t in plan["tage"] if str(t["datum"]) == iso)


def fehler(plan, rezepte, db, packungen):
    return wp.pruefe_plan(plan, rezepte, db, packungen).fehler


# --- Schichten ----------------------------------------------------------------------
@pytest.mark.parametrize("iso,erwartet", [
    ("2026-11-01", "Tag"), ("2026-11-02", "Nacht"), ("2026-11-03", "frei"), ("2026-11-05", "frei"),
    ("2026-11-06", "Tag"), ("2026-11-07", "Nacht"), ("2026-10-31", "frei"), ("2026-11-11", "Tag"),
])
def test_schicht_aus_zyklus(iso, erwartet):
    assert wp.schicht(dt.date.fromisoformat(iso)) == erwartet


# --- Tagessummen ------------------------------------------------------------------------
def test_tagessumme_mit_faktor_snack_extras(rezepte, db):
    tag = {"datum": "2026-11-02",
           "fruehstueck": {"rezept": "protein-pancakes", "kochen": True},
           "mittag": {"rezept": "chili-con-carne", "faktor": 1.25, "kochen": True},
           "snack": {"rezept": "beeren-nice-cream", "kochen": True},
           "extras": [{"zutat": "Mandeln gehobelt", "g": 30}]}
    p = lambda i: nw.rezept_naehrwerte(rezepte[i], db)["portion"]
    erwartet = (p("protein-pancakes")["kcal"] + 1.25 * p("chili-con-carne")["kcal"] + p("beeren-nice-cream")["kcal"]
                + db["Mandeln gehobelt"]["kcal"] * 0.3)
    assert wp.tagessumme(tag, rezepte, db)["kcal"] == pytest.approx(erwartet)


def test_auswaerts_platzhalter(rezepte, db):
    tag = {"datum": "2026-11-03", "fruehstueck": {"rezept": "protein-pancakes", "kochen": True},
           "auswaerts": {"mahlzeit": "abend"}}
    s = wp.tagessumme(tag, rezepte, db)
    p = nw.rezept_naehrwerte(rezepte["protein-pancakes"], db)["portion"]
    for k in ("kcal", "protein", "fett", "kh"):
        assert s[k] == pytest.approx(p[k] + config.AUSWAERTS[k])
    assert config.AUSWAERTS == {"kcal": 950, "protein": 40, "fett": 45, "kh": 90}


def test_auswaerts_erzeugt_keine_zutaten(rezepte):
    plan = {"kw": 1, "jahr": 2026, "name": "t", "einkauf": [{"tag": "Sa", "datum": "2026-11-07"}],
            "tage": [{"datum": "2026-11-08", "auswaerts": {"mahlzeit": "abend"}}]}
    assert ek.nutzungen(plan, rezepte) == {}
    assert ek.gesamtbedarf(plan, rezepte) == 0


# --- Echter Plan -------------------------------------------------------------------------
def test_echter_plan_kw45_erfuellt_alle_regeln(plan, rezepte, db, packungen):
    p = wp.pruefe_plan(plan, rezepte, db, packungen)
    assert p.fehler == []
    for tag in plan["tage"]:
        s = wp.tagessumme(tag, rezepte, db)
        assert s["protein"] >= config.PLAN_PROTEIN_MIN
        assert abs(s["kcal"] - config.TAGESZIELE["kcal"]) <= config.PLAN_KCAL_TOLERANZ
        assert config.PLAN_FETT_MIN <= s["fett"] and abs(s["fett"] - config.TAGESZIELE["fett"]) <= config.PLAN_FETT_TOLERANZ
        assert abs(s["kh"] - config.TAGESZIELE["kh"]) <= config.PLAN_KH_TOLERANZ


def test_markdown_wochenplan_abschnitte(plan, rezepte, db):
    md = wp.wochenplan_markdown(plan, rezepte, db)
    for teil in ["## Übersicht", "**Zeitplan:**", "**Erinnerungen für morgen:**", "## Reste-Übersicht",
                 "## Meal-Prep-Plan", "## Wochenbilanz", "Nachtschicht", "📦 Box"]:
        assert teil in md, teil


# --- Regelverstöße -------------------------------------------------------------------------
def test_zu_wenig_protein(plan, rezepte, db, packungen):
    tag_von(plan, "2026-11-08")["extras"] = []
    tag_von(plan, "2026-11-08")["abend"] = {"rezept": "mie-nudeln-pute", "kochen": True}
    assert any("So 08.11." in f for f in fehler(plan, rezepte, db, packungen))


def test_aussortiertes_rezept_nie_geplant(plan, rezepte, db, packungen):
    r = copy.deepcopy(rezepte)
    r["haehnchen-piccata"]["bewertung"] = {"sterne": 2, "kommentar": "zu trocken", "datum": "2026-11-01"}
    assert any("aussortiert" in f for f in fehler(plan, r, db, packungen))


def test_drei_sterne_max_einmal(plan, rezepte, db, packungen):
    r = copy.deepcopy(rezepte)
    for i in ("haehnchen-piccata", "rindergulasch"):
        r[i]["bewertung"] = {"sterne": 3, "kommentar": None, "datum": None}
    assert any("3-Sterne" in f for f in fehler(plan, r, db, packungen))


def test_hack_spaeter_als_2_tage_ohne_einfrieren(plan, rezepte, db, packungen):
    tag_von(plan, "2026-11-04")["abend"].pop("einfrieren")
    assert any("Rinderhackfleisch" in f and "einfrieren" in f for f in fehler(plan, rezepte, db, packungen))


def test_tk_fisch_erzeugt_auftau_erinnerung(plan, rezepte, db, packungen):
    p = wp.pruefe_plan(plan, rezepte, db, packungen)
    assert any("Lachs" in t and "auftauen" in t for t in p.erinnerungen[dt.date(2026, 11, 4)])


def test_rest_zu_alt(plan, rezepte, db, packungen):
    # Lachs-Bowl (1 Tag haltbar) erst 2 Tage später essen
    tag_von(plan, "2026-11-03")["mittag"] = None
    tag_von(plan, "2026-11-04")["mittag"] = {"rezept": "lachs-reis-bowl", "rest_von": "2026-11-02/abend"}
    assert any("Tage alt" in f for f in fehler(plan, rezepte, db, packungen))


def test_mehr_reste_als_ladungen(plan, rezepte, db, packungen):
    tag_von(plan, "2026-11-08")["abend"] = {"rezept": "wrap-hack-putenhack", "rest_von": "2026-11-07/abend"}
    assert any("Ladung" in f for f in fehler(plan, rezepte, db, packungen))


def test_faktor_nur_viertelschritte(plan, rezepte, db, packungen):
    tag_von(plan, "2026-11-03")["abend"]["faktor"] = 1.3
    assert any("Faktor" in f for f in fehler(plan, rezepte, db, packungen))


def test_abendessen_gleiche_kueche_folgetag(plan, rezepte, db, packungen):
    # Di Wrap-Hack und Mi Burrito-Bowl: zweimal Mexikanisch hintereinander am Abend
    tag_von(plan, "2026-11-03")["abend"] = {"rezept": "wrap-hack-putenhack", "kochen": True}
    tag_von(plan, "2026-11-04")["abend"]["rezept"] = "haehnchen-burrito-bowl"
    tag_von(plan, "2026-11-04")["abend"].pop("einfrieren")
    tag_von(plan, "2026-11-06")["mittag"]["rezept"] = "haehnchen-burrito-bowl"
    assert any("Mexikanisch" in f for f in fehler(plan, rezepte, db, packungen))


# --- Einkauf -------------------------------------------------------------------------------
def test_kontrollrechnung(plan, rezepte, db, packungen):
    listen, _ = ek.berechne(plan, rezepte, db, packungen)
    k = ek.kontrolle(plan, rezepte, listen)
    assert k["stimmt"]
    assert k["rezeptmengen"] == pytest.approx(k["zu_kaufen"] + k["aus_bestand"])


def test_aufrunden_auf_packungen(plan, rezepte, db, packungen):
    listen, _ = ek.berechne(plan, rezepte, db, packungen, vorrat=[])
    z = next(z for z in listen[0].zeilen if z.zutat == "Rinderhackfleisch 5 % Fett roh")
    assert z.bedarf == pytest.approx(2 * 350 * 0.75 + 400 * 1.25)   # Chili × 2 Ladungen × 0,75 + Frikadellen × 1,25
    assert z.pakete == math.ceil(z.bedarf / 400) == 3


def test_vorratsabzug(plan, rezepte, db, packungen):
    ohne, _ = ek.berechne(plan, rezepte, db, packungen, vorrat=[])
    mit, _ = ek.berechne(plan, rezepte, db, packungen, vorrat=[{"zutat": "Magerquark", "g": 500},
                                                               {"zutat": "Rapsöl", "g": None}])
    q0 = next(z for z in ohne[0].zeilen if z.zutat == "Magerquark")
    q1 = next(z for z in mit[0].zeilen if z.zutat == "Magerquark")
    assert q1.aus_bestand == 500 and q1.pakete == q0.pakete - 1
    oel = next(z for z in mit[0].zeilen if z.zutat == "Rapsöl")
    assert oel.pakete == 0 and oel.vorrat_unbekannt


def test_zwei_einkaufstermine_getrennt(plan, rezepte, db, packungen):
    listen, _ = ek.berechne(plan, rezepte, db, packungen)
    assert [l.datum for l in listen] == [dt.date(2026, 10, 31), dt.date(2026, 11, 7)]
    zweite = {z.zutat for z in listen[1].zeilen}
    assert "Rindergulasch roh" in zweite and "Rindergulasch roh" not in {z.zutat for z in listen[0].zeilen}


def test_faktor_skaliert_einkauf(rezepte):
    basis = {"kw": 1, "jahr": 2026, "name": "t", "einkauf": [{"tag": "Sa", "datum": "2026-11-07"}],
             "tage": [{"datum": "2026-11-08", "abend": {"rezept": "marry-me-chicken", "kochen": True}}]}
    gross = copy.deepcopy(basis)
    gross["tage"][0]["abend"]["faktor"] = 1.5
    n1 = ek.nutzungen(basis, rezepte)["Hähnchenbrustfilet roh"][0].g
    n2 = ek.nutzungen(gross, rezepte)["Hähnchenbrustfilet roh"][0].g
    assert n2 == pytest.approx(1.5 * n1)


def test_reste_landen_im_vorrat(plan, rezepte, db, packungen, tmp_path):
    pfad = tmp_path / "vorrat.yaml"
    pfad.write_text(yaml.safe_dump({"vorrat": [{"zutat": "Rapsöl", "g": None}]}), encoding="utf-8")
    _, reste = ek.berechne(plan, rezepte, db, packungen, vorrat=ek.lade_vorrat(pfad))
    ek.reste_uebernehmen(reste, pfad)
    neu = {v["zutat"]: v for v in ek.lade_vorrat(pfad)}
    assert neu["Rapsöl"]["g"] is None                      # unbekannte Menge bleibt unbekannt
    rest = next(z for z, v in reste.items() if z != "Rapsöl" and v["g"])
    assert neu[rest]["g"] == round(reste[rest]["g"])
    assert "haltbar_bis" in neu[rest]


def test_einkaufsliste_markdown(plan, rezepte, db, packungen):
    listen, reste = ek.berechne(plan, rezepte, db, packungen)
    md = ek.einkauf_markdown(plan, rezepte, db, listen, reste)
    for teil in ["- [ ] **", "wofür:", "### Vorrat prüfen", "### Kostenschätzung", "## Budget",
                 "## Reste nach der Woche", "## Kontrollrechnung", "**stimmt**", "einfrieren"]:
        assert teil in md, teil
    reihenfolge = [md.index(f"### {a}") for a in config.PROFIL["einkauf"]["abteilungen"] if f"### {a}" in md.split("## Einkauf Samstag, 07.11.2026")[0]]
    assert reihenfolge == sorted(reihenfolge)


def test_kw45_ohne_extras_regelkonform(rezepte, db, packungen):
    """Fettstrategie „rezepte“: Der echte Plan trifft alle Regeln aus 8.2 ohne Nüsse-Extras."""
    echt = wp.lade_plan(config.WOCHENPLAENE_DIR / "KW-45-2026.yaml")
    assert all(not t.get("extras") for t in echt["tage"])
    assert fehler(echt, rezepte, db, packungen) == []


def test_kosten_teuerste_posten_je_zutat(plan, rezepte, db, packungen):
    listen, _ = ek.berechne(plan, rezepte, db, packungen)
    k = ek.kosten(listen)
    namen = [t["zutat"] for t in k["teuer"]]
    assert len(namen) == len(set(namen)) == 3                 # Zutat aus beiden Einkäufen nur einmal
    assert k["woche"] + k["vorrat"] == pytest.approx(sum(z.kosten for l in listen for z in l.zeilen if z.pakete))
