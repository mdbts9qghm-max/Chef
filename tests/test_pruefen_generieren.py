import re

import config
import generieren as gen
import naehrwerte as nw
import pruefen


# --- Platzhalter -----------------------------------------------------------------
def test_platzhalter_menge_und_name(testrezept):
    t = gen.ersetze_platzhalter("{huhn} und {reis:n}", testrezept)
    assert t == "300 g Testhuhn und Testreis"


def test_platzhalter_stueckangabe(testrezept):
    assert gen.ersetze_platzhalter("{eier}", testrezept) == "2 Eier Gr. M (120 g)"
    assert gen.ersetze_platzhalter("{eier:n}", testrezept) == "Eier"


def test_platzhalter_prise(testrezept):
    assert gen.ersetze_platzhalter("{salz}", testrezept) == "1 Prise Salz (0,5 g)"


def test_platzhalter_mit_faktor(testrezept):
    assert gen.ersetze_platzhalter("{huhn}", testrezept, faktor=1.5) == "450 g Testhuhn"


def test_zutatentabelle_nicht_mitgerechnet(testrezept):
    zeilen = "\n".join(gen.abschnitt_zutaten(testrezept))
    assert "| Eier | 2 Eier Gr. M (120 g) |" in zeilen
    assert "nicht mitgerechnet" in zeilen


# --- Prüfungen an den echten Beispielrezepten ---------------------------------------
def test_beispielrezepte_bestehen(echte_rezepte, db):
    for e in pruefen.pruefe_alle(echte_rezepte, db):
        assert e.ok, (e.rezept_id, e.fehler)


def fehler(rezept, db):
    return pruefen.pruefe_rezept(rezept, db, rezept["id"]).fehler


def test_fehlende_kerntemperatur(chicken, db):
    for s in chicken["schritte"]:
        s["text"] = s["text"].replace("Kerntemperatur", "").replace("Garprobe", "")
    assert any("Kerntemperatur" in f for f in fehler(chicken, db))


def test_ofen_ohne_modus(brownie, db):
    for s in brownie["schritte"]:
        s["text"] = s["text"].replace(" (160 °C Umluft)", "")
    assert any("Umluft" in f for f in fehler(brownie, db))


def test_fisch_nicht_laenger_als_2_tage(chicken, db):
    for z in chicken["zutaten"]:
        if z.get("id") == "haehnchen":
            z["zutat"] = "Lachsfilet ohne Haut roh"
    assert any("Fisch" in f for f in fehler(chicken, db))


def test_zielkorridor_verfehlt(chicken, db):
    for z in chicken["zutaten"]:
        if z.get("id") == "reis":
            z["g"] = 400
    assert any("Maximum" in f for f in fehler(chicken, db))


def test_hauptkategorie_nicht_erfuellt(chicken, db):
    chicken["hauptkategorie"] = "schnell"
    assert any("Hauptkategorie" in f for f in fehler(chicken, db))


def test_unbekannter_und_ungenutzter_platzhalter(chicken, db):
    chicken["schritte"][0]["text"] += " {gibtsnicht}"
    chicken["anrichten"] = chicken["anrichten"]  # unverändert
    chicken["zutaten"].append({"id": "extra", "zutat": "Salz", "g": 1})
    f = fehler(chicken, db)
    assert any("{gibtsnicht}" in x for x in f)
    assert any("{extra}" in x for x in f)


def test_unbekannte_zutat(chicken, db):
    chicken["zutaten"].append({"id": "exot", "zutat": "Drachenfrucht", "g": 50})
    assert any("nicht in zutaten.csv" in f for f in fehler(chicken, db))


def test_meal_prep_braucht_3_tage(brownie, db):
    brownie["aufbewahrung"]["kuehlschrank_tage"] = 2
    assert any("Meal Prep" in f for f in fehler(brownie, db))


def test_dateiname_gleich_id(chicken, db):
    assert any("Dateiname" in f for f in pruefen.pruefe_rezept(chicken, db, "anderer-name").fehler)


def test_herzhaftes_fruehstueck_nur_warnung(brownie, db):
    brownie["geschmack"] = "herzhaft"
    e = pruefen.pruefe_rezept(brownie, db, brownie["id"])
    assert e.ok and any("nicht süß" in w for w in e.warnungen)


def test_zucker_warnung(brownie, db):
    for z in brownie["zutaten"]:
        if z.get("id") == "banane":
            z["g"] = 160
    e = pruefen.pruefe_rezept(brownie, db, brownie["id"])
    assert any("Zucker" in w for w in e.warnungen)


# --- Markdown -----------------------------------------------------------------------
def test_markdown_abschnitte_in_reihenfolge(echte_rezepte, db):
    for r in echte_rezepte.values():
        md = gen.rezept_markdown(r, db)
        assert md.splitlines()[1] == f"# {r['name']}"
        titel = re.findall(r"^## (.+)$", md, flags=re.M)
        assert titel == config.MD_ABSCHNITTE


def test_markdown_kopf_und_naehrwerte(chicken, db):
    md = gen.rezept_markdown(chicken, db)
    for teil in ["**Bewertung:**", "**Kategorien:**", "**Küche:**", "**Inspiration:**", "**Mahlzeit:**",
                 "**Portionen:** 2", "**Schwierigkeit:**", "**Zeit:**", "**Ausstattung:**",
                 "Protein pro 100 kcal", "Makroverteilung", "pro Portion**", "Schätzwerte",
                 "Plausibilitätscheck"]:
        assert teil in md, teil


def test_markdown_keine_offenen_platzhalter(echte_rezepte, db):
    for r in echte_rezepte.values():
        assert not pruefen.PLATZHALTER.search(gen.rezept_markdown(r, db))


def test_markdown_mengen_identisch_mit_zutatenliste(chicken, db):
    md = gen.rezept_markdown(chicken, db)
    portion = nw.runden(nw.rezept_naehrwerte(chicken, db)["portion"])
    assert f"| Kalorien | {nw.zahl(portion['kcal'], 0)} kcal |" in md
    assert "2 Hähnchenbrustfilets (400 g)" in md


def test_rezeptbuch_aussortiert(echte_rezepte, db):
    rezepte = [dict(r) for r in echte_rezepte.values()]
    rezepte[0]["bewertung"] = {"sterne": 2, "kommentar": "zu trocken", "datum": "2026-10-22"}
    md = gen.rezeptbuch_markdown(rezepte, db)
    assert "(aussortiert)" in md


# --- Varianten ------------------------------------------------------------------------
def test_variante_delta_und_vorzeichen(mini_db):
    d = nw.variante_delta({"Testhuhn": 100, "Testreis": -50}, mini_db)   # (100 − 175) / 2
    assert d["kcal"] == -37.5
    assert nw.vorzeichen(d["kcal"], 0, " kcal") == "−38 kcal"
    assert nw.vorzeichen(5.25, 1, " g") == "+5,3 g"
    assert nw.vorzeichen(0.04, 1, " g") == "±0 g"


def test_variante_text(mini_db):
    v = {"titel": "Mehr Huhn", "text": "100 g Testhuhn extra.", "aenderung": {"Testhuhn": 100}}
    assert gen.variante_text(v, mini_db) == "**Mehr Huhn:** 100 g Testhuhn extra. (+50 kcal, +10 g Protein, +1 g Fett pro Portion)"
    assert gen.variante_text("**Tipp:** ohne Änderung", mini_db) == "**Tipp:** ohne Änderung"


def test_variante_unbekannte_zutat(chicken, db):
    chicken["varianten"][0] = {"titel": "X", "text": "Y", "aenderung": {"Drachenfrucht": 50}}
    assert any("Variante" in f for f in fehler(chicken, db))


def test_portion_g_platzhalter(chicken, db):
    chicken["anrichten"] = "Pro Teller {portion_g}."
    assert pruefen.pruefe_rezept(chicken, db, chicken["id"]).ok
    erg = nw.rezept_naehrwerte(chicken, db)
    md = gen.rezept_markdown(chicken, db)
    assert f"Pro Teller ca. {nw.gramm(round(erg['gargewicht_portion'], -1))}." in md
