"""Wochenplan: laden, Tagessummen rechnen, Regeln aus SPEC 8.2 prüfen, Markdown erzeugen.

CLI: python3 tools/wochenplan.py KW-45-2026   → prüft und schreibt wochenplaene/KW-45-2026.md
"""
import csv
import datetime as dt
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import naehrwerte as nw  # noqa: E402

MAKROS = ["kcal", "protein", "fett", "kh"]
zahl = nw.zahl


# --- Laden ---------------------------------------------------------------------
def lade_plan(name_oder_pfad):
    pfad = Path(name_oder_pfad)
    if not pfad.suffix:
        pfad = config.WOCHENPLAENE_DIR / f"{name_oder_pfad}.yaml"
    with open(pfad, encoding="utf-8") as f:
        plan = yaml.safe_load(f)
    plan.setdefault("name", pfad.stem)
    return plan


def lade_packungen(pfad=config.PACKUNGEN_CSV):
    with open(pfad, encoding="utf-8") as f:
        zeilen = csv.DictReader(z for z in f if z.strip() and not z.startswith("#"))
        return {z["zutat"]: {"abteilung": z["abteilung"], "packung_g": float(z["packung_g"]),
                             "packung_text": z["packung_text"],
                             "preis": float(z["preis_eur"]) if z.get("preis_eur") else None,
                             "haltbar_tage_offen": int(z["haltbar_tage_offen"])} for z in zeilen}


def datum(x):
    return x if isinstance(x, dt.date) else dt.date.fromisoformat(str(x))


def tag_kurz(d):
    return f"{config.WOCHENTAGE[d.weekday()]} {d.strftime('%d.%m.')}"


# --- Schichten -------------------------------------------------------------------
def schicht(d, schichten=None):
    """Schichttyp (Tag/Nacht/frei) für ein Datum aus dem Zyklus im Profil."""
    s = schichten if schichten is not None else config.SCHICHTEN
    if not s:
        return "frei"
    zyklus = s["zyklus"]
    return zyklus[(datum(d) - datum(s["start"])).days % len(zyklus)]


# --- Einträge ---------------------------------------------------------------------
@dataclass
class Eintrag:
    datum: dt.date
    slot: str
    rezept_id: str
    faktor: float = 1.0
    kochen: bool = False
    ladungen: int = 1
    rest_von: str = None
    gekocht_am: dt.date = None
    box: bool = False
    einfrieren: bool = False
    notiz: str = ""

    @property
    def schluessel(self):
        return f"{self.datum.isoformat()}/{self.slot}"


def eintraege(plan):
    """Alle Mahlzeiten als Eintrag-Objekte (Reihenfolge: Tag, Slot)."""
    out = []
    for tag in plan["tage"]:
        d = datum(tag["datum"])
        for slot in config.SLOTS:
            e = tag.get(slot)
            if not e:
                continue
            out.append(Eintrag(
                datum=d, slot=slot, rezept_id=e["rezept"], faktor=float(e.get("faktor", 1.0)),
                kochen=bool(e.get("kochen")), ladungen=int(e.get("ladungen", 1)), rest_von=e.get("rest_von"),
                gekocht_am=datum(e["gekocht_am"]) if e.get("gekocht_am") else None,
                box=bool(e.get("box")), einfrieren=bool(e.get("einfrieren")), notiz=e.get("notiz", "")))
    idx = {e.schluessel: e for e in out}
    for e in out:   # Kochdatum: eigenes, sonst Tag der Mahlzeit; Reste erben vom Original
        if e.kochen and e.gekocht_am is None:
            e.gekocht_am = e.datum
    for e in out:
        if e.rest_von and e.rest_von in idx:
            e.gekocht_am = idx[e.rest_von].gekocht_am
    return out


# --- Rechnen -----------------------------------------------------------------------
def portion(rezept_id, faktor, rezepte, db):
    return {k: v * faktor for k, v in nw.rezept_naehrwerte(rezepte[rezept_id], db)["portion"].items()}


def extra_werte(extra, db):
    w = db[extra["zutat"]]
    return {k: w[k] * extra["g"] / 100 for k in nw.NAEHRSTOFFE}


def tagessumme(tag, rezepte, db):
    """Summen eines Tages: Mahlzeiten × faktor, Extras, Auswärts-Platzhalter."""
    summe = {k: 0.0 for k in nw.NAEHRSTOFFE}
    for slot in config.SLOTS:
        e = tag.get(slot)
        if e:
            for k, v in portion(e["rezept"], float(e.get("faktor", 1.0)), rezepte, db).items():
                summe[k] += v
    for x in tag.get("extras") or []:
        for k, v in extra_werte(x, db).items():
            summe[k] += v
    if tag.get("auswaerts"):
        a = tag["auswaerts"]
        for k in MAKROS:
            summe[k] += a.get(f"platzhalter_{k}", config.AUSWAERTS[k])
    return summe


def abweichung(summe):
    ziel = config.TAGESZIELE
    return {k: summe[k] - ziel[k] for k in MAKROS}


# --- Prüfen --------------------------------------------------------------------------
@dataclass
class Pruefung:
    fehler: list = field(default_factory=list)
    warnungen: list = field(default_factory=list)
    erinnerungen: dict = field(default_factory=dict)   # datum → [Texte] (für den Vortag-Hinweis gesammelt)

    @property
    def ok(self):
        return not self.fehler


def einkauf_fuer(gekocht_am, plan):
    """Spätester Einkaufstermin am oder vor dem Kochtag (sonst der erste)."""
    termine = sorted(datum(e["datum"]) for e in plan.get("einkauf", []))
    if not termine:
        return None
    vorher = [t for t in termine if t <= gekocht_am]
    return vorher[-1] if vorher else termine[0]


def frische_typen(rezept, db, packungen):
    """[(Zutat, 'tk'|'frisch', max. Tage nach Einkauf)] für Fisch, Garnelen, Hack und Frischfleisch."""
    out = []
    for z in nw.zutaten_eintraege(rezept):
        typ = db[z["zutat"]]["typ"]
        quelle = typ.split("-")[0]
        if quelle not in config.FLEISCH_FISCH:
            continue
        tk = packungen.get(z["zutat"], {}).get("abteilung") == config.TK_ABTEILUNG
        streng = quelle in config.FISCH_GARNELEN or typ.endswith("-hack")
        out.append((z["zutat"], "tk" if tk else "frisch",
                    config.FRISCH_MAX_TAGE if streng else config.FLEISCH_FRISCH_MAX_TAGE))
    return out


def merke(p, d, text):
    p.erinnerungen.setdefault(d, [])
    if text not in p.erinnerungen[d]:
        p.erinnerungen[d].append(text)


def pruefe_plan(plan, rezepte, db, packungen=None):
    packungen = packungen if packungen is not None else lade_packungen()
    p = Pruefung()
    alle = eintraege(plan)
    idx = {e.schluessel: e for e in alle}
    ziel = config.TAGESZIELE

    for e in alle:
        wo = f"{tag_kurz(e.datum)} {config.SLOT_NAMEN[e.slot]}"
        if e.rezept_id not in rezepte:
            p.fehler.append(f"{wo}: Rezept „{e.rezept_id}“ existiert nicht")
            continue
        r = rezepte[e.rezept_id]
        # Faktor
        if e.faktor > config.FAKTOR_MAX or e.faktor <= 0 or (e.faktor / config.FAKTOR_SCHRITT) % 1:
            p.fehler.append(f"{wo}: Faktor {zahl(e.faktor, 2)} nicht erlaubt (Schritte {zahl(config.FAKTOR_SCHRITT, 2)}, "
                            f"max. {zahl(config.FAKTOR_MAX, 1)})")
        # Bewertung
        sterne = (r.get("bewertung") or {}).get("sterne")
        if sterne is not None and sterne <= 2:
            p.fehler.append(f"{wo}: „{r['name']}“ hat {sterne} Sterne und ist aussortiert")
        # Kochen oder Rest
        if e.kochen == bool(e.rest_von):
            p.fehler.append(f"{wo}: braucht genau eins von „kochen: true“ oder „rest_von“")
        if e.rest_von:
            q = idx.get(e.rest_von)
            if q is None or not q.kochen:
                p.fehler.append(f"{wo}: rest_von „{e.rest_von}“ verweist auf keinen Koch-Eintrag")
            elif q.rezept_id != e.rezept_id or q.faktor != e.faktor:
                p.fehler.append(f"{wo}: Rest passt nicht zum Original ({q.rezept_id} × {zahl(q.faktor, 2)})")
        # Haltbarkeit (Reste und vorgekochte Mahlzeiten)
        if e.gekocht_am:
            alter = (e.datum - e.gekocht_am).days
            erlaubt = r["aufbewahrung"].get("kuehlschrank_tage") or 0
            if alter < 0:
                p.fehler.append(f"{wo}: wird vor dem Kochen gegessen")
            elif alter > erlaubt:
                p.fehler.append(f"{wo}: „{r['name']}“ ist {alter} Tage alt, erlaubt sind {erlaubt}")
        # Frühstück süß
        if e.slot == "fruehstueck" and r["geschmack"] != "süß":
            p.warnungen.append(f"{wo}: Frühstück ist nicht süß")
        # Schicht-Boxen
        s = schicht(e.datum, plan.get("schichten"))
        box_slots = (config.SCHICHTEN.get("boxen") or {}).get(s, [])
        if e.slot in box_slots:
            vorher = e.gekocht_am is not None and e.gekocht_am < e.datum
            if s == "Tag" and not vorher:
                p.warnungen.append(f"{wo}: Tagschicht – Box sollte am Vortag vorbereitet sein")
            if (r["aufbewahrung"].get("kuehlschrank_tage") or 0) < 1 and not (s == "Nacht" and e.gekocht_am == e.datum):
                p.warnungen.append(f"{wo}: „{r['name']}“ ist nicht als Box geeignet")

    # Reste-Anzahl ≤ Ladungen
    for q in (e for e in alle if e.kochen):
        n = 1 + sum(1 for e in alle if e.rest_von == q.schluessel)
        if n > q.ladungen:
            p.fehler.append(f"{tag_kurz(q.datum)} {config.SLOT_NAMEN[q.slot]}: {n} Mahlzeiten, aber nur "
                            f"{q.ladungen} Ladung(en) gekocht")
        elif n < q.ladungen:
            p.warnungen.append(f"{tag_kurz(q.datum)} {config.SLOT_NAMEN[q.slot]}: {q.ladungen} Ladungen gekocht, "
                               f"nur {n} verplant")

    # Frische Fisch/Garnelen/Hack + Erinnerungen
    for q in (e for e in alle if e.kochen and e.rezept_id in rezepte):
        r = rezepte[q.rezept_id]
        ek = einkauf_fuer(q.gekocht_am, plan)
        for zutat, art, max_tage in frische_typen(r, db, packungen):
            name = db_name(zutat)
            if art == "tk":
                merke(p, q.gekocht_am, f"{name} für {r['name']} aus dem Gefrierfach in den Kühlschrank legen (auftauen)")
            elif ek and (q.gekocht_am - ek).days > max_tage:
                if q.einfrieren:
                    merke(p, q.gekocht_am, f"{name} für {r['name']} aus dem Gefrierfach in den Kühlschrank legen (auftauen)")
                else:
                    p.fehler.append(f"{tag_kurz(q.gekocht_am)}: {zutat} wird {(q.gekocht_am - ek).days} Tage nach dem "
                                    f"Einkauf gegart (max. {max_tage}) – „einfrieren: true“ setzen")
        wz = r["zeit"].get("wartezeit", 0)
        if wz >= config.WARTEZEIT_VORABEND_MIN:
            merke(p, q.gekocht_am, f"{r['name']} am Vorabend ansetzen ({wz // 60} h Wartezeit)")

    # Tagesregeln
    vorher_abend = None
    drei_sterne = set()
    for tag in plan["tage"]:
        d = datum(tag["datum"])
        if any(tag.get(s) and tag[s]["rezept"] not in rezepte for s in config.SLOTS):
            continue
        summe = tagessumme(tag, rezepte, db)
        kurz = tag_kurz(d)
        if summe["protein"] < config.PLAN_PROTEIN_MIN:
            p.fehler.append(f"{kurz}: Protein {zahl(summe['protein'])} g < {config.PLAN_PROTEIN_MIN} g")
        if abs(summe["kcal"] - ziel["kcal"]) > config.PLAN_KCAL_TOLERANZ:
            p.fehler.append(f"{kurz}: {zahl(summe['kcal'], 0)} kcal, Ziel {zahl(ziel['kcal'], 0)} ± {config.PLAN_KCAL_TOLERANZ}")
        if abs(summe["fett"] - ziel["fett"]) > config.PLAN_FETT_TOLERANZ or summe["fett"] < config.PLAN_FETT_MIN:
            p.fehler.append(f"{kurz}: Fett {zahl(summe['fett'])} g, Ziel {ziel['fett']} ± {config.PLAN_FETT_TOLERANZ} g")
        if abs(summe["kh"] - ziel["kh"]) > config.PLAN_KH_TOLERANZ:
            p.fehler.append(f"{kurz}: KH {zahl(summe['kh'])} g, Ziel {ziel['kh']} ± {config.PLAN_KH_TOLERANZ} g")
        for s in config.SLOTS:
            if tag.get(s):
                st = (rezepte[tag[s]["rezept"]].get("bewertung") or {}).get("sterne")
                if st == 3:
                    drei_sterne.add(tag[s]["rezept"])
        # Abendessen: Küche und Proteinquelle nicht wie am Vortag
        abend = tag.get("abend")
        if abend and not tag.get("auswaerts"):
            r = rezepte[abend["rezept"]]
            jetzt = (r["kueche"], nw.hauptproteinquelle(r, db))
            if vorher_abend and not plan.get("gleiche_kueche_erlaubt"):
                if jetzt[0] == vorher_abend[0]:
                    p.fehler.append(f"{kurz}: Abendessen wieder {jetzt[0]} wie am Vortag")
                if jetzt[1] == vorher_abend[1]:
                    p.fehler.append(f"{kurz}: Abendessen wieder mit {config.PROTEIN_GRUPPEN.get(jetzt[1], jetzt[1])} wie am Vortag")
            vorher_abend = jetzt
        else:
            vorher_abend = None
    # Wiederholungen (Entscheidung 25.10.2026): Hauptgericht max. 1 Kochvorgang, Frühstück/Snack max. 2 Tage
    koch_haupt = [e.rezept_id for e in alle if e.kochen and e.slot in ("mittag", "abend")]
    for rid in sorted(set(koch_haupt)):
        if koch_haupt.count(rid) > config.PLANER_HAUPT_MAX_KOCHEN:
            p.fehler.append(f"„{rezepte[rid]['name']}“ wird {koch_haupt.count(rid)}× gekocht "
                            f"(max. {config.PLANER_HAUPT_MAX_KOCHEN}× pro Woche, Reste zählen nicht)")
    for slot, maxi in (("fruehstueck", config.PLANER_FRUEHSTUECK_MAX_TAGE), ("snack", config.PLANER_SNACK_MAX_TAGE)):
        ids = [e.rezept_id for e in alle if e.slot == slot]
        for rid in sorted(set(ids)):
            if ids.count(rid) > maxi:
                p.fehler.append(f"„{rezepte[rid]['name']}“ an {ids.count(rid)} Tagen als {config.SLOT_NAMEN[slot]} "
                                f"(max. {maxi})")
    if len(drei_sterne) > config.DREI_STERNE_MAX:
        p.fehler.append(f"3-Sterne-Rezepte {len(drei_sterne)}× in der Woche (max. {config.DREI_STERNE_MAX})")
    return p


def db_name(zutat):
    return zutat.replace(" roh", "").replace(" geschält", "")


# --- Markdown -------------------------------------------------------------------------
def rezept_link(r, prefix="../"):
    return f"[{r['name']}]({prefix}rezepte/{r['hauptkategorie']}/{r['id']}.md)"


def zeit_minus(uhrzeit, minuten):
    h, m = map(int, uhrzeit.split(":"))
    t = (h * 60 + m - minuten) % (24 * 60)
    return f"{t // 60:02d}:{t % 60:02d}"


def zeit_plus(uhrzeit, minuten):
    return zeit_minus(uhrzeit, -minuten)


def abw_text(wert, ziel, einheit, nachkomma=1):
    d = wert - ziel
    return f"{nw.vorzeichen(d, nachkomma, ' ' + einheit)} ({nw.vorzeichen(d / ziel * 100, 0, ' %')})"


def mahlzeit_kurz(e_dict, rezepte, db):
    r = rezepte[e_dict["rezept"]]
    w = portion(e_dict["rezept"], float(e_dict.get("faktor", 1.0)), rezepte, db)
    return r, w


def wochenplan_markdown(plan, rezepte, db, pruefung=None):
    pruefung = pruefung or pruefe_plan(plan, rezepte, db)
    alle = eintraege(plan)
    ziel = config.TAGESZIELE
    tage = plan["tage"]
    erste, letzte = datum(tage[0]["datum"]), datum(tage[-1]["datum"])
    out = [f"<!-- Generiert aus daten/wochenplaene/{plan['name']}.yaml – nicht von Hand bearbeiten. -->",
           f"# Wochenplan KW {plan['kw']}/{plan['jahr']} ({erste.strftime('%d.%m.')}–{letzte.strftime('%d.%m.%Y')})", ""]
    ek = ", ".join(f"{e['tag']} {datum(e['datum']).strftime('%d.%m.')} ({e.get('art', '')})" for e in plan.get("einkauf", []))
    out += [f"Tagesziel: {zahl(ziel['kcal'], 0)} kcal · {ziel['protein']} g Protein · {ziel['fett']} g Fett · "
            f"{ziel['kh']} g KH · Einkauf: {ek} · [Einkaufsliste](../einkaufslisten/{plan['name']}.md)", ""]
    if pruefung.fehler:
        out += ["> **Achtung, Regelverstöße:**"] + [f"> - {f}" for f in pruefung.fehler] + [""]

    vorab = pruefung.erinnerungen.get(erste, [])
    if vorab:
        out += [f"**Vor Wochenbeginn ({tag_kurz(erste - dt.timedelta(days=1))}):**"] + [f"- [ ] {x}" for x in vorab] + [""]

    # Übersicht
    out += ["## Übersicht", "", "| Tag | Schicht | Frühstück | Mittag | Abend | Snack/Extras | kcal | Protein |",
            "|---|---|---|---|---|---|---:|---:|"]
    for tag in tage:
        d = datum(tag["datum"])
        zellen = []
        for s in ["fruehstueck", "mittag", "abend"]:
            if tag.get("auswaerts") and tag["auswaerts"].get("mahlzeit") == s:
                zellen.append(f"auswärts (~{config.AUSWAERTS['kcal']} kcal)")
            elif tag.get(s):
                r, w = mahlzeit_kurz(tag[s], rezepte, db)
                zellen.append(f"{rezept_link(r)}<br>{nw.gesamtzeit(r)} min · {zahl(w['kcal'], 0)} kcal · "
                              f"{zahl(w['protein'], 0)} g P")
            else:
                zellen.append("–")
        extra = []
        if tag.get("snack"):
            r, w = mahlzeit_kurz(tag["snack"], rezepte, db)
            extra.append(f"{rezept_link(r)} ({zahl(w['kcal'], 0)} kcal)")
        for x in tag.get("extras") or []:
            extra.append(x.get("text") or f"{nw.gramm(x['g'])} {x['zutat']}")
        summe = tagessumme(tag, rezepte, db)
        out.append(f"| {tag_kurz(d)} | {schicht(d, plan.get('schichten'))} | {' | '.join(zellen)} | "
                   f"{'<br>'.join(extra) or '–'} | {zahl(summe['kcal'], 0)} | {zahl(summe['protein'], 0)} g |")
    out.append("")

    # Tage
    for i, tag in enumerate(tage):
        d = datum(tag["datum"])
        s = schicht(d, plan.get("schichten"))
        zeiten = config.ESSENSZEITEN.get(s, config.ESSENSZEITEN.get("frei", {}))
        titel = f"## {config.WOCHENTAGE_LANG[d.weekday()]}, {d.strftime('%d.%m.%Y')}"
        if s != "frei":
            titel += f" · {s}schicht {config.SCHICHTEN['zeiten'][s]}"
        else:
            titel += " · frei"
        out += [titel, ""]
        for slot in config.SLOTS:
            if tag.get("auswaerts") and tag["auswaerts"].get("mahlzeit") == slot:
                a = config.AUSWAERTS
                out.append(f"- **{config.SLOT_NAMEN[slot]}:** auswärts – Platzhalter {a['kcal']} kcal · {a['protein']} g P · "
                           f"{a['fett']} g F · {a['kh']} g KH")
                continue
            e = tag.get(slot)
            if not e:
                continue
            r, w = mahlzeit_kurz(e, rezepte, db)
            info = [f"{zahl(w['kcal'], 0)} kcal · {zahl(w['protein'])} g P"]
            if e.get("faktor", 1.0) != 1.0:
                info.append(f"Faktor {zahl(float(e['faktor']), 2)}: alle Mengen × {zahl(float(e['faktor']), 2)}")
            eintrag = next(x for x in alle if x.datum == d and x.slot == slot)
            if eintrag.kochen:
                if eintrag.gekocht_am != d:
                    info.append(f"vorgekocht am {tag_kurz(eintrag.gekocht_am)}")
                if eintrag.ladungen > 1:
                    info.append(f"Rezept × {eintrag.ladungen} kochen ({eintrag.ladungen * config.PORTIONEN} Portionen)")
            else:
                info.append(f"Rest vom {tag_kurz(eintrag.gekocht_am)}")
            if e.get("box") or slot in (config.SCHICHTEN.get("boxen") or {}).get(s, []):
                info.append(f"📦 Box, {zeiten.get(slot, '')} Uhr")
            elif zeiten.get(slot):
                info.append(f"{zeiten[slot]} Uhr")
            if e.get("notiz"):
                info.append(e["notiz"])
            out.append(f"- **{config.SLOT_NAMEN[slot]}:** {rezept_link(r)} – {' · '.join(info)}")
        for x in tag.get("extras") or []:
            w = extra_werte(x, db)
            out.append(f"- **Extra:** {x.get('text') or x['zutat']} ({nw.gramm(x['g'])}) – {zahl(w['kcal'], 0)} kcal · "
                       f"{zahl(w['protein'])} g P · {zahl(w['fett'])} g F")
        summe = tagessumme(tag, rezepte, db)
        out += ["", "| | Summe | Ziel | Abweichung |", "|---|---:|---:|---:|",
                f"| kcal | {zahl(summe['kcal'], 0)} | {zahl(ziel['kcal'], 0)} | {abw_text(summe['kcal'], ziel['kcal'], 'kcal', 0)} |",
                f"| Protein | {zahl(summe['protein'])} g | ≥ {config.PLAN_PROTEIN_MIN} g | {abw_text(summe['protein'], ziel['protein'], 'g')} |",
                f"| Fett | {zahl(summe['fett'])} g | {ziel['fett']} g | {abw_text(summe['fett'], ziel['fett'], 'g')} |",
                f"| KH | {zahl(summe['kh'])} g | {ziel['kh']} g | {abw_text(summe['kh'], ziel['kh'], 'g')} |", ""]
        if tag.get("auswaerts"):
            out += ["**Tipps fürs Restaurant:**"] + [f"- {t}" for t in config.AUSWAERTS_TIPPS] + [""]
        # Zeitplan für alles, was heute gekocht wird
        heute = [e for e in alle if e.kochen and e.gekocht_am == d]
        if heute:
            plan_zeilen = []   # (Startzeit, Text) – chronologisch sortiert
            box_slots = (config.SCHICHTEN.get("boxen") or {}).get(s, [])
            for e in (x for x in heute if x.datum == d):
                r = rezepte[e.rezept_id]
                aktiv = nw.gesamtzeit(r)
                wz = r["zeit"].get("wartezeit", 0)
                extra = f", × {e.ladungen}" if e.ladungen > 1 else ""
                if e.slot in box_slots:   # Box: vor Schichtbeginn fertig
                    fertig = zeit_minus(config.SCHICHTEN["zeiten"][s][:5], config.BOX_FERTIG_VOR_SCHICHT_MIN)
                    ziel_text = f"{fertig} fertig, in die Box"
                else:
                    fertig = zeiten.get(e.slot, "12:00")
                    ziel_text = f"{fertig} essen"
                start = zeit_minus(fertig, aktiv + (wz if wz < config.WARTEZEIT_VORABEND_MIN else 0))
                plan_zeilen.append((start, f"{r['name']} starten ({aktiv} min aktiv{extra}) → {ziel_text}"))
            t = config.MEAL_PREP_START
            for e in meal_prep_reihenfolge([x for x in heute if x.datum != d], rezepte):
                r = rezepte[e.rezept_id]
                plan_zeilen.append((t, f"Meal Prep: {r['name']} für {tag_kurz(e.datum)} {config.SLOT_NAMEN[e.slot]} "
                                       f"({nw.gesamtzeit(r)} min)"))
                t = zeit_plus(t, r["zeit"].get("vorbereitung", 0))
            # Tage mit Nachtschicht: Zeiten nach Mitternacht ans Ende
            def sortier(z):
                h = int(z[0][:2])
                return (h + 24 if h < 6 else h, z[0])
            out += ["**Zeitplan:**"] + [f"- {zt} {txt}" for zt, txt in sorted(plan_zeilen, key=sortier)] + [""]
        erinn = erinnerungen_morgen(plan, i, rezepte, pruefung)
        if erinn:
            out += ["**Erinnerungen für morgen:**"] + [f"- [ ] {x}" for x in erinn] + [""]

    # Reste-Übersicht
    out += ["## Reste-Übersicht", "", "| Gericht | gekocht | Portionen | gegessen | Lagerung |", "|---|---|---:|---|---|"]
    for q in (e for e in alle if e.kochen and (e.ladungen > 1 or e.gekocht_am != e.datum)):
        r = rezepte[q.rezept_id]
        gegessen = [q] + [e for e in alle if e.rest_von == q.schluessel]
        wann = ", ".join(f"{tag_kurz(e.datum)} {config.SLOT_NAMEN[e.slot]}" for e in gegessen)
        a = r["aufbewahrung"]
        out.append(f"| {r['name']} | {tag_kurz(q.gekocht_am)} | {q.ladungen * config.PORTIONEN} | {wann} | "
                   f"Kühlschrank max. {a.get('kuehlschrank_tage', 0)} Tage{', einfrierbar' if a.get('einfrierbar') else ''} |")
    out.append("")

    # Meal-Prep-Plan
    prep_tage = sorted({e.gekocht_am for e in alle if e.kochen and e.gekocht_am != e.datum})
    if prep_tage:
        out += ["## Meal-Prep-Plan", ""]
        for pt in prep_tage:
            jobs = meal_prep_reihenfolge([e for e in alle if e.kochen and e.gekocht_am == pt and e.datum != pt], rezepte)
            sequenziell = sum(nw.gesamtzeit(rezepte[e.rezept_id]) for e in jobs)
            parallel = sum(rezepte[e.rezept_id]["zeit"].get("vorbereitung", 0) for e in jobs) + \
                max(rezepte[e.rezept_id]["zeit"].get("kochen", 0) for e in jobs)
            out += [f"### {config.WOCHENTAGE_LANG[pt.weekday()]}, {pt.strftime('%d.%m.')} ab {config.MEAL_PREP_START} Uhr", ""]
            for n, e in enumerate(jobs, 1):
                r = rezepte[e.rezept_id]
                wo = "Ofen" if ofen_rezept(r) else ("Airfryer" if "Airfryer" in r["ausstattung"] else "Herd/kalt")
                out.append(f"{n}. **{r['name']}** ({wo}, {r['zeit'].get('vorbereitung', 0)} min Vorbereitung + "
                           f"{r['zeit'].get('kochen', 0)} min Garzeit) → Box für {tag_kurz(e.datum)} {config.SLOT_NAMEN[e.slot]}")
            out += ["", f"Reihenfolge: Ofengerichte zuerst, während sie backen die Herd- und kalten Gerichte vorbereiten. "
                        f"Gesamtdauer ca. {parallel} min parallel (nacheinander wären es {sequenziell} min). "
                        "Gekochtes innerhalb von 1 Stunde abkühlen und in den Kühlschrank.", ""]

    # Wochenbilanz
    summen = [tagessumme(t, rezepte, db) for t in tage]
    n = len(summen)
    avg = {k: sum(s[k] for s in summen) / n for k in MAKROS}
    tage_ok = sum(1 for t in tage if not any(f.startswith(tag_kurz(datum(t["datum"]))) for f in pruefung.fehler))
    out += ["## Wochenbilanz", "", "| | Ø pro Tag | Ziel | Abweichung |", "|---|---:|---:|---:|",
            f"| kcal | {zahl(avg['kcal'], 0)} | {zahl(ziel['kcal'], 0)} | {abw_text(avg['kcal'], ziel['kcal'], 'kcal', 0)} |",
            f"| Protein | {zahl(avg['protein'])} g | {ziel['protein']} g | {abw_text(avg['protein'], ziel['protein'], 'g')} |",
            f"| Fett | {zahl(avg['fett'])} g | {ziel['fett']} g | {abw_text(avg['fett'], ziel['fett'], 'g')} |",
            f"| KH | {zahl(avg['kh'])} g | {ziel['kh']} g | {abw_text(avg['kh'], ziel['kh'], 'g')} |", ""]
    out.append(f"**Einschätzung:** {tage_ok} von {n} Tagen erfüllen alle Regeln aus SPEC 8.2. " + einschaetzung(avg, summen))
    out += ["", f"*{config.HINWEIS_SCHAETZWERTE} Der Plan ist eine Empfehlung und ersetzt keine Ernährungs- oder ärztliche Beratung.*"]
    return "\n".join(out) + "\n"


def erinnerungen_morgen(plan, i, rezepte, pruefung):
    """Erinnerungen am Tag i für den Folgetag: Auftauen, Ansetzen, Boxen packen."""
    tage = plan["tage"]
    morgen = datum(tage[i]["datum"]) + dt.timedelta(days=1)
    erinn = list(pruefung.erinnerungen.get(morgen, []))
    if i + 1 < len(tage):
        sm = schicht(morgen, plan.get("schichten"))
        for slot in (config.SCHICHTEN.get("boxen") or {}).get(sm, []):
            if tage[i + 1].get(slot):
                erinn.append(f"Box für {config.SLOT_NAMEN[slot]} ({rezepte[tage[i + 1][slot]['rezept']]['name']}) "
                             f"für die {sm}schicht packen")
    return erinn


def einschaetzung(avg, summen):
    ziel = config.TAGESZIELE
    teile = []
    p_min = min(s["protein"] for s in summen)
    teile.append(f"Protein liegt an jedem Tag bei mindestens {zahl(p_min, 0)} g." if p_min >= config.PLAN_PROTEIN_MIN
                 else f"Protein fällt an mindestens einem Tag auf {zahl(p_min, 0)} g.")
    if avg["fett"] < ziel["fett"] - 5:
        teile.append(f"Fett liegt im Schnitt {zahl(ziel['fett'] - avg['fett'], 0)} g unter dem Ziel – die Rezepte sind fettarm, "
                     "die Extras gleichen das nur teilweise aus.")
    if avg["kh"] > ziel["kh"] + 10:
        teile.append("Kohlenhydrate liegen etwas über dem Ziel.")
    if abs(avg["kcal"] - ziel["kcal"]) <= 50:
        teile.append("Die Kalorien treffen das Ziel im Schnitt sehr genau.")
    return " ".join(teile)


def ofen_rezept(r):
    return any("Backofen" in a for a in r["ausstattung"])


def meal_prep_reihenfolge(jobs, rezepte):
    """Ofengerichte mit der längsten Garzeit zuerst, dann Herd/Airfryer, kalte Gerichte zuletzt."""
    def rang(e):
        r = rezepte[e.rezept_id]
        art = 0 if ofen_rezept(r) else (1 if r["zeit"].get("kochen", 0) > 0 else 2)
        return (art, -r["zeit"].get("kochen", 0))
    return sorted(jobs, key=rang)


def main(argv):
    if not argv:
        sys.exit("Aufruf: python3 tools/wochenplan.py KW-45-2026")
    plan = lade_plan(argv[0])
    db = nw.lade_zutaten()
    rezepte = nw.lade_alle_rezepte()
    p = pruefe_plan(plan, rezepte, db)
    for f in p.fehler:
        print("✗", f)
    for w in p.warnungen:
        print("!", w)
    config.AUSGABE_WOCHENPLAENE.mkdir(exist_ok=True)
    ziel = config.AUSGABE_WOCHENPLAENE / f"{plan['name']}.md"
    ziel.write_text(wochenplan_markdown(plan, rezepte, db, p), encoding="utf-8")
    print(f"{len(p.fehler)} Fehler, {len(p.warnungen)} Warnungen · {ziel.relative_to(config.WURZEL)} geschrieben.")
    return 0 if p.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
