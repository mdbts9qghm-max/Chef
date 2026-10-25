"""Generiert Rezept-Markdown (SPEC 7), rezeptbuch.md und die Web-App (tools/web.py) aus den YAML-Daten.

CLI: python3 tools/generieren.py   → bricht ab, wenn pruefen.py Fehler meldet
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import naehrwerte as nw  # noqa: E402
import pruefen  # noqa: E402

zahl, gramm = nw.zahl, nw.gramm


# --- Platzhalter ---------------------------------------------------------------
def anzeigename(eintrag):
    return eintrag.get("name") or eintrag["zutat"]


def mengentext(eintrag, faktor=1.0):
    """„120 g“ oder „2 Eier Gr. M (120 g)“ bzw. „1 Prise (0,5 g)“."""
    g = gramm(eintrag["g"] * faktor)
    if eintrag.get("anzeige"):
        return f"{eintrag['anzeige']} ({g})"
    return g


def name_anhaengen(eintrag):
    """Braucht die Stückangabe den Zutatennamen dahinter? („1 Prise“ ja, „2 Eier Gr. M“ nein)"""
    anz = eintrag.get("anzeige")
    if not anz:
        return True
    stamm = anzeigename(eintrag).split()[0].lower().rstrip("ns")
    return stamm not in anz.lower()


def platzhalter_text(eintrag, faktor=1.0):
    """{id} → Menge + Name: „120 g Haferflocken“. Mit anzeige: „2 Eier Gr. M (120 g)“, wenn
    die Anzeige den Namen schon enthält, sonst „1 Prise Salz (0,5 g)“."""
    g = gramm(eintrag["g"] * faktor)
    name = anzeigename(eintrag)
    anz = eintrag.get("anzeige")
    if anz:
        return f"{anz} {name} ({g})" if name_anhaengen(eintrag) else f"{anz} ({g})"
    return f"{g} {name}"


def portion_text(gargewicht_portion):
    return f"ca. {gramm(round(gargewicht_portion, -1))}"


def ersetze_platzhalter(text, rezept, faktor=1.0, portion_g=None):
    idx = {e["id"]: e for e in nw.zutaten_eintraege(rezept)}

    def ersetzen(m):
        if m.group(1) == "portion_g" and portion_g is not None:
            return portion_text(portion_g * faktor)
        e = idx.get(m.group(1))
        if e is None:
            return m.group(0)
        return anzeigename(e) if m.group(2) else platzhalter_text(e, faktor)

    return pruefen.PLATZHALTER.sub(ersetzen, text)


# --- Bausteine ------------------------------------------------------------------
def sterne(bewertung):
    s = (bewertung or {}).get("sterne")
    return "noch nicht bewertet" if s is None else "★" * s + "☆" * (5 - s)


def minuten(m):
    return f"{m} min"


def ausgabepfad(rezept):
    return config.AUSGABE_REZEPTE / rezept["hauptkategorie"] / f"{rezept['id']}.md"


def prozent(teil, ganz):
    return zahl(teil / ganz * 100, 0) + " %" if ganz else "–"


def abschnitt_kopf(r, kats):
    z = r["zeit"]
    gesamt = nw.gesamtzeit(r)
    zeile_zeit = (f"Vorbereitung {minuten(z.get('vorbereitung', 0))} · Kochen {minuten(z.get('kochen', 0))} · "
                  f"Wartezeit {minuten(z.get('wartezeit', 0))} · **Gesamt {minuten(gesamt + z.get('wartezeit', 0))}**")
    if z.get("wartezeit"):
        zeile_zeit += f" (aktiv {minuten(gesamt)}; Wartezeit zählt nicht für „schnell“)"
    out = [f"# {r['name']}", ""]
    out.append(f"- **Bewertung:** {sterne(r.get('bewertung'))}")
    b = r.get("bewertung") or {}
    if b.get("kommentar"):
        out.append(f"  - „{b['kommentar']}“ ({b.get('datum', '')})")
    out.append(f"- **Kategorien:** {' · '.join(kats)} (Hauptkategorie: {config.HAUPTKATEGORIEN[r['hauptkategorie']]})")
    out.append(f"- **Küche:** {r['kueche']}")
    insp = r.get("inspiration")
    if insp:
        link = f" ([Link]({insp['link']}))" if insp.get("link") else ""
        out.append(f"- **Inspiration:** {insp['quelle']}{link}. Geändert: {insp['aenderungen']}")
    out.append(f"- **Mahlzeit:** {r['mahlzeit']} ({r['geschmack']})")
    out.append(f"- **Portionen:** {config.PORTIONEN}")
    out.append(f"- **Schwierigkeit:** {r['schwierigkeit']}")
    out.append(f"- **Zeit:** {zeile_zeit}")
    out.append(f"- **Ausstattung:** {', '.join(r['ausstattung'])}")
    return out


def abschnitt_naehrwerte(r, erg):
    p = nw.runden(erg["portion"])
    ziel = config.TAGESZIELE
    zeilen = [
        ("Kalorien", f"{zahl(p['kcal'], 0)} kcal", prozent(p["kcal"], ziel["kcal"])),
        ("Protein", f"{zahl(p['protein'])} g", prozent(p["protein"], ziel["protein"])),
        ("Fett", f"{zahl(p['fett'])} g", prozent(p["fett"], ziel["fett"])),
        ("davon gesättigt", f"{zahl(p['gesaettigt'])} g", ""),
        ("Kohlenhydrate", f"{zahl(p['kh'])} g", prozent(p["kh"], ziel["kh"])),
        ("davon Zucker", f"{zahl(p['zucker'])} g", ""),
        ("Ballaststoffe", f"{zahl(p['ballaststoffe'])} g", ""),
        ("Salz", f"{zahl(p['salz'])} g", ""),
    ]
    out = ["## Nährwerte pro Portion", "", "| Nährwert | pro Portion | Anteil Tagesziel |", "|---|---:|---:|"]
    out += [f"| {a} | {b} | {c} |" for a, b, c in zeilen]
    w = erg["portion"]
    e_p, e_k, e_f = 4 * w["protein"], 4 * w["kh"], 9 * w["fett"]
    e_sum = e_p + e_k + e_f
    out += [
        "",
        f"- **Protein pro 100 kcal:** {zahl(w['protein'] / w['kcal'] * 100)} g",
        f"- **Makroverteilung (Energie):** Protein {prozent(e_p, e_sum)} · Kohlenhydrate {prozent(e_k, e_sum)} · Fett {prozent(e_f, e_sum)}",
    ]
    art = "gemessen" if erg["gargewicht_gemessen"] else "geschätzt aus Garfaktoren"
    out.append(f"- **Gewicht fertig:** {portion_text(erg['gargewicht_gesamt'])} gesamt · "
               f"**{portion_text(erg['gargewicht_portion'])} pro Portion** ({art})")
    out.append("- **MacroFactor:** Fertiges Gericht wiegen und als Gesamtgewicht in MacroFactor eintragen, "
               "dann kannst du nach Gramm loggen.")
    return out


def abschnitt_zutaten(r):
    out = [f"## Zutaten (für {config.PORTIONEN} Portionen)", "", "| Zutat | Menge | Hinweis |", "|---|---|---|"]
    for z in r["zutaten"]:
        if "gruppe" in z:
            out.append(f"| **{z['gruppe']}** | | |")
            continue
        hinweis = z.get("hinweis") or ""
        if z.get("nicht_mitgerechnet"):
            hinweis = (hinweis + "; " if hinweis else "") + "nicht mitgerechnet"
        out.append(f"| {anzeigename(z)} | {mengentext(z)} | {hinweis} |")
    return out


def abschnitt_liste(titel, eintraege, r, nummeriert=False):
    out = [f"## {titel}", ""]
    for i, t in enumerate(eintraege, 1):
        out.append(f"{i}. {ersetze_platzhalter(t, r)}" if nummeriert else f"- {ersetze_platzhalter(t, r)}")
    return out


def abschnitt_schritte(r):
    out = ["## Zubereitung", ""]
    for i, s in enumerate(r["schritte"], 1):
        timer = f" ⏱ {s['timer_min']} min" if s.get("timer_min") else ""
        out.append(f"{i}. **{s['titel']}**{timer}: {ersetze_platzhalter(s['text'], r)}")
    return out


def variante_text(v, db):
    """Text-Variante unverändert; strukturierte Variante mit gerechneter Makro-Änderung."""
    if isinstance(v, str):
        return v
    text = f"**{v['titel']}:** {v['text']}"
    if v.get("aenderung"):
        d = nw.variante_delta(v["aenderung"], db)
        text += (f" ({nw.vorzeichen(d['kcal'], 0, ' kcal')}, {nw.vorzeichen(d['protein'], 1, ' g')} Protein, "
                 f"{nw.vorzeichen(d['fett'], 1, ' g')} Fett pro Portion)")
    return text


def abschnitt_aufbewahrung(r):
    a = r["aufbewahrung"]
    tage = a.get("kuehlschrank_tage") or 0
    out = ["## Meal Prep & Aufbewahrung", ""]
    out.append(f"- **Kühlschrank:** {tage} Tage" if tage else "- **Kühlschrank:** nicht geeignet, frisch essen")
    if a.get("einfrierbar"):
        out.append(f"- **Einfrieren:** ja, bis {a.get('einfrieren_monate', '?')} Monat(e)")
    else:
        out.append("- **Einfrieren:** nein")
    out.append(f"- **Aufwärmen:** {a['aufwaermen']}")
    if a.get("separat"):
        out.append(f"- **Separat lagern:** {a['separat']}")
    return out


def abschnitt_berechnung(r, erg, db):
    out = ["## Nährwert-Berechnung", "",
           "| Zutat | Menge | kcal | Protein | Fett | KH |", "|---|---:|---:|---:|---:|---:|"]
    for e, w in erg["zeilen"]:
        if e.get("nicht_mitgerechnet"):
            out.append(f"| {e['zutat']} | {gramm(e['g'])} | – | – | – | – |")
            continue
        out.append(f"| {e['zutat']} | {gramm(e['g'])} | {zahl(w['kcal'], 0)} | {zahl(w['protein'])} | "
                   f"{zahl(w['fett'])} | {zahl(w['kh'])} |")
    g, p = erg["gesamt"], erg["portion"]
    out.append(f"| **Summe** | | **{zahl(g['kcal'], 0)}** | **{zahl(g['protein'])}** | **{zahl(g['fett'])}** | **{zahl(g['kh'])}** |")
    out.append(f"| **Pro Portion (÷ {config.PORTIONEN})** | | **{zahl(p['kcal'], 0)}** | **{zahl(p['protein'])}** | "
               f"**{zahl(p['fett'])}** | **{zahl(p['kh'])}** |")
    pl = nw.plausibilitaet_rezept(r, db, g)
    status = "bestanden" if pl["ok"] else "NICHT bestanden"
    out += ["",
            f"**Plausibilitätscheck:** 4 × Protein + 4 × KH + 9 × Fett + 2 × Ballaststoffe = "
            f"{zahl(pl['berechnet'], 0)} kcal gegenüber {zahl(g['kcal'], 0)} kcal → Abweichung "
            f"{zahl(pl['prozent'])} % ({status}, Grenze ±{zahl(config.PLAUSI_PROZENT, 0)} %).",
            "",
            f"*Schätzwerte: {config.HINWEIS_SCHAETZWERTE}*"]
    return out


def rezept_markdown(r, db):
    erg = nw.rezept_naehrwerte(r, db)
    kats = nw.kategorien(r, erg["portion"])
    teile = [
        abschnitt_kopf(r, kats),
        abschnitt_naehrwerte(r, erg),
        abschnitt_zutaten(r),
        abschnitt_liste("Mise en place", r["mise_en_place"], r),
        abschnitt_schritte(r),
        abschnitt_liste("Zeitablauf", r.get("zeitablauf") or ["Keine parallelen Arbeitsschritte nötig."], r),
        abschnitt_liste("Häufige Fehler", r["fehler"], r),
        ["## Anrichten", "", ersetze_platzhalter(r["anrichten"], r, portion_g=erg["gargewicht_portion"])],
        abschnitt_aufbewahrung(r),
        abschnitt_liste("Varianten & Austausch", [variante_text(v, db) for v in r["varianten"]], r),
        abschnitt_liste("Tipps", r["tipps"], r),
        abschnitt_berechnung(r, erg, db),
    ]
    kopf = "<!-- Generiert aus daten/rezepte/{}.yaml – nicht von Hand bearbeiten. -->".format(r["id"])
    return kopf + "\n" + "\n\n".join("\n".join(t) for t in teile) + "\n"


def rezeptbuch_markdown(rezepte, db):
    out = ["<!-- Generiert – nicht von Hand bearbeiten. -->", "# Rezeptbuch", "",
           f"{len(rezepte)} Rezepte · Nährwerte pro Portion · Tagesziel {zahl(config.TAGESZIELE['kcal'], 0)} kcal / "
           f"{config.TAGESZIELE['protein']} g Protein", ""]
    for slug, titel in config.HAUPTKATEGORIEN.items():
        auswahl = sorted((r for r in rezepte if r["hauptkategorie"] == slug), key=lambda r: r["name"])
        if not auswahl:
            continue
        out += [f"## {titel}", "", "| Rezept | Mahlzeit | Küche | kcal | Protein | Zeit | Kategorien | Bewertung |",
                "|---|---|---|---:|---:|---:|---|---|"]
        for r in auswahl:
            erg = nw.rezept_naehrwerte(r, db)
            p = nw.runden(erg["portion"])
            kats = nw.kategorien(r, erg["portion"])
            s = (r.get("bewertung") or {}).get("sterne")
            bew = sterne(r.get("bewertung")) if s else "–"
            name = f"[{r['name']}](rezepte/{slug}/{r['id']}.md)"
            if s is not None and s <= 2:
                name = f"~~{name}~~ (aussortiert)"
            out.append(f"| {name} | {r['mahlzeit']} | {r['kueche']} | {zahl(p['kcal'], 0)} | {zahl(p['protein'])} g | "
                       f"{nw.gesamtzeit(r)} min | {', '.join(kats)} | {bew} |")
        out.append("")
    out.append(f"*{config.HINWEIS_SCHAETZWERTE} Die Pläne sind eine Empfehlung und ersetzen keine "
               "Ernährungs- oder ärztliche Beratung.*")
    return "\n".join(out) + "\n"


def generiere_alles():
    db = nw.lade_zutaten()
    rezepte = nw.lade_alle_rezepte()
    ergebnisse = pruefen.pruefe_alle(rezepte, db)
    if not all(e.ok for e in ergebnisse):
        print(pruefen.bericht(ergebnisse))
        print("\nAbbruch: erst Fehler beheben.")
        return 1
    # Ausgabeordner neu aufbauen, damit verschobene/gelöschte Rezepte nicht liegen bleiben
    for slug in config.HAUPTKATEGORIEN:
        shutil.rmtree(config.AUSGABE_REZEPTE / slug, ignore_errors=True)
    for r in rezepte.values():
        pfad = ausgabepfad(r)
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(rezept_markdown(r, db), encoding="utf-8")
    config.REZEPTBUCH_MD.write_text(rezeptbuch_markdown(list(rezepte.values()), db), encoding="utf-8")
    warnungen = sum(len(e.warnungen) for e in ergebnisse)
    print(f"{len(rezepte)} Rezepte generiert, rezeptbuch.md aktualisiert ({warnungen} Warnungen).")
    import web   # erst hier, weil web.py dieses Modul importiert
    info = web.generiere_web(rezepte, db)
    print(f"Web-App erzeugt: {info['seiten']} Dateien in web/, Service-Worker-Version {info['version']}.")
    return 0


if __name__ == "__main__":
    sys.exit(generiere_alles())
