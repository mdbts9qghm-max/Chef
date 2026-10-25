"""Web-App (SPEC 10, 12.2): JSON-LD, Abschnitte, PWA, und Playwright im iPhone-Format (390 × 844)."""
import functools
import http.server
import json
import re
import threading
from pathlib import Path

import pytest
import yaml

import config
import naehrwerte as nw
import web

CHROMIUM = "/opt/pw-browsers/chromium"     # vorinstalliert, kein „playwright install“


@pytest.fixture(scope="module")
def webdir(tmp_path_factory):
    ziel = tmp_path_factory.mktemp("web")
    web.generiere_web(ziel=ziel)
    return ziel


def json_ld(pfad):
    m = re.search(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', pfad.read_text(encoding="utf-8"), re.S)
    assert m, pfad.name
    return json.loads(m.group(1))


# --- Unit ------------------------------------------------------------------------------
def test_json_ld_jeder_rezeptseite(webdir, echte_rezepte, db):
    pflicht = ["name", "recipeYield", "recipeIngredient", "recipeInstructions", "prepTime", "cookTime",
               "totalTime", "recipeCategory", "recipeCuisine", "nutrition"]
    naehr = ["calories", "proteinContent", "fatContent", "saturatedFatContent", "carbohydrateContent",
             "sugarContent", "fiberContent", "sodiumContent"]
    for rid, r in echte_rezepte.items():
        ld = json_ld(webdir / "rezept" / f"{rid}.html")
        assert ld["@type"] == "Recipe"
        for f in pflicht:
            assert ld.get(f), (rid, f)
        for f in naehr:
            assert ld["nutrition"].get(f), (rid, f)
        assert ld["recipeYield"] == "2 Portionen"
        assert all(re.match(r"^\d[\d.,]* g \S", z) for z in ld["recipeIngredient"]), rid
        assert all(s["@type"] == "HowToStep" and "{" not in s["text"] for s in ld["recipeInstructions"])
        assert re.fullmatch(r"PT(\d+H)?(\d+M)?", ld["totalTime"])
        kcal = nw.rund(nw.rezept_naehrwerte(r, db)["portion"]["kcal"])
        assert ld["nutrition"]["calories"] == f"{kcal} kcal"


def test_rezeptseiten_haben_alle_abschnitte(webdir, echte_rezepte):
    for rid in echte_rezepte:
        html = (webdir / "rezept" / f"{rid}.html").read_text(encoding="utf-8")
        titel = [t.replace("&amp;", "&") for t in re.findall(r"<h2>(.*?)</h2>", html)]
        assert titel == config.MD_ABSCHNITTE, rid
        assert "{" not in re.sub(r"<script.*?</script>", "", html, flags=re.S).split("<main>")[1].split("</main>")[0]


def test_macrofactor_text_und_hinweis(webdir):
    html = (webdir / "rezept" / "marry-me-chicken.html").read_text(encoding="utf-8")
    assert "400 g Hähnchenbrustfilet roh" in html
    assert "Fertiges Gericht wiegen und als Gesamtgewicht in MacroFactor eintragen" in html


def test_pwa_dateien(webdir):
    m = json.loads((webdir / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert m["display"] == "standalone" and m["start_url"] == "./index.html"
    for icon in m["icons"]:
        assert (webdir / icon["src"]).exists()
    assert (webdir / "icons" / "apple-touch-icon.png").exists()
    sw = (webdir / "sw.js").read_text(encoding="utf-8")
    liste = json.loads(re.search(r"const DATEIEN = (\[.*?\]);", sw, re.S).group(1))
    alle = {p.relative_to(webdir).as_posix() for p in webdir.rglob("*") if p.is_file() and p.name != "sw.js"}
    assert alle <= set(liste)


def test_veroeffentlichungs_flags(tmp_path):
    web.generiere_web(ziel=tmp_path, flags={"rezeptbuch": True, "wochenplaene": False, "einkaufslisten": False})
    assert not (tmp_path / "woche").exists() and not (tmp_path / "einkauf").exists()
    assert '"plaene": []' in (tmp_path / "assets" / "daten.js").read_text(encoding="utf-8")


# --- Playwright --------------------------------------------------------------------------
@pytest.fixture(scope="module")
def server(webdir):
    class Leise(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Leise, directory=str(webdir)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


@pytest.fixture(scope="module")
def browser():
    pw = pytest.importorskip("playwright.sync_api")
    if not Path(CHROMIUM).exists():
        pytest.fail(f"Chromium fehlt unter {CHROMIUM}")
    with pw.sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM)
        yield b
        b.close()


@pytest.fixture
def seite(browser):
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="de-DE", timezone_id="Europe/Berlin")
    pg = ctx.new_page()
    pg.fehler = []
    pg.on("pageerror", lambda e: pg.fehler.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and pg.fehler.append(m.text))
    yield pg
    ctx.close()


def test_alle_seiten_ohne_js_fehler(seite, server, webdir):
    seiten = sorted(p.relative_to(webdir).as_posix() for p in webdir.rglob("*.html"))
    assert len(seiten) >= 50
    for s in seiten:
        seite.goto(server + s)
        seite.wait_for_load_state("load")
    assert seite.fehler == []


def test_heute_zeigt_plan(seite, server):
    seite.goto(server + "index.html?datum=2026-11-05")
    assert seite.locator(".mahlzeit").count() >= 3
    plan = yaml.safe_load((config.WOCHENPLAENE_DIR / "KW-45-2026.yaml").read_text(encoding="utf-8"))
    abend = next(t["abend"]["rezept"] for t in plan["tage"] if str(t["datum"]) == "2026-11-05")
    assert nw.lade_alle_rezepte()[abend]["name"] in seite.inner_text("#heute")
    assert seite.locator(".balken").count() == 4
    seite.goto(server + "index.html?datum=2026-10-20")
    assert "nichts geplant" in seite.inner_text("#heute")


def test_rezeptbuch_suche_und_filter(seite, server, echte_rezepte):
    seite.goto(server + "rezepte.html")
    sichtbar = lambda: seite.locator(".kachel:not([hidden])").count()
    alle = len(echte_rezepte)
    assert sichtbar() == alle
    seite.fill("input[name=suche]", "lachs")
    assert 0 < sichtbar() < alle
    seite.fill("input[name=suche]", "")
    seite.select_option("select[name=mahlzeit]", "Snack")
    assert sichtbar() == sum(r["mahlzeit"] == "Snack" for r in echte_rezepte.values())


def test_portionsrechner_skaliert(seite, server):
    seite.goto(server + "rezept/marry-me-chicken.html")
    zelle = seite.locator(".m[data-art=zelle]").first
    assert zelle.inner_text() == "120 g"
    seite.click("[data-schritt='1']")
    seite.click("[data-schritt='1']")
    assert seite.inner_text("#portionen output") == "4"
    assert zelle.inner_text() == "240 g"
    assert "4 Hähnchenbrustfilets (800 g)" in seite.inner_text("main")


def test_kochmodus_schritt_1_bis_n(seite, server, echte_rezepte):
    n = len(echte_rezepte["marry-me-chicken"]["schritte"])
    seite.goto(server + "rezept/marry-me-chicken.html")
    seite.click("#kochmodus-start")
    for i in range(1, n + 1):
        assert seite.inner_text(".kochmodus .zaehler") == f"Schritt {i} von {n}"
        if i == 1:
            assert seite.locator(".kochmodus button:has-text('Timer')").count() == 1
        seite.click(".kochmodus .unten button.primaer")
    assert seite.locator(".kochmodus").count() == 0
    assert seite.fehler == []


def test_einkaufsliste_merkt_haken(seite, server):
    seite.goto(server + "einkauf/KW-45-2026.html")
    erste_liste = seite.locator(".liste").first
    erster = erste_liste.locator("li").first
    name = erster.inner_text()
    erster.locator("input").check()
    assert erste_liste.locator("li").last.inner_text() == name          # abgehakt wandert nach unten
    seite.reload()
    assert seite.locator(".liste").first.locator("li").last.locator("input").is_checked()
    seite.click("#zuruecksetzen")
    assert seite.locator(".liste input:checked").count() == 0


# --- Livegang (Phase 8) --------------------------------------------------------------------
def test_oeffentliche_adresse_in_rezeptseiten(webdir):
    basis = config.WEB_URL
    assert basis.startswith("https://") and basis.endswith("/")
    pfad = webdir / "rezept" / "marry-me-chicken.html"
    ld = json_ld(pfad)
    assert ld["url"] == f"{basis}rezept/marry-me-chicken.html"
    assert ld["image"] == f"{basis}icons/icon-512.png" and (webdir / "icons" / "icon-512.png").exists()
    html = pfad.read_text(encoding="utf-8")
    assert f'<link rel="canonical" href="{ld["url"]}">' in html
    assert f'<meta property="og:url" content="{ld["url"]}">' in html


def test_ohne_adresse_nur_relative_links(tmp_path):
    web.generiere_web(ziel=tmp_path, basis_url="")
    pfad = tmp_path / "rezept" / "marry-me-chicken.html"
    assert "url" not in json_ld(pfad) and "image" not in json_ld(pfad)
    assert "canonical" not in pfad.read_text(encoding="utf-8")


def test_pages_workflow():
    import yaml
    wf = yaml.safe_load((config.WURZEL / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8"))
    schritte = wf["jobs"]["deploy"]["steps"]
    hochladen = next(s for s in schritte if s.get("uses", "").startswith("actions/upload-pages-artifact"))
    assert hochladen["with"]["path"] == "web"
    assert any(s.get("uses", "").startswith("actions/deploy-pages") for s in schritte)
    assert wf["permissions"]["pages"] == "write" and wf["permissions"]["id-token"] == "write"
    assert wf[True]["push"]["branches"] == ["main"]          # YAML 1.1 liest „on“ als True


def test_live_pruefung_mit_lokalen_dateien(webdir):
    import veroeffentlichen as vo
    laden = lambda url: (webdir / url.removeprefix("https://x/")).read_text(encoding="utf-8")
    assert vo.live_pruefen("https://x/", laden) == []
    kaputt = lambda url: (_ for _ in ()).throw(OSError("404")) if url.endswith("sw.js") else laden(url)
    assert vo.live_pruefen("https://x/", kaputt) == ["sw.js: 404"]


def test_budget_in_der_app_aenderbar(seite, server):
    seite.goto(server + "einkauf/KW-45-2026.html")
    k = json.loads(seite.inner_text("#kostendaten"))
    gesamt = k["woche"] + k["vorrat"]
    assert seite.input_value("#budget-betrag") == str(config.PROFIL["einkauf"]["budget_eur_pro_woche"])
    seite.fill("#budget-betrag", str(int(gesamt) + 50))
    assert "Im Budget" in seite.inner_text("#budget-ergebnis")
    seite.fill("#budget-betrag", "50")
    assert "⚠️" in seite.inner_text("#budget-ergebnis") and "Sparvorschläge" in seite.inner_text("#budget-ergebnis")
    seite.reload()
    assert seite.input_value("#budget-betrag") == "50"                  # bleibt auf dem Gerät gespeichert
    seite.goto(server + "index.html?datum=2026-11-05")
    assert "Budget 50 €" in seite.inner_text("#heute")
    seite.goto(server + "einkauf/KW-45-2026.html")
    seite.click("#budget-standard")
    assert seite.input_value("#budget-betrag") == str(config.PROFIL["einkauf"]["budget_eur_pro_woche"])
    assert seite.fehler == []


def test_budget_zeigt_verbrauch(seite, server):
    seite.goto(server + "einkauf/KW-45-2026.html")
    k = json.loads(seite.inner_text("#kostendaten"))
    assert k["verbrauch"] + k["reste"] == pytest.approx(k["woche"], abs=0.02)
    assert "davon verbraucht" in seite.inner_text("#budget-ergebnis").lower()
