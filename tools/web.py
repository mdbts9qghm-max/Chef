"""Statische Web-App (SPEC 10) aus den YAML-Daten erzeugen: web/ – nie von Hand bearbeiten.

Wird von generieren.py aufgerufen; einzeln: python3 tools/web.py
"""
import datetime as dt
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import einkauf as ek  # noqa: E402
import generieren as gen  # noqa: E402
import naehrwerte as nw  # noqa: E402
import pruefen  # noqa: E402
import wochenplan as wp  # noqa: E402

WEB = config.WURZEL / "web"
STATIC = Path(__file__).resolve().parent / "web_static"
APP_NAME = "Rezeptbuch"
esc = html.escape
zahl, gramm = nw.zahl, nw.gramm

# Symbole (immer zusammen mit Text – Farbe/Icon nie allein bedeutungstragend)
SCHICHT_ICON = {"Tag": "☀️", "Nacht": "🌙", "frei": "🏠"}
SCHICHT_NAME = {"Tag": "Tagschicht", "Nacht": "Nachtschicht", "frei": "frei"}
SLOT_ICON = {"fruehstueck": "🥣", "mittag": "🍽️", "abend": "🍲", "snack": "🍫"}
KAT_ICON = {"High Protein": "💪", "Schnelle Rezepte": "⚡", "Meal Prep": "🍱", "Kalorienarm": "🪶", "Frühstück & Snacks": "🥣"}
KAT_KLASSE = {"High Protein": "hp", "Schnelle Rezepte": "schnell", "Meal Prep": "prep", "Kalorienarm": "leicht",
              "Frühstück & Snacks": "fs"}
KUECHE_ICON = {"Deutsch": "🥨", "Italienisch": "🍝", "Asiatisch": "🥢", "Mexikanisch": "🌮", "Indisch": "🍛",
               "Griechisch & Mediterran": "🫒", "Türkisch & Orientalisch": "🧆", "Amerikanisch": "🍔",
               "International / Fusion": "🌍"}
ABT_ICON = {"Obst & Gemüse": "🥦", "Fleisch & Fisch": "🥩", "Kühlregal": "🥛", "Brot & Backwaren": "🍞",
            "Trockenwaren": "🌾", "Konserven & Saucen": "🥫", "Gewürze & Öle": "🧂", "Tiefkühl": "❄️", "Sonstiges": "📦"}
MAKRO = [("kcal", "kcal", "kcal"), ("protein", "Protein", "g"), ("fett", "Fett", "g"), ("kh", "KH", "g")]


def korridor():
    """Erlaubte Tagesspanne je Makro (SPEC 8.2) – für Ringe und Diagramme."""
    z = config.TAGESZIELE
    return {"kcal": [z["kcal"] - config.PLAN_KCAL_TOLERANZ, z["kcal"] + config.PLAN_KCAL_TOLERANZ],
            "protein": [config.PLAN_PROTEIN_MIN, None],
            "fett": [max(config.PLAN_FETT_MIN, z["fett"] - config.PLAN_FETT_TOLERANZ), z["fett"] + config.PLAN_FETT_TOLERANZ],
            "kh": [z["kh"] - config.PLAN_KH_TOLERANZ, z["kh"] + config.PLAN_KH_TOLERANZ]}


def kat_chips(kats):
    return "".join(f'<li class="chip kat-{KAT_KLASSE.get(k, "x")}"><span aria-hidden="true">{KAT_ICON.get(k, "")}</span> {esc(k)}</li>'
                   for k in kats)


def donut_svg(teile, groesse=132, dicke=18):
    """Ring aus Anteilen [(label, wert, css-var)] mit 2-px-Lücken; Beschriftung steht daneben (Legende)."""
    r = (groesse - dicke) / 2
    umfang = 2 * 3.141592653589793 * r
    summe = sum(w for _, w, _ in teile) or 1
    pos, boegen = 0.0, []
    for label, w, var in teile:
        laenge = umfang * w / summe
        sichtbar = max(laenge - 2, 0.1)
        boegen.append(f'<circle r="{r:.1f}" cx="{groesse / 2}" cy="{groesse / 2}" fill="none" stroke="var({var})" '
                      f'stroke-width="{dicke}" stroke-dasharray="{sichtbar:.1f} {umfang - sichtbar:.1f}" '
                      f'stroke-dashoffset="{-pos:.1f}" transform="rotate(-90 {groesse / 2} {groesse / 2})">'
                      f'<title>{esc(label)}: {round(100 * w / summe)} %</title></circle>')
        pos += laenge
    return (f'<svg class="donut" viewBox="0 0 {groesse} {groesse}" width="{groesse}" height="{groesse}" role="img" '
            f'aria-label="Makroverteilung">{"".join(boegen)}</svg>')


def tag_balken(summe):
    """4 Mini-Balken (Anteil am Tagesziel) mit Beschriftung."""
    z, out = config.TAGESZIELE, []
    for k, label, einheit in MAKRO:
        pz = summe[k] / z[k] * 100
        out.append(f'<div class="mini"><span class="ml">{label}</span><span class="ms"><span class="mf m-{k}" '
                   f'style="width:{min(pz, 100):.0f}%"></span></span><span class="mw">{zahl(summe[k], 0)} {einheit}</span></div>')
    return '<div class="minis">' + "".join(out) + "</div>"


def wochen_diagramm(tage, schluessel, titel, einheit):
    """Säulen pro Tag mit Ziel-Korridor (eine Achse, Werte direkt beschriftet)."""
    lo, hi = korridor()[schluessel]
    werte = [t["summe"][schluessel] for t in tage]
    oben = max(werte + [hi or lo]) * 1.08
    unten = 0 if schluessel != "kcal" else 1500
    b, h, pad = 300, 120, 18
    sp = (b - 8) / len(tage)
    y = lambda v: pad + (h - pad - 16) * (1 - (v - unten) / (oben - unten))
    teile = []
    band_oben = y(hi) if hi else pad
    teile.append(f'<rect x="4" y="{band_oben:.1f}" width="{b - 8}" height="{y(lo) - band_oben:.1f}" class="band"/>')
    for i, (t, v) in enumerate(zip(tage, werte)):
        x = 4 + i * sp + sp * 0.2
        w = sp * 0.6
        ok = v >= lo and (hi is None or v <= hi)
        tag = config.WOCHENTAGE[wp.datum(t["datum"]).weekday()]
        teile.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{w:.1f}" height="{h - 16 - y(v):.1f}" rx="4" class="saeule m-{schluessel}">'
                     f'<title>{tag}: {zahl(v, 0)} {einheit}{"" if ok else " (außerhalb)"}</title></rect>')
        teile.append(f'<text x="{x + w / 2:.1f}" y="{y(v) - 4:.1f}" class="wert">{zahl(v, 0)}{"" if ok else "!"}</text>')
        teile.append(f'<text x="{x + w / 2:.1f}" y="{h - 3}" class="achse">{tag}</text>')
    spanne = f"{zahl(lo, 0)}–{zahl(hi, 0)}" if hi else f"ab {zahl(lo, 0)}"
    return (f'<figure class="diagramm"><figcaption>{titel} pro Tag <span class="leise">· Zielbereich {spanne} {einheit} (grau)</span></figcaption>'
            f'<svg viewBox="0 0 {b} {h}" role="img" aria-label="{titel} pro Tag">{"".join(teile)}</svg></figure>')


def woche_seite(pd, md, einkauf_link, nachbarn):
    tage = pd["tage"]
    leiste = []
    for t in tage:
        d = wp.datum(t["datum"])
        extra = ("🛒" if t["einkauf"] else "") + ("🍱" if t["mealprep"] else "")
        leiste.append(f'<a class="wtag s-{t["schicht"].lower()}" href="#tag-{t["datum"]}"><span class="wt">'
                      f'{config.WOCHENTAGE[d.weekday()]}</span><span class="dz">{d.day}</span>'
                      f'<span class="ic" aria-label="{SCHICHT_NAME[t["schicht"]]}">{SCHICHT_ICON[t["schicht"]]}</span>'
                      f'<span class="ex">{extra}</span></a>')
    navi = " ".join(f'<a class="knopf" href="{href}">{text}</a>' for text, href in nachbarn)
    legende = ('<p class="legende">☀️ Tagschicht · 🌙 Nachtschicht · 🏠 frei · 🛒 Einkauf · 🍱 Meal Prep · '
               '📦 Box · ↻ Rest · ❄️ einfrieren/auftauen</p>')
    n = len(tage)
    mittel = {k: sum(t["summe"][k] for t in tage) / n for k in ("kcal", "protein", "fett", "kh")}
    kopf = (f'<div class="wochenleiste" role="navigation" aria-label="Tage">{"".join(leiste)}</div>{legende}'
            f'<div class="knopfreihe">{einkauf_link}{navi}</div>'
            f'<section class="karte"><h2>Woche im Überblick</h2>'
            f'<p class="leise">Ø pro Tag: {zahl(mittel["kcal"], 0)} kcal · {zahl(mittel["protein"], 0)} g Protein · '
            f'{zahl(mittel["fett"], 0)} g Fett · {zahl(mittel["kh"], 0)} g KH</p>'
            f'{wochen_diagramm(tage, "kcal", "Kalorien", "kcal")}{wochen_diagramm(tage, "protein", "Protein", "g")}'
            f'{wochen_diagramm(tage, "fett", "Fett", "g")}</section>')
    karten = []
    for t in tage:
        d = wp.datum(t["datum"])
        marken = []
        if t["einkauf"]:
            marken.append(f'<span class="marke">🛒 {"Starteinkauf" if t["start_einkauf"] else "Einkauf"}</span>')
        if t["mealprep"]:
            marken.append('<span class="marke">🍱 Meal Prep</span>')
        kacheln = []
        for m in t["mahlzeiten"]:
            sym = ("📦 " if m["box"] else "") + ("↻ " if m["rest"] else "") + ("❄️ " if m["einfrieren"] else "")
            fak = f' · ×{zahl(m["faktor"], 2)}' if m["faktor"] != 1 else ""
            kacheln.append(f'<a class="mkachel" href="../rezept/{m["id"]}.html"><span class="slot">{SLOT_ICON[m["slot"]]} '
                           f'{m["label"]}{" · " + m["zeit"] if m["zeit"] else ""}</span><span class="name">{esc(m["name"])}</span>'
                           f'<span class="werte">{sym}{m["kcal"]} kcal · {zahl(m["protein"], 0)} g P{fak}</span></a>')
        if t["auswaerts"]:
            kacheln.append(f'<div class="mkachel"><span class="slot">🍴 Auswärts</span><span class="name">{esc(t["auswaerts"])}</span>'
                           f'<span class="werte">Platzhalter</span></div>')
        erinn = "".join(f"<li>{esc(x)}</li>" for x in t["erinnerungen"])
        karten.append(f'<section class="karte tag s-{t["schicht"].lower()}" id="tag-{t["datum"]}">'
                      f'<div class="band"><span>{SCHICHT_ICON[t["schicht"]]} <strong>{config.WOCHENTAGE_LANG[d.weekday()]}, '
                      f'{d.strftime("%d.%m.")}</strong> · {SCHICHT_NAME[t["schicht"]]}{" " + t["schichtzeit"] if t["schichtzeit"] else ""}</span>'
                      f'{"".join(marken)}</div><div class="mkacheln">{"".join(kacheln)}</div>{tag_balken(t["summe"])}'
                      f'{f"<details><summary>Erinnerungen für morgen</summary><ul>{erinn}</ul></details>" if erinn else ""}</section>')
    details = f'<details class="karte"><summary><strong>Zeitpläne &amp; alle Details (Text)</strong></summary>{md_html(md)}</details>'
    return kopf + "".join(karten) + details


TABS = [("heute", "index.html", "🏠", "Heute"), ("rezepte", "rezepte.html", "📖", "Rezepte"),
        ("woche", None, "🗓️", "Woche"), ("einkauf", None, "🛒", "Einkauf")]


# --- Seitenrahmen -------------------------------------------------------------------
def seite(titel, inhalt, tiefe=0, aktiv="", kopf_extra="", links=None):
    p = "../" * tiefe
    links = links or {}
    tabs = []
    for key, ziel, symbol, text in TABS:
        ziel = links.get(key, ziel)
        if ziel is None:
            continue
        cur = ' aria-current="page"' if key == aktiv else ""
        tabs.append(f'<a href="{p}{ziel}"{cur}><span aria-hidden="true">{symbol}</span>{text}</a>')
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(titel)} · {APP_NAME}</title>
<meta name="theme-color" content="#2f6b4f" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#121714" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="{APP_NAME}">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="{p}manifest.webmanifest">
<link rel="icon" href="{p}icons/icon-192.png">
<link rel="apple-touch-icon" href="{p}icons/apple-touch-icon.png">
<link rel="stylesheet" href="{p}assets/app.css">
{kopf_extra}</head>
<body data-basis="{p}">
<header class="kopf"><h1>{esc(titel)}</h1></header>
<main>
{inhalt}
</main>
<footer class="fuss">{esc(config.HINWEIS_SCHAETZWERTE)} Die Pläne sind eine Empfehlung und ersetzen keine Ernährungs- oder ärztliche Beratung.</footer>
<nav class="tabs" aria-label="Hauptnavigation">{''.join(tabs)}</nav>
<script src="{p}assets/daten.js"></script>
<script src="{p}assets/app.js"></script>
</body>
</html>
"""


# --- Inline-Markdown und Platzhalter als HTML ----------------------------------------------
def inline(text):
    """Escapen, dann **fett**, *kursiv*, [Link](url) und <br>."""
    s = esc(text, quote=False).replace("&lt;br&gt;", "<br>")
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{link_web(m.group(2))}">{m.group(1)}</a>', s)
    return s


def link_web(url):
    """Links aus dem Markdown auf die Web-Seiten umbiegen."""
    m = re.search(r"rezepte/[\w-]+/([\w-]+)\.md$", url)
    if m:
        return f"../rezept/{m.group(1)}.html"
    m = re.search(r"einkaufslisten/([\w-]+)\.md$", url)
    if m:
        return f"../einkauf/{m.group(1)}.html"
    m = re.search(r"wochenplaene/([\w-]+)\.md$", url)
    if m:
        return f"../woche/{m.group(1)}.html"
    return url


def menge_span(e, art="text"):
    """Menge als <span>, den der Portionsrechner live skaliert (art: text = in Sätzen, zelle = Zutatentabelle)."""
    name = "" if art == "zelle" or not gen.name_anhaengen(e) else gen.anzeigename(e)
    text = gen.platzhalter_text(e) if art == "text" else gen.mengentext(e)
    return (f'<span class="m" data-g="{e["g"]}" data-anz="{esc(e.get("anzeige") or "")}" '
            f'data-name="{esc(name)}" data-art="{art}">{esc(text)}</span>')


def text_html(text, rezept, portion_g=None):
    """Rezepttext mit Platzhaltern → HTML mit skalierbaren Mengen."""
    idx = {e["id"]: e for e in nw.zutaten_eintraege(rezept)}
    teile, pos = [], 0
    for m in pruefen.PLATZHALTER.finditer(text):
        teile.append(inline(text[pos:m.start()]))
        if m.group(1) == "portion_g" and portion_g is not None:
            teile.append(esc(gen.portion_text(portion_g)))
        elif m.group(1) in idx:
            e = idx[m.group(1)]
            teile.append(esc(gen.anzeigename(e)) if m.group(2) else menge_span(e))
        else:
            teile.append(esc(m.group(0)))
        pos = m.end()
    teile.append(inline(text[pos:]))
    return "".join(teile)


def klartext(text, rezept):
    """Platzhalter aufgelöst, Markdown entfernt (für JSON-LD)."""
    return re.sub(r"\*\*(.+?)\*\*", r"\1", gen.ersetze_platzhalter(text, rezept))


# --- Rezeptseite ---------------------------------------------------------------------------
def iso_dauer(minuten):
    h, m = divmod(int(minuten), 60)
    return "PT" + (f"{h}H" if h else "") + (f"{m}M" if m or not h else "")


def einkaufbare_zeilen(erg):
    return [(e, w) for e, w in erg["zeilen"]
            if not e.get("nicht_mitgerechnet") and e["zutat"] not in config.NICHT_EINKAUFEN]


def json_ld(r, erg, basis_url=""):
    p = erg["portion"]
    z = r["zeit"]
    ld = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": r["name"],
        "description": f"{r['name']}: {nw.rund(p['kcal'])} kcal und {nw.rund(p['protein'], 1)} g Protein pro Portion.",
        "recipeYield": f"{config.PORTIONEN} Portionen",
        "recipeCategory": r["mahlzeit"],
        "recipeCuisine": r["kueche"],
        "keywords": ", ".join(nw.kategorien(r, p)),
        "prepTime": iso_dauer(z.get("vorbereitung", 0)),
        "cookTime": iso_dauer(z.get("kochen", 0)),
        "totalTime": iso_dauer(nw.gesamtzeit(r) + z.get("wartezeit", 0)),
        "recipeIngredient": [f"{gramm(e['g'])} {e['zutat']}" for e, _ in einkaufbare_zeilen(erg)],
        "recipeInstructions": [{"@type": "HowToStep", "name": s["titel"], "text": klartext(s["text"], r)}
                               for s in r["schritte"]],
        "nutrition": {
            "@type": "NutritionInformation",
            "servingSize": f"1 Portion ({gen.portion_text(erg['gargewicht_portion'])})",
            "calories": f"{nw.rund(p['kcal'])} kcal",
            "proteinContent": f"{nw.rund(p['protein'], 1)} g",
            "fatContent": f"{nw.rund(p['fett'], 1)} g",
            "saturatedFatContent": f"{nw.rund(p['gesaettigt'], 1)} g",
            "carbohydrateContent": f"{nw.rund(p['kh'], 1)} g",
            "sugarContent": f"{nw.rund(p['zucker'], 1)} g",
            "fiberContent": f"{nw.rund(p['ballaststoffe'], 1)} g",
            "sodiumContent": f"{nw.rund(p['salz'] * 400)} mg",     # Natrium = Salz × 0,4
        },
    }
    if basis_url:
        ld["url"] = f"{basis_url}rezept/{r['id']}.html"
        ld["image"] = f"{basis_url}icons/icon-512.png"
    return ld


def teilen_kopf(r, ld):
    """Canonical-Link und Open-Graph-Tags (nur mit öffentlicher Adresse)."""
    if "url" not in ld:
        return ""
    return (f'<link rel="canonical" href="{esc(ld["url"])}">\n'
            f'<meta property="og:type" content="article">\n'
            f'<meta property="og:title" content="{esc(r["name"])}">\n'
            f'<meta property="og:description" content="{esc(ld["description"])}">\n'
            f'<meta property="og:url" content="{esc(ld["url"])}">\n'
            f'<meta property="og:image" content="{esc(ld["image"])}">\n')


def liste_html(eintraege, r, nummeriert=False):
    tag = "ol" if nummeriert else "ul"
    return f"<{tag}>" + "".join(f"<li>{text_html(t, r)}</li>" for t in eintraege) + f"</{tag}>"


def rezept_seite(r, db, basis_url=""):
    erg = nw.rezept_naehrwerte(r, db)
    p = erg["portion"]
    kats = nw.kategorien(r, p)
    z = r["zeit"]
    ziel = config.TAGESZIELE
    sterne = (r.get("bewertung") or {}).get("sterne")
    out = []
    # 1 Kopf
    chips = kat_chips(kats)
    zeile = (f"Vorbereitung {z.get('vorbereitung', 0)} min · Kochen {z.get('kochen', 0)} min · Wartezeit "
             f"{z.get('wartezeit', 0)} min · <strong>Gesamt {nw.gesamtzeit(r) + z.get('wartezeit', 0)} min</strong>")
    kopf = [f'<ul class="chips">{chips}</ul>', "<table>",
            f"<tr><th>Bewertung</th><td>{esc(gen.sterne(r.get('bewertung')))}</td></tr>",
            f"<tr><th>Küche</th><td>{KUECHE_ICON.get(r['kueche'], '')} {esc(r['kueche'])}</td></tr>",
            f"<tr><th>Mahlzeit</th><td>{esc(r['mahlzeit'])} ({esc(r['geschmack'])})</td></tr>",
            f"<tr><th>Portionen</th><td>{config.PORTIONEN}</td></tr>",
            f"<tr><th>Schwierigkeit</th><td>{esc(r['schwierigkeit'])}</td></tr>",
            f"<tr><th>Zeit</th><td>{zeile}</td></tr>",
            f"<tr><th>Ausstattung</th><td>{esc(', '.join(r['ausstattung']) or '–')}</td></tr>"]
    if r.get("inspiration"):
        i = r["inspiration"]
        kopf.append(f"<tr><th>Inspiration</th><td>{inline(i['quelle'])}. Geändert: {inline(i['aenderungen'])}</td></tr>")
    kopf.append("</table>")
    out.append(f'<p class="leise"><strong>{zahl(p["kcal"], 0)} kcal · {zahl(p["protein"])} g Protein</strong> pro Portion · '
               f'⏱ {nw.gesamtzeit(r)} min</p>')
    out.append('<div class="knopfreihe"><button type="button" class="primaer" id="kochmodus-start">👩‍🍳 Kochmodus</button>'
               '<button type="button" id="macrofactor">📋 Für MacroFactor kopieren</button></div>')
    out.append('<section class="karte">' + "".join(kopf) + "</section>")
    # 2 Nährwerte
    zeilen = [("Kalorien", f"{zahl(p['kcal'], 0)} kcal", ziel["kcal"], p["kcal"]),
              ("Protein", f"{zahl(p['protein'])} g", ziel["protein"], p["protein"]),
              ("Fett", f"{zahl(p['fett'])} g", ziel["fett"], p["fett"]),
              ("davon gesättigt", f"{zahl(p['gesaettigt'])} g", None, None),
              ("Kohlenhydrate", f"{zahl(p['kh'])} g", ziel["kh"], p["kh"]),
              ("davon Zucker", f"{zahl(p['zucker'])} g", None, None),
              ("Ballaststoffe", f"{zahl(p['ballaststoffe'])} g", None, None),
              ("Salz", f"{zahl(p['salz'])} g", None, None)]
    tab = "".join(f"<tr><td>{a}</td><td class='zahl'>{b}</td><td class='zahl'>{gen.prozent(w, s) if s else ''}</td></tr>"
                  for a, b, s, w in zeilen)
    e_p, e_k, e_f = 4 * p["protein"], 4 * p["kh"], 9 * p["fett"]
    e_sum = e_p + e_k + e_f
    legende = "".join(f'<li><span class="punkt m-{k}"></span>{n}<strong>{gen.prozent(v, e_sum)}</strong>'
                      f'<span class="leise">{zahl(g_)} g</span></li>'
                      for k, n, v, g_ in (("protein", "Protein", e_p, p["protein"]), ("fett", "Fett", e_f, p["fett"]),
                                          ("kh", "KH", e_k, p["kh"])))
    ziele_balken = "".join(
        f'<div class="mini"><span class="ml">{n}</span><span class="ms"><span class="mf m-{k}" style="width:{min(100, w / s * 100):.0f}%">'
        f'</span></span><span class="mw">{gen.prozent(w, s)}</span></div>'
        for k, n, w, s in (("kcal", "kcal", p["kcal"], ziel["kcal"]), ("protein", "Protein", p["protein"], ziel["protein"]),
                           ("fett", "Fett", p["fett"], ziel["fett"]), ("kh", "KH", p["kh"], ziel["kh"])))
    visual = (f'<div class="makro-visual">{donut_svg([("Protein", e_p, "--p"), ("Fett", e_f, "--f"), ("KH", e_k, "--kh")])}'
              f'<div class="donut-mitte"><strong>{zahl(p["kcal"], 0)}</strong><span>kcal</span></div>'
              f'<ul class="legende-liste">{legende}</ul></div>'
              f'<span class="plakette">💪 {zahl(p["protein"] / p["kcal"] * 100)} g Protein pro 100 kcal</span>'
              f'<h3>Anteil am Tagesziel</h3><div class="minis">{ziele_balken}</div>')
    out.append(f"""<section class="karte"><h2>Nährwerte pro Portion</h2>{visual}
<div class="tabelle"><table><tr><th>Nährwert</th><th class="zahl">pro Portion</th><th class="zahl">Tagesziel</th></tr>{tab}</table></div>
<p class="leise">Protein pro 100 kcal: {zahl(p['protein'] / p['kcal'] * 100)} g · Makroverteilung: Protein {gen.prozent(e_p, e_sum)} ·
KH {gen.prozent(e_k, e_sum)} · Fett {gen.prozent(e_f, e_sum)}</p>
<p class="hinweis">⚖️ Fertiges Gericht wiegen und als Gesamtgewicht in MacroFactor eintragen, dann kannst du nach Gramm loggen.
Orientierung: {esc(gen.portion_text(erg['gargewicht_gesamt']))} gesamt, <strong>{esc(gen.portion_text(erg['gargewicht_portion']))} pro Portion</strong>
({'gemessen' if erg['gargewicht_gemessen'] else 'geschätzt'}).</p></section>""")
    # 3 Zutaten mit Portionsrechner
    zeilen_z = []
    for e in r["zutaten"]:
        if "gruppe" in e:
            zeilen_z.append(f'<tr class="gruppe"><td colspan="3">{esc(e["gruppe"])}</td></tr>')
            continue
        hinweis = e.get("hinweis") or ""
        if e.get("nicht_mitgerechnet"):
            hinweis = (hinweis + "; " if hinweis else "") + "nicht mitgerechnet"
        zeilen_z.append(f"<tr><td>{esc(gen.anzeigename(e))}</td><td>{menge_span(e, 'zelle')}</td><td class='leise'>{esc(hinweis)}</td></tr>")
    out.append(f"""<section class="karte"><h2>Zutaten (für {config.PORTIONEN} Portionen)</h2>
<div class="portionen" id="portionen" data-basis="{config.PORTIONEN}"><span>Portionen:</span>
<button type="button" data-schritt="-1" aria-label="Eine Portion weniger">−</button><output aria-live="polite">{config.PORTIONEN}</output>
<button type="button" data-schritt="1" aria-label="Eine Portion mehr">+</button></div>
<p class="leise" id="faktor-hinweis" hidden>Mengen sind umgerechnet; Nährwerte pro Portion bleiben gleich.</p>
<div class="tabelle"><table><tr><th>Zutat</th><th>Menge</th><th>Hinweis</th></tr>{''.join(zeilen_z)}</table></div></section>""")
    # 4–11
    eigen = gen.ist_eigen(r)
    leer = lambda feld: eigen and not r.get(feld)          # eigene Rezepte: leere Abschnitte weglassen
    if eigen:
        out.insert(0, f'<p class="hinweis">✍️ {esc(gen.HINWEIS_EIGEN)}</p>')
    if not leer("mise_en_place"):
        out.append(f'<section class="karte"><h2>Mise en place</h2>{liste_html(r["mise_en_place"], r)}</section>')
    schritte = "".join(f"<li><strong>{esc(s['titel'])}</strong>{' ⏱ ' + str(s['timer_min']) + ' min' if s.get('timer_min') else ''}: "
                       f"{text_html(s['text'], r)}</li>" for s in r["schritte"])
    out.append(f'<section class="karte"><h2>Zubereitung</h2><ol class="schritte">{schritte}</ol></section>')
    if not leer("zeitablauf"):
        out.append(f'<section class="karte"><h2>Zeitablauf</h2>'
                   f'{liste_html(r.get("zeitablauf") or ["Keine parallelen Arbeitsschritte nötig."], r)}</section>')
    if not leer("fehler"):
        out.append(f'<section class="karte"><h2>Häufige Fehler</h2>{liste_html(r["fehler"], r)}</section>')
    if not leer("anrichten"):
        out.append(f'<section class="karte"><h2>Anrichten</h2><p>{text_html(r["anrichten"], r, erg["gargewicht_portion"])}</p></section>')
    a = r["aufbewahrung"]
    tage = a.get("kuehlschrank_tage") or 0
    auf = [f"<li><strong>Kühlschrank:</strong> {f'{tage} Tage' if tage else 'nicht geeignet, frisch essen'}</li>",
           f"<li><strong>Einfrieren:</strong> {'ja, bis ' + str(a.get('einfrieren_monate', '?')) + ' Monat(e)' if a.get('einfrierbar') else 'nein'}</li>",
           f"<li><strong>Aufwärmen:</strong> {inline(a['aufwaermen'])}</li>"]
    if a.get("separat"):
        auf.append(f"<li><strong>Separat lagern:</strong> {inline(a['separat'])}</li>")
    out.append(f'<section class="karte"><h2>Meal Prep &amp; Aufbewahrung</h2><ul>{"".join(auf)}</ul></section>')
    var = "".join(f"<li>{inline(gen.variante_text(v, db))}</li>" for v in r["varianten"])
    if not leer("varianten"):
        out.append(f'<section class="karte"><h2>Varianten &amp; Austausch</h2><ul>{var}</ul></section>')
    if not leer("tipps"):
        out.append(f'<section class="karte"><h2>Tipps</h2>{liste_html(r["tipps"], r)}</section>')
    # 12 Berechnung
    ber = []
    for e, w in erg["zeilen"]:
        if e.get("nicht_mitgerechnet"):
            ber.append(f"<tr><td>{esc(e['zutat'])}</td><td class='zahl'>{gramm(e['g'])}</td><td colspan='4' class='leise'>nicht mitgerechnet</td></tr>")
        else:
            ber.append(f"<tr><td>{esc(e['zutat'])}</td><td class='zahl'>{gramm(e['g'])}</td><td class='zahl'>{zahl(w['kcal'], 0)}</td>"
                       f"<td class='zahl'>{zahl(w['protein'])}</td><td class='zahl'>{zahl(w['fett'])}</td><td class='zahl'>{zahl(w['kh'])}</td></tr>")
    g = erg["gesamt"]
    pl = nw.plausibilitaet_rezept(r, db, g)
    out.append(f"""<section class="karte"><h2>Nährwert-Berechnung</h2><div class="tabelle"><table>
<tr><th>Zutat</th><th class="zahl">Menge</th><th class="zahl">kcal</th><th class="zahl">P</th><th class="zahl">F</th><th class="zahl">KH</th></tr>
{''.join(ber)}
<tr><td><strong>Summe</strong></td><td></td><td class="zahl"><strong>{zahl(g['kcal'], 0)}</strong></td><td class="zahl">{zahl(g['protein'])}</td>
<td class="zahl">{zahl(g['fett'])}</td><td class="zahl">{zahl(g['kh'])}</td></tr>
<tr><td><strong>Pro Portion</strong></td><td></td><td class="zahl"><strong>{zahl(p['kcal'], 0)}</strong></td><td class="zahl">{zahl(p['protein'])}</td>
<td class="zahl">{zahl(p['fett'])}</td><td class="zahl">{zahl(p['kh'])}</td></tr></table></div>
<p class="leise">Plausibilitätscheck: 4 × P + 4 × KH + 9 × F + 2 × Ballaststoffe = {zahl(pl['berechnet'], 0)} kcal gegenüber
{zahl(g['kcal'], 0)} kcal → {zahl(pl['prozent'])} % ({'bestanden' if pl['ok'] else 'NICHT bestanden'}). Schätzwerte.</p></section>""")
    # Kochmodus-Daten und MacroFactor-Text
    idx = {e["id"]: e for e in nw.zutaten_eintraege(r)}
    koch = []
    for s in r["schritte"]:
        ids = list(dict.fromkeys(m.group(1) for m in pruefen.PLATZHALTER.finditer(s["text"]) if m.group(1) in idx))
        koch.append({"titel": s["titel"], "html": text_html(s["text"], r), "timer": s.get("timer_min"),
                     "zutaten": [menge_span(idx[i]) for i in ids]})
    mf = "\n".join(f"{gramm(e['g'])} {e['zutat']}" for e, _ in einkaufbare_zeilen(erg))
    out.append(f'<script type="application/json" id="kochdaten">{json.dumps(koch, ensure_ascii=False).replace("</", "<\\/")}</script>')
    out.append(f'<pre id="macrofactor-text" hidden>{esc(mf)}</pre>')
    daten = json_ld(r, erg, basis_url)
    ld = json.dumps(daten, ensure_ascii=False, indent=1).replace("</", "<\\/")
    kopf_extra = teilen_kopf(r, daten) + f'<script type="application/ld+json">\n{ld}\n</script>\n'
    if sterne is not None and sterne <= 2:
        out.insert(0, '<p class="hinweis">Dieses Rezept ist aussortiert (1–2 Sterne) und wird nicht mehr geplant.</p>')
    if config.PROFIL.get("github_repo"):
        out.append(f'<div class="knopfreihe"><button type="button" class="gefahr" id="loeschen" data-id="{r["id"]}" '
                   f'data-name="{esc(r["name"])}">🗑 Rezept löschen</button></div>')
    return r["name"], "\n".join(out), kopf_extra


# --- Rezeptbuch ---------------------------------------------------------------------------
def makro_streifen(p):
    """Gestapelter Balken: Anteil der kcal aus Protein / Fett / KH, mit Beschriftung."""
    e = {"protein": 4 * p["protein"], "fett": 9 * p["fett"], "kh": 4 * p["kh"]}
    s = sum(e.values()) or 1
    teile = "".join(f'<span class="m-{k}" style="width:{100 * v / s:.1f}%" title="{n} {round(100 * v / s)} %"></span>'
                    for (k, v), n in zip(e.items(), ("Protein", "Fett", "KH")))
    text = f'P {round(100 * e["protein"] / s)} % · F {round(100 * e["fett"] / s)} % · KH {round(100 * e["kh"] / s)} %'
    return f'<div class="streifen" role="img" aria-label="Makroverteilung {text}">{teile}</div><div class="streifen-text">{text}</div>'


def zutaten_json(db):
    """Nährwerte je 100 g für das Rezept-Formular: [Name, kcal, P, F, KH, Zucker, Ballaststoffe, Typ]."""
    return [[n, w["kcal"], w["protein"], w["fett"], w["kh"], w["zucker"], w["ballaststoffe"], w.get("typ") or ""]
            for n, w in sorted(db.items()) if n not in config.NICHT_EINKAUFEN]


def rezept_neu_seite(db):
    """Formular für eigene Rezepte; app.js rechnet live und erzeugt die YAML für GitHub."""
    opt = lambda werte, gewaehlt=None: "".join(f'<option value="{esc(w)}"{" selected" if w == gewaehlt else ""}>{esc(w)}</option>'
                                             for w in werte)
    namen = "".join(f'<option value="{esc(n)}">' for n, *_ in zutaten_json(db))
    return f"""<p class="leise">Zutaten kommen aus deiner Zutatenliste, die Nährwerte rechnet die App sofort mit.
„Auf GitHub speichern“ öffnet GitHub mit der fertigen Rezeptdatei – dort nur noch <strong>„Commit changes“</strong> tippen.
Nach 1–2 Minuten ist das Rezept in der App und steht dem Planer zur Verfügung.</p>
<form id="rezept-form" class="formular" autocomplete="off">
<section class="karte"><h2>Grunddaten</h2>
<label>Name <input type="text" name="name" required maxlength="80" placeholder="z. B. Hähnchen-Reis-Pfanne"></label>
<div class="zwei"><label>Mahlzeit <select name="mahlzeit">{opt(config.MAHLZEITEN, "Mittag/Abend")}</select></label>
<label>Geschmack <select name="geschmack">{opt(config.GESCHMACK, "herzhaft")}</select></label></div>
<div class="zwei"><label>Küche <select name="kueche">{opt(config.KUECHEN, "International / Fusion")}</select></label>
<label>Schwierigkeit <select name="schwierigkeit">{opt(config.SCHWIERIGKEIT, "leicht")}</select></label></div>
<div class="drei"><label>Vorbereitung (min) <input type="number" name="vorbereitung" min="0" value="10" inputmode="numeric"></label>
<label>Kochen (min) <input type="number" name="kochen" min="0" value="20" inputmode="numeric"></label>
<label>Wartezeit (min) <input type="number" name="wartezeit" min="0" value="0" inputmode="numeric"></label></div>
<div class="zwei"><label>Haltbar im Kühlschrank (Tage) <input type="number" name="tage" min="0" max="4" value="2" inputmode="numeric"></label>
<label class="haken"><input type="checkbox" name="einfrierbar"> einfrierbar</label></div></section>
<section class="karte"><h2>Zutaten <span class="leise">(Gramm für {config.PORTIONEN} Portionen)</span></h2>
<datalist id="zutaten-liste">{namen}</datalist>
<ul id="zutaten-zeilen" class="zzeilen"></ul>
<button type="button" id="zutat-plus">＋ Zutat</button>
<p class="leise">Zutat fehlt in der Liste? In Claude „Neue Zutat: …“ schreiben – dafür braucht es Nährwerte.</p></section>
<section class="karte"><h2>Zubereitung</h2>
<label>Schritte <span class="leise">(ein Schritt pro Zeile)</span><textarea name="schritte" rows="6"
placeholder="Reis kochen.&#10;Hähnchen würfeln und in Öl auf Stufe 7 von 9 braten (74 °C Kerntemperatur).&#10;…"></textarea></label>
<label>Tipps <span class="leise">(optional, einer pro Zeile)</span><textarea name="tipps" rows="2"></textarea></label></section>
<section class="karte sticky-werte"><h2>Nährwerte pro Portion</h2><div id="rezept-werte" aria-live="polite"></div>
<ul id="rezept-probleme" class="probleme"></ul>
<div class="knopfreihe"><button type="button" class="primaer" id="rezept-speichern" disabled>💾 Auf GitHub speichern</button>
<button type="button" id="rezept-verwerfen">Entwurf verwerfen</button></div>
<details><summary>Vorschau der Rezeptdatei</summary><pre id="rezept-yaml"></pre></details></section>
</form>"""


def rezeptbuch_seite(rezepte, db):
    karten = []
    for r in sorted(rezepte.values(), key=lambda r: r["name"]):
        p = nw.rezept_naehrwerte(r, db)["portion"]
        kats = nw.kategorien(r, p)
        sterne = (r.get("bewertung") or {}).get("sterne")
        suche = " ".join([r["name"], r["kueche"]] + [z["zutat"] for z in nw.zutaten_eintraege(r)]).lower()
        klasse = " aussortiert" if sterne is not None and sterne <= 2 else ""
        bew = gen.sterne(r.get("bewertung")) if sterne else "neu"
        karten.append(
            f'<li class="kachel{klasse}" data-name="{esc(r["name"])}" data-kcal="{nw.rund(p["kcal"])}" '
            f'data-protein="{nw.rund(p["protein"], 1)}" data-zeit="{nw.gesamtzeit(r)}" data-kueche="{esc(r["kueche"])}" '
            f'data-mahlzeit="{esc(r["mahlzeit"])}" data-sterne="{sterne or ""}" data-kategorien="{esc("|".join(kats))}" '
            f'data-suche="{esc(suche)}"><a class="kachel-link" href="rezept/{r["id"]}.html" style="text-decoration:none;color:inherit;display:block">'
            f'<h3>{esc(r["name"])}</h3><div class="zahlen"><span>{zahl(p["kcal"], 0)} kcal</span><span>{zahl(p["protein"], 0)} g Protein</span>'
            f'<span>⏱ {nw.gesamtzeit(r)} min</span><span>{esc(bew)}</span></div>'
            f'{makro_streifen(p)}'
            f'<ul class="chips"><li class="chip grau">{esc(r["mahlzeit"])}</li><li class="chip grau">'
            f'<span aria-hidden="true">{KUECHE_ICON.get(r["kueche"], "")}</span> {esc(r["kueche"])}</li>'
            + kat_chips([k for k in kats if k != "Frühstück & Snacks"])
            + ('<li class="chip grau">✍️ eigenes</li>' if gen.ist_eigen(r) else "") + "</ul></a></li>")
    opt = lambda werte: "".join(f'<option value="{esc(w)}">{esc(t)}</option>' for w, t in werte)
    kuechen = sorted({r["kueche"] for r in rezepte.values()})
    neu_knopf = ('<div class="knopfreihe"><a class="knopf primaer" href="rezept-neu.html">＋ Eigenes Rezept</a></div>'
                 if config.PROFIL.get("github_repo") else "")
    inhalt = neu_knopf + f"""<form id="filter" class="filter" role="search">
<input type="search" name="suche" placeholder="Suchen: Name oder Zutat" aria-label="Rezepte durchsuchen">
<select name="kategorie" aria-label="Kategorie">{opt([("", "Alle Kategorien")] + [(k, k) for k in config.KATEGORIE_REIHENFOLGE])}</select>
<select name="kueche" aria-label="Küche">{opt([("", "Alle Küchen")] + [(k, k) for k in kuechen])}</select>
<select name="mahlzeit" aria-label="Mahlzeit">{opt([("", "Alle Mahlzeiten")] + [(m, m) for m in config.MAHLZEITEN])}</select>
<select name="bewertung" aria-label="Bewertung">{opt([("", "Alle Bewertungen"), ("4", "ab 4 Sternen"), ("3", "ab 3 Sternen"), ("neu", "noch nicht bewertet")])}</select>
<select name="zeit" aria-label="Maximale Zeit">{opt([("", "Beliebige Zeit"), ("15", "bis 15 min"), ("25", "bis 25 min"), ("45", "bis 45 min"), ("60", "bis 60 min")])}</select>
<select name="sortierung" aria-label="Sortierung">{opt([("name", "Sortieren: Name"), ("kcal", "Sortieren: kcal ↑"), ("protein", "Sortieren: Protein ↓"), ("zeit", "Sortieren: Zeit ↑")])}</select>
</form>
<p class="leise" id="treffer" aria-live="polite">{len(karten)} Rezepte</p>
<ul class="kacheln" id="kacheln">{''.join(karten)}</ul>"""
    return inhalt


# --- Markdown → HTML (für Wochenplan und Teile der Einkaufsliste) -----------------------------
def md_html(md, karten=True):
    """Kleiner Konverter für das von wochenplan.py/einkauf.py erzeugte Markdown."""
    out, liste, tabelle, offen = [], None, [], False

    def schliesse_liste():
        nonlocal liste
        if liste:
            out.append(f"</{liste}>")
            liste = None

    def schliesse_tabelle():
        if not tabelle:
            return
        zeilen = [t for t in tabelle if not re.fullmatch(r"\|[\s:|-]+\|", t)]
        html_z = []
        for n, z in enumerate(zeilen):
            zellen = [c.strip() for c in z.strip("|").split("|")]
            tag = "th" if n == 0 else "td"
            html_z.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in zellen) + "</tr>")
        out.append('<div class="tabelle"><table>' + "".join(html_z) + "</table></div>")
        tabelle.clear()

    for zeile in md.splitlines():
        if zeile.startswith("<!--"):
            continue
        if zeile.startswith("|"):
            schliesse_liste()
            tabelle.append(zeile)
            continue
        schliesse_tabelle()
        if zeile.startswith("# "):
            continue                                  # Titel steht im Seitenkopf
        if zeile.startswith("## "):
            schliesse_liste()
            if karten and offen:
                out.append("</section>")
            if karten:
                out.append('<section class="karte tag">')
                offen = True
            out.append(f"<h2>{inline(zeile[3:])}</h2>")
        elif zeile.startswith("### "):
            schliesse_liste()
            out.append(f"<h3>{inline(zeile[4:])}</h3>")
        elif re.match(r"^\s*- \[ \] ", zeile):
            if liste != "ul":
                schliesse_liste(); out.append("<ul>"); liste = "ul"
            out.append(f"<li>☐ {inline(zeile.split('- [ ] ', 1)[1])}</li>")
        elif re.match(r"^- ", zeile):
            if liste != "ul":
                schliesse_liste(); out.append("<ul>"); liste = "ul"
            out.append(f"<li>{inline(zeile[2:])}</li>")
        elif re.match(r"^\d+\. ", zeile):
            if liste != "ol":
                schliesse_liste(); out.append("<ol>"); liste = "ol"
            out.append(f"<li>{inline(zeile.split('. ', 1)[1])}</li>")
        elif zeile.startswith(">"):
            schliesse_liste()
            out.append(f"<blockquote>{inline(zeile.lstrip('> ').lstrip('- '))}</blockquote>")
        elif zeile.strip():
            schliesse_liste()
            out.append(f"<p>{inline(zeile)}</p>")
        else:
            schliesse_liste()
    schliesse_liste()
    schliesse_tabelle()
    if karten and offen:
        out.append("</section>")
    return "\n".join(out)


# --- Pläne ---------------------------------------------------------------------------------
def lade_plaene():
    plaene = [wp.lade_plan(p) for p in sorted(config.WOCHENPLAENE_DIR.glob("KW-*.yaml"))]
    return sorted(plaene, key=lambda p: (p["jahr"], p["kw"]))


def plan_daten(plan, rezepte, db, pruefung):
    """Kompakte Plandaten für die Heute-Ansicht."""
    alle = {(e.datum.isoformat(), e.slot): e for e in wp.eintraege(plan)}
    einkauf_tage = {wp.datum(x["datum"]): x.get("art") for x in plan.get("einkauf", [])}
    tage = []
    for i, tag in enumerate(plan["tage"]):
        d = wp.datum(tag["datum"])
        s = wp.schicht(d, plan.get("schichten"))
        zeiten = config.ESSENSZEITEN.get(s, {})
        box_slots = (config.SCHICHTEN.get("boxen") or {}).get(s, [])
        mahl = []
        for slot in config.SLOTS:
            e = tag.get(slot)
            if not e:
                continue
            r = rezepte[e["rezept"]]
            w = wp.portion(e["rezept"], float(e.get("faktor", 1.0)), rezepte, db)
            eintrag = alle[(d.isoformat(), slot)]
            mahl.append({"slot": slot, "label": config.SLOT_NAMEN[slot], "id": r["id"], "name": r["name"],
                         "kcal": round(w["kcal"]), "protein": round(w["protein"], 1), "kochen": eintrag.kochen and eintrag.gekocht_am == d,
                         "rest": bool(e.get("rest_von")), "box": bool(e.get("box")) or slot in box_slots, "zeit": zeiten.get(slot, ""),
                         "einfrieren": bool(e.get("einfrieren")), "vorbereiten": bool(e.get("gekocht_am")),
                         "faktor": float(e.get("faktor", 1.0))})
        extras = [{"text": x.get("text") or x["zutat"], "kcal": round(wp.extra_werte(x, db)["kcal"]),
                   "protein": round(wp.extra_werte(x, db)["protein"], 1)} for x in tag.get("extras") or []]
        summe = wp.tagessumme(tag, rezepte, db)
        aus = tag.get("auswaerts")
        morgen = d + dt.timedelta(1)
        tage.append({"datum": d.isoformat(), "schicht": s, "schichtzeit": (config.SCHICHTEN.get("zeiten") or {}).get(s, ""),
                     "einkauf": d in einkauf_tage, "start_einkauf": d in einkauf_tage and einkauf_tage[d] == "start",
                     "mealprep": s == "frei" and wp.schicht(morgen, plan.get("schichten")) == "Tag",
                     "mahlzeiten": mahl, "extras": extras, "auswaerts": f"{config.SLOT_NAMEN.get(aus['mahlzeit'], '')} auswärts" if aus else None,
                     "summe": {k: round(summe[k], 1) for k in ("kcal", "protein", "fett", "kh")},
                     "erinnerungen": wp.erinnerungen_morgen(plan, i, rezepte, pruefung)})
    return {"name": plan["name"], "kw": plan["kw"], "jahr": plan["jahr"], "tage": tage}


def einkauf_seite(plan, rezepte, db):
    listen, reste = ek.berechne(plan, rezepte, db)
    reihenfolge = config.PROFIL["einkauf"]["abteilungen"]
    out = [f'<div id="einkauf" data-plan="{esc(plan["name"])}">',
           f'<p class="leise">Für den <a href="../woche/{plan["name"]}.html">Wochenplan KW {plan["kw"]}</a>. '
           'Haken werden auf diesem Gerät gespeichert.</p>',
           '<div class="knopfreihe"><button type="button" id="zuruecksetzen">↺ Alle Haken zurücksetzen</button></div>']
    for liste in listen:
        out.append(f'<section class="karte"><h2>🛒 Einkauf {config.WOCHENTAGE_LANG[liste.datum.weekday()]}, '
                   f'{liste.datum.strftime("%d.%m.%Y")}{esc(ek.start_hinweis(plan, liste.datum))}</h2>')
        kaufen = [z for z in liste.zeilen if z.pakete > 0]
        for abt in reihenfolge + sorted({ek.abteilung(z) for z in kaufen} - set(reihenfolge)):
            teil = sorted((z for z in kaufen if ek.abteilung(z) == abt), key=lambda z: z.zutat)
            if not teil:
                continue
            out.append(f'<h3><span aria-hidden="true">{ABT_ICON.get(abt, "📦")}</span> {esc(abt)}</h3><ul class="liste">')
            for z in teil:
                pk = z.packung
                menge = pk["packung_text"] if z.pakete == 1 else f"{z.pakete} × {pk['packung_text']}"
                preis = f" · ca. {zahl(z.kosten, 2)} €" if pk.get("preis") is not None else ""
                da = f" (davon {gramm(z.aus_bestand)} schon da)" if z.aus_bestand > ek.EPS else ""
                hinweis = f'<div class="detail warn">⚠️ {esc(z.hinweis)}</div>' if z.hinweis else ""
                key = esc(f"{liste.datum.isoformat()}|{z.zutat}")
                out.append(f'<li><label><input type="checkbox" data-key="{key}"><span><span class="titel"><strong>{esc(z.zutat)}</strong> · '
                           f'{esc(menge)}{preis}</span><div class="detail">Bedarf {gramm(z.bedarf)}{da} · {esc("; ".join(z.wofuer))}</div>'
                           f'{hinweis}</span></label></li>')
            out.append("</ul>")
        pruefen_z = [z for z in liste.zeilen if z.pakete == 0 and (z.vorrat_unbekannt or z.packung is None)]
        schon = [z for z in liste.zeilen if z.pakete == 0 and z not in pruefen_z]
        if pruefen_z:
            out.append('<h3>Vorrat prüfen</h3><ul class="liste">')
            for z in sorted(pruefen_z, key=lambda z: z.zutat):
                key = esc(f"{liste.datum.isoformat()}|vorrat|{z.zutat}")
                out.append(f'<li><label><input type="checkbox" data-key="{key}"><span><span class="titel">{esc(z.zutat)}: '
                           f'{gramm(z.bedarf)}</span><div class="detail">{esc("; ".join(z.wofuer))}</div></span></label></li>')
            out.append("</ul>")
        if schon:
            out.append("<h3>Schon da (Reste aus dem vorherigen Einkauf)</h3><p class='leise'>"
                       + esc(", ".join(f"{z.zutat} {gramm(z.bedarf)}" for z in sorted(schon, key=lambda z: z.zutat))) + "</p>")
        out.append("</section>")
    out.append(kosten_balken(listen))
    out.append(budget_html(ek.kosten(listen)))
    md = ek.einkauf_markdown(plan, rezepte, db, listen, reste)
    if "## Reste" in md:
        out.append(md_html(md[md.index("## Reste"):]))
    out.append("</div>")
    return "\n".join(out)


def kosten_balken(listen):
    """Kosten je Abteilung (Wochenbedarf, ohne Vorratskäufe) als beschriftete horizontale Balken."""
    abt = {}
    for l in listen:
        for z in l.zeilen:
            if z.pakete and not z.vorratskauf:
                abt[ek.abteilung(z)] = abt.get(ek.abteilung(z), 0.0) + z.kosten
    if not abt:
        return ""
    groesster = max(abt.values())
    zeilen = "".join(f'<div class="kbalken"><span class="kl">{ABT_ICON.get(a, "📦")} {esc(a)}</span><span class="ks">'
                     f'<span style="width:{100 * v / groesster:.0f}%"></span></span><span class="kw">{zahl(v, 2)} €</span></div>'
                     for a, v in sorted(abt.items(), key=lambda x: -x[1]))
    return f'<section class="karte"><h2>Wofür das Geld ausgegeben wird</h2>{zeilen}</section>'


def budget_html(k):
    """Budget-Karte: Betrag ist in der App änderbar (app.js rechnet mit den Kostendaten live)."""
    daten = json.dumps({"woche": round(k["woche"], 2), "vorrat": round(k["vorrat"], 2),
                        "verbrauch": round(k["verbrauch"], 2), "reste": round(k["reste"], 2),
                        "teuer": [{"zutat": t["zutat"], "kosten": round(t["kosten"], 2)} for t in k["teuer"]],
                        "spar_whey": ek.SPAR_WHEY}, ensure_ascii=False).replace("</", "<\\/")
    standard = ek.budget() or 0
    return f"""<section class="karte" id="budget" data-standard="{standard}">
<h2>Budget</h2>
<div class="budget-eingabe"><label for="budget-betrag">€ pro Woche</label>
<input type="number" id="budget-betrag" min="0" step="5" inputmode="decimal" value="{standard}">
<button type="button" id="budget-standard">Standard ({zahl(standard, 0)} €)</button></div>
<div id="budget-ergebnis" aria-live="polite"></div>
<p class="leise">Gilt auf diesem Gerät für alle Wochen. Damit auch die Planung danach rechnet, in Claude „Budget: [€]“ sagen.</p>
<script type="application/json" id="kostendaten">{daten}</script>
</section>"""


# --- PWA -----------------------------------------------------------------------------------
def manifest():
    return {"name": APP_NAME, "short_name": "Rezepte", "lang": "de", "start_url": "./index.html", "scope": "./",
            "display": "standalone", "background_color": "#f6f4ef", "theme_color": "#2f6b4f",
            "description": "Persönliches High-Protein-Rezeptbuch mit Wochenplan und Einkaufsliste",
            "icons": [{"src": "icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
                      {"src": "icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}


SW_VORLAGE = """// Service Worker – generiert, nicht von Hand bearbeiten
const VERSION = "rezeptbuch-%(version)s";
const DATEIEN = %(dateien)s;
self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(DATEIEN)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(caches.match(e.request, { ignoreSearch: true })
    .then((r) => r || fetch(e.request).catch(() => caches.match("index.html"))));
});
"""


def precache_liste(wurzel=WEB):
    return sorted(p.relative_to(wurzel).as_posix() for p in wurzel.rglob("*") if p.is_file() and p.name != "sw.js")


# --- Alles erzeugen ----------------------------------------------------------------------------
def schreibe(pfad, text):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(text, encoding="utf-8")


def generiere_web(rezepte=None, db=None, ziel=WEB, flags=None, basis_url=None):
    db = db or nw.lade_zutaten()
    rezepte = rezepte if rezepte is not None else nw.lade_alle_rezepte()
    flags = flags or config.PROFIL.get("veroeffentlichen", {})
    basis_url = config.WEB_URL if basis_url is None else basis_url
    if ziel.exists():
        shutil.rmtree(ziel)
    ziel.mkdir(parents=True)
    shutil.copytree(STATIC / "icons", ziel / "icons")
    (ziel / "assets").mkdir()
    shutil.copy(STATIC / "app.css", ziel / "assets" / "app.css")
    shutil.copy(STATIC / "app.js", ziel / "assets" / "app.js")

    plaene = lade_plaene() if flags.get("wochenplaene", True) else []
    links = {}
    if plaene:
        links["woche"] = f"woche/{plaene[-1]['name']}.html"
        if flags.get("einkaufslisten", True):
            links["einkauf"] = f"einkauf/{plaene[-1]['name']}.html"
    rel = lambda tiefe: {k: v for k, v in links.items()}

    plan_json = []
    for i, plan in enumerate(plaene):
        pr = wp.pruefe_plan(plan, rezepte, db)
        pd = plan_daten(plan, rezepte, db, pr)
        plan_json.append(pd)
        md = wp.wochenplan_markdown(plan, rezepte, db, pr)
        # Web: Tage als Karten – die breite Übersichtstabelle passt nicht aufs iPhone
        md = re.sub(r"## Übersicht\n.*?(?=\n## )", "", md, count=1, flags=re.S)
        einkauf_link = (f'<a class="knopf primaer" href="../einkauf/{plan["name"]}.html">🛒 Einkaufsliste</a>'
                        if flags.get("einkaufslisten", True) else "")
        nachbarn = ([(f"← KW {plaene[i - 1]['kw']}", f"{plaene[i - 1]['name']}.html")] if i else []) + \
                   ([(f"KW {plaene[i + 1]['kw']} →", f"{plaene[i + 1]['name']}.html")] if i + 1 < len(plaene) else [])
        schreibe(ziel / "woche" / f"{plan['name']}.html",
                 seite(f"Woche KW {plan['kw']}/{plan['jahr']}", woche_seite(pd, md, einkauf_link, nachbarn), 1, "woche",
                       links=rel(1)))
        if flags.get("einkaufslisten", True):
            schreibe(ziel / "einkauf" / f"{plan['name']}.html",
                     seite(f"Einkauf KW {plan['kw']}/{plan['jahr']}", einkauf_seite(plan, rezepte, db), 1, "einkauf", links=rel(1)))

    daten = {"ziele": config.TAGESZIELE, "korridor": korridor(), "plaene": plan_json, "budget": ek.budget(),
             "einkauf": links.get("einkauf"), "einkaufslisten": bool(flags.get("einkaufslisten", True)),
             "github": config.PROFIL.get("github_repo"), "korridore": config.KORRIDORE,
             "zutaten": zutaten_json(db), "kuechen": config.KUECHEN, "ids": sorted(rezepte),
             "namen": sorted(r["name"].lower() for r in rezepte.values())}
    schreibe(ziel / "assets" / "daten.js", "window.REZEPTBUCH = " + json.dumps(daten, ensure_ascii=False) + ";\n")
    heute = ('<div id="heute"><noscript><p>Für die Tagesansicht bitte JavaScript aktivieren. '
             '<a href="rezepte.html">Zum Rezeptbuch</a></p></noscript></div>')
    schreibe(ziel / "index.html", seite("Heute", heute, 0, "heute", links=rel(0)))
    schreibe(ziel / "rezepte.html", seite("Rezeptbuch", rezeptbuch_seite(rezepte, db), 0, "rezepte", links=rel(0)))
    if config.PROFIL.get("github_repo"):
        schreibe(ziel / "rezept-neu.html", seite("Eigenes Rezept", rezept_neu_seite(db), 0, "rezepte", links=rel(0)))
    for r in rezepte.values():
        titel, inhalt, kopf = rezept_seite(r, db, basis_url)
        schreibe(ziel / "rezept" / f"{r['id']}.html", seite(titel, inhalt, 1, "rezepte", kopf, links=rel(1)))
    schreibe(ziel / "manifest.webmanifest", json.dumps(manifest(), ensure_ascii=False, indent=1))
    dateien = precache_liste(ziel)
    version = hashlib.sha256(b"".join((ziel / d).read_bytes() for d in dateien)).hexdigest()[:12]
    schreibe(ziel / "sw.js", SW_VORLAGE % {"version": version, "dateien": json.dumps(["./"] + dateien, ensure_ascii=False)})
    return {"seiten": len(dateien), "version": version}


if __name__ == "__main__":
    info = generiere_web()
    print(f"web/ erzeugt: {info['seiten']} Dateien, Version {info['version']}")
