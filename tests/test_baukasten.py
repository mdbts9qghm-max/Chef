"""Baukasten (Woche in der App zusammenstellen), Eingang (eingang.py) und Rezept-Vorschläge."""
import datetime as dt
import re
import shutil
import urllib.parse

import pytest
import yaml

import config
import einkauf as ek
import eingang
import naehrwerte as nw
import web
import wochenplan as wp
from test_web import browser, seite  # noqa: F401  (Playwright-Fixtures wiederverwenden)

HEUTE = dt.date(2026, 10, 31)          # Sa: diese Woche = KW 44, nächste = KW 45


@pytest.fixture(scope="module")
def webdir(tmp_path_factory):
    ziel = tmp_path_factory.mktemp("web-baukasten")
    web.generiere_web(ziel=ziel, heute=HEUTE)
    return ziel


@pytest.fixture(scope="module")
def server(webdir):
    import functools
    import http.server
    import threading

    class Leise(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Leise, directory=str(webdir)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


def oeffnen(seite, server, woche, heute="2026-10-20"):  # noqa: F811
    seite.goto(f"{server}baukasten.html?woche={woche}&heute={heute}")
    seite.evaluate("localStorage.clear()")
    seite.reload()
    seite.wait_for_function("window.BAUKASTEN_API !== undefined")


def plan_aus_app(seite, name):  # noqa: F811
    plan = yaml.safe_load(seite.evaluate("BAUKASTEN_API.yaml()"))
    plan["name"] = name
    return plan


# --- Gleiche Zahlen in App und Python ------------------------------------------------------------
@pytest.mark.parametrize("name", ["KW-44-2026", "KW-45-2026"])
def test_baukasten_rechnet_wie_python(seite, server, name, echte_rezepte, db):  # noqa: F811
    oeffnen(seite, server, name)
    plan = wp.lade_plan(name)
    # Tageswerte
    for t, j in zip(plan["tage"], seite.evaluate("BAUKASTEN_API.tage()")):
        py = wp.tagessumme(t, echte_rezepte, db)
        assert all(abs(py[k] - j[k]) < 0.01 for k in ("kcal", "protein", "fett", "kh")), t["datum"]
    # Plandatei: geladener Plan wird unverändert wieder erzeugt (Struktur wie planer.plan_dict)
    app = plan_aus_app(seite, name)
    assert app["quelle"] == "baukasten" and app["kw"] == plan["kw"]
    for a, b in zip(plan["tage"], app["tage"]):
        for slot in config.SLOTS + ["auswaerts"]:
            erwartet = {k: v for k, v in (a.get(slot) or {}).items() if k != "fest"} or None
            assert erwartet == b.get(slot), (a["datum"], slot)
    # Einkaufsliste wie einkauf.berechne + einkauf.kosten
    listen, reste = ek.berechne(plan, echte_rezepte, db)
    j = seite.evaluate("BAUKASTEN_API.einkauf()")
    py = {(l.datum.isoformat(), z.zutat): z for l in listen for z in l.zeilen}
    js = {(l["datum"], z["zutat"]): z for l in j["listen"] for z in l["zeilen"]}
    assert set(py) == set(js)
    for key, z in py.items():
        x = js[key]
        assert abs(z.bedarf - x["bedarf"]) < 1e-6 and abs(z.aus_bestand - x["aus_bestand"]) < 1e-6, key
        assert z.pakete == x["pakete"] and abs(z.kosten - x["kosten"]) < 1e-6, key
        assert z.hinweis == x["hinweis"] and z.wofuer == x["wofuer"], key
    k = ek.kosten(listen)
    assert all(abs(k[x] - j["kosten"][x]) < 1e-6 for x in ("woche", "verbrauch", "reste", "vorrat"))
    assert set(reste) == set(j["reste"])
    for z, r in reste.items():
        assert abs(r["g"] - j["reste"][z]["g"]) < 1e-6 and str(r["haltbar_bis"]) == j["reste"][z]["haltbar_bis"]
    assert seite.fehler == []


# --- Bauen --------------------------------------------------------------------------------------
def test_baukasten_waehlen_doppelt_und_auffuellen(seite, server, echte_rezepte, db):  # noqa: F811
    oeffnen(seite, server, "KW-46-2026", heute=HEUTE.isoformat())
    assert seite.locator(".bk-tag").count() == 7 and seite.locator(".bk-platz").count() == 28
    # Di 10.11. Mittag vor der Tagschicht Mi → doppelt kochen ist vorausgewählt, zweite Ladung = Abend Mi
    seite.click("[data-platz='2026-11-10/mittag']")
    assert "auch Abend Mi" in seite.inner_text(".bk-doppelt")
    seite.locator(".bk-kandidat").first.click()
    a = {x["key"]: x for x in seite.evaluate("BAUKASTEN_API.ableitung()")}
    assert a["2026-11-11/abend"]["rest"] == "2026-11-10/mittag" and a["2026-11-10/mittag"]["ladungen"] == 2
    assert a["2026-11-11/abend"]["r"] == a["2026-11-10/mittag"]["r"]
    # Rest auffüllen füllt nur die leeren Plätze, die eigene Wahl bleibt
    gewaehlt = a["2026-11-10/mittag"]["r"]
    seite.click("#bk-auffuellen")
    seite.wait_for_function("document.querySelectorAll('.bk-platz.voll').length === 28")
    a = {x["key"]: x for x in seite.evaluate("BAUKASTEN_API.ableitung()")}
    assert len(a) == 28 and a["2026-11-10/mittag"]["r"] == gewaehlt
    # Tagschicht Mi: Frühstück am Vortag vorbereitet, Box
    assert a["2026-11-11/fruehstueck"]["gekocht_am"] == "2026-11-10" and a["2026-11-11/fruehstueck"]["box"]
    # Die erzeugte Woche besteht die Python-Prüfung ohne Fehler
    pr = wp.pruefe_plan(plan_aus_app(seite, "KW-46-2026"), echte_rezepte, db)
    assert pr.fehler == []
    assert len(seite.locator(".bk-status.ok").all()) >= 5
    # Entwurf bleibt nach dem Neuladen
    seite.reload()
    seite.wait_for_function("window.BAUKASTEN_API !== undefined")
    assert len(seite.evaluate("BAUKASTEN_API.ableitung()")) == 28
    assert seite.evaluate("document.documentElement.scrollWidth") <= 390
    assert seite.fehler == []


def test_baukasten_einfrieren_und_faktor(seite, server, echte_rezepte, db):  # noqa: F811
    oeffnen(seite, server, "KW-46-2026", heute=HEUTE.isoformat())
    # frisches Putenhack am Do 12.11. – 5 Tage nach dem Samstag-Einkauf → einfrieren (Fisch ist TK-Ware)
    seite.click("[data-platz='2026-11-12/abend']")
    seite.fill(".bk-suche", "Wrap-Hack")
    seite.locator(".bk-kandidat").first.click()
    a = {x["key"]: x for x in seite.evaluate("BAUKASTEN_API.ableitung()")}
    m = a["2026-11-12/abend"]
    assert m["r"] == "wrap-hack-putenhack" and m["einfrieren"]
    assert m["faktor"] == 1                                          # Tag unvollständig → noch kein Auto-Faktor
    # Faktor von Hand: ＋ → 1,25 (gilt auch für die zweite Ladung)
    seite.locator("[data-platz='2026-11-12/abend']").locator("xpath=..").locator("[data-schritt='1']").click()
    a = {x["key"]: x for x in seite.evaluate("BAUKASTEN_API.ableitung()")}
    assert a["2026-11-12/abend"]["faktor"] == 1.25
    kinder = [x for x in a.values() if x["rest"] == "2026-11-12/abend"]
    assert all(k["faktor"] == 1.25 for k in kinder)
    plan = plan_aus_app(seite, "KW-46-2026")
    assert not [f for f in wp.pruefe_plan(plan, echte_rezepte, db).fehler if "einfrieren" in f]


def test_baukasten_vergangene_tage_gesperrt_und_speichern(seite, server):  # noqa: F811
    oeffnen(seite, server, "KW-45-2026", heute="2026-11-04")
    assert seite.locator("[data-platz='2026-11-02/abend']").is_disabled()
    assert seite.locator("[data-platz='2026-11-03/mittag']").is_disabled()
    assert seite.locator("[data-platz='2026-11-04/abend']").is_enabled()
    url = seite.evaluate("BAUKASTEN_API.url()")
    teile = urllib.parse.urlparse(url)
    q = urllib.parse.parse_qs(teile.query)
    assert teile.path == f"/{config.PROFIL['github_repo']}/new/main"
    assert re.fullmatch(r"daten/baukasten/KW-45-2026-\d{8}-\d{6}\.yaml", q["filename"][0])
    assert yaml.safe_load(q["value"][0])["quelle"] == "baukasten"
    assert len(url) < 7000                                          # GitHub-Adresse bleibt kurz genug


# --- Prüfregeln ---------------------------------------------------------------------------------
def test_baukasten_plan_zielregeln_nur_hinweise(echte_rezepte, db):
    plan = wp.lade_plan("KW-45-2026")
    plan["tage"][2]["snack"] = None                                 # Tag fällt unter die Ziele
    streng = wp.pruefe_plan(plan, echte_rezepte, db)
    plan["quelle"] = "baukasten"
    weich = wp.pruefe_plan(plan, echte_rezepte, db)
    assert any("Mi 04.11." in f for f in streng.fehler)
    assert not any("Mi 04.11." in f for f in weich.fehler) and any("Mi 04.11." in w for w in weich.warnungen)
    plan["tage"][1]["mittag"]["rest_von"] = "2026-11-01/abend"      # Struktur bleibt ein Fehler
    assert wp.pruefe_plan(plan, echte_rezepte, db).fehler


# --- Eingang ------------------------------------------------------------------------------------
@pytest.fixture
def ordner(tmp_path):
    d = {n: tmp_path / n for n in ("baukasten", "wochenplaene", "vorschlaege", "rezepte")}
    for p in d.values():
        p.mkdir()
    d["vorrat"] = tmp_path / "vorrat.yaml"
    shutil.copy(config.VORRAT_YAML, d["vorrat"])
    return d


def test_eingang_uebernimmt_neueste_woche(ordner):
    text = (config.WOCHENPLAENE_DIR / "KW-45-2026.yaml").read_text(encoding="utf-8")
    alt = text.replace("kw: 45", "quelle: baukasten\nkw: 45")
    (ordner["baukasten"] / "KW-45-2026-20261030-100000.yaml").write_text(text, encoding="utf-8")
    (ordner["baukasten"] / "KW-45-2026-20261030-110000.yaml").write_text(alt, encoding="utf-8")
    (ordner["wochenplaene"] / "KW-45-2026.yaml").write_text("alt", encoding="utf-8")
    wochen, fehler = eingang.baukasten_uebernehmen(dt.date(2026, 10, 30), ordner["baukasten"], ordner["wochenplaene"],
                                                   ordner["vorrat"], ausgabe=lambda *_: None)
    assert wochen == ["KW-45-2026"] and fehler == []
    assert (ordner["wochenplaene"] / "KW-45-2026.yaml").read_text(encoding="utf-8") == alt
    assert not list(ordner["baukasten"].glob("*.yaml"))


def test_eingang_strukturfehler_bleibt_liegen(ordner):
    text = (config.WOCHENPLAENE_DIR / "KW-45-2026.yaml").read_text(encoding="utf-8")
    kaputt = text.replace("rest_von: 2026-11-02/abend", "rest_von: 2026-11-01/abend", 1)
    datei = ordner["baukasten"] / "KW-45-2026-20261030-100000.yaml"
    datei.write_text(kaputt, encoding="utf-8")
    wochen, fehler = eingang.baukasten_uebernehmen(dt.date(2026, 10, 30), ordner["baukasten"], ordner["wochenplaene"],
                                                   ordner["vorrat"], ausgabe=lambda *_: None)
    assert wochen == [] and fehler and datei.exists()


def vorschlag_datei(ordner, rid="test-vorschlag", datum="2026-10-29"):
    text = (config.REZEPTE_DIR / "marry-me-chicken.yaml").read_text(encoding="utf-8")
    text = re.sub(r"^id: .*$", f"id: {rid}", text, count=1, flags=re.M)
    text = re.sub(r"^(id: .*)$", rf"\1\nherkunft: {{art: vorschlag, quelle: https://example.org, datum: {datum}}}", text,
                  count=1, flags=re.M)
    (ordner["vorschlaege"] / f"{rid}.yaml").write_text(text, encoding="utf-8")
    return text


def test_eingang_vorschlaege(ordner):
    vorschlag_datei(ordner, "angenommen")
    vorschlag_datei(ordner, "schon-drin")
    vorschlag_datei(ordner, "alt", datum="2026-09-01")
    vorschlag_datei(ordner, "offen")
    (ordner["vorschlaege"] / "angenommen.ok").write_text("aufnehmen: angenommen\n", encoding="utf-8")
    (ordner["rezepte"] / "schon-drin.yaml").write_text("x", encoding="utf-8")
    auf = eingang.vorschlaege_aufraeumen(HEUTE, ordner["vorschlaege"], ordner["rezepte"], ausgabe=lambda *_: None)
    assert auf == ["angenommen"]
    neu = yaml.safe_load((ordner["rezepte"] / "angenommen.yaml").read_text(encoding="utf-8"))
    assert neu["herkunft"]["art"] == "neu" and neu["id"] == "angenommen"
    assert sorted(p.name for p in ordner["vorschlaege"].iterdir()) == ["offen.yaml"]


# --- Vorschläge in der App ------------------------------------------------------------------------
def test_vorschlaege_seite(tmp_path, monkeypatch, db):
    vorschlaege = tmp_path / "vorschlaege"
    vorschlaege.mkdir()
    vorschlag_datei({"vorschlaege": vorschlaege}, "test-vorschlag")
    monkeypatch.setattr(config, "VORSCHLAEGE_DIR", vorschlaege)
    ziel = tmp_path / "web"
    web.generiere_web(ziel=ziel, heute=HEUTE)
    seite_html = (ziel / "vorschlaege.html").read_text(encoding="utf-8")
    repo = config.PROFIL["github_repo"]
    assert f"https://github.com/{repo}/new/main?filename=daten/vorschlaege/test-vorschlag.ok" in seite_html
    assert f"https://github.com/{repo}/delete/main/daten/vorschlaege/test-vorschlag.yaml" in seite_html
    assert "Neue Vorschläge (1)" in (ziel / "rezepte.html").read_text(encoding="utf-8")
    rezept = (ziel / "vorschlag" / "test-vorschlag.html").read_text(encoding="utf-8")
    assert "vorschlag-banner" in rezept and 'id="loeschen"' not in rezept
    assert "test-vorschlag" not in (ziel / "assets" / "baukasten-daten.js").read_text(encoding="utf-8")


def test_vorschlaege_werden_streng_geprueft(tmp_path):
    import pruefen
    vorschlaege = tmp_path / "vorschlaege"
    vorschlaege.mkdir()
    vorschlag_datei({"vorschlaege": vorschlaege}, "test-vorschlag")
    (vorschlaege / "verlauf.yaml").write_text("vorschlaege: []\n", encoding="utf-8")
    geladen = pruefen.lade_vorschlaege(vorschlaege)
    assert list(geladen) == ["test-vorschlag"]
    assert all(e.ok for e in pruefen.pruefe_alle(geladen))


def test_pages_workflow_uebernimmt_eingang():
    wf = yaml.safe_load((config.WURZEL / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8"))
    assert wf["permissions"]["contents"] == "write"
    namen = [s.get("name", s.get("uses", "")) for s in wf["jobs"]["deploy"]["steps"]]
    i = {n: k for k, n in enumerate(namen)}
    eingang_schritt = next(k for k, n in enumerate(namen) if "Eingang" in n)
    pruefen_schritt = next(k for k, n in enumerate(namen) if "prüfen" in n)
    commit = next(k for k, n in enumerate(namen) if "committen" in n)
    upload = next(k for k, n in enumerate(namen) if "upload-pages-artifact" in n)
    assert eingang_schritt < pruefen_schritt < commit < upload and i
