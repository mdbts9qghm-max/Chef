"""Einkaufsliste aus dem Wochenplan berechnen (SPEC 8.5).

CLI: python3 tools/einkauf.py KW-45-2026 [--reste-uebernehmen]
     schreibt einkaufslisten/KW-45-2026.md; mit --reste-uebernehmen werden die Reste in daten/vorrat.yaml eingetragen.
"""
import datetime as dt
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import naehrwerte as nw  # noqa: E402
import wochenplan as wp  # noqa: E402

zahl, gramm = nw.zahl, nw.gramm
EPS = 1e-6


def lade_vorrat(pfad=config.VORRAT_YAML):
    if not Path(pfad).exists():
        return []
    with open(pfad, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("vorrat") or []


# --- Bedarf ------------------------------------------------------------------------
@dataclass
class Nutzung:
    datum: dt.date          # Koch- bzw. Verzehrtag
    g: float
    wofuer: str
    einfrieren: bool = False


def nutzungen(plan, rezepte):
    """Alle Mengen, die eingekauft werden müssen: Koch-Einträge × faktor × ladungen, plus Extras.
    Reste-Einträge und Auswärts-Mahlzeiten erzeugen keine Zutaten."""
    out = {}
    for e in wp.eintraege(plan):
        if not e.kochen:
            continue
        r = rezepte[e.rezept_id]
        mult = e.faktor * e.ladungen
        txt = f"{wp.tag_kurz(e.datum)[:2]} {config.SLOT_NAMEN[e.slot]}"
        if e.gekocht_am != e.datum:
            txt += f" (vorgekocht {wp.tag_kurz(e.gekocht_am)[:2]})"
        txt += f": {r['name']}" + (f" × {zahl(mult, 2)}" if mult != 1 else "")
        for z in nw.zutaten_eintraege(r):
            if z.get("nicht_mitgerechnet") or z["zutat"] in config.NICHT_EINKAUFEN:
                continue
            out.setdefault(z["zutat"], []).append(Nutzung(e.gekocht_am, z["g"] * mult, txt, e.einfrieren))
    for tag in plan["tage"]:
        d = wp.datum(tag["datum"])
        for x in tag.get("extras") or []:
            out.setdefault(x["zutat"], []).append(Nutzung(d, x["g"], f"{wp.tag_kurz(d)[:2]} Extra"))
    return out


def gesamtbedarf(plan, rezepte):
    """Unabhängig gerechnete Summe aller Rezeptmengen (für die Kontrollrechnung)."""
    summe = 0.0
    for tag in plan["tage"]:
        for slot in config.SLOTS:
            e = tag.get(slot)
            if e and e.get("kochen"):
                mult = float(e.get("faktor", 1.0)) * int(e.get("ladungen", 1))
                summe += sum(z["g"] * mult for z in nw.zutaten_eintraege(rezepte[e["rezept"]])
                             if not z.get("nicht_mitgerechnet") and z["zutat"] not in config.NICHT_EINKAUFEN)
        summe += sum(x["g"] for x in tag.get("extras") or [])
    return summe


# --- Liste ---------------------------------------------------------------------------
@dataclass
class Zeile:
    zutat: str
    bedarf: float
    aus_bestand: float      # aus Vorrat oder Rest eines früheren Einkaufs dieser Woche
    pakete: int
    packung: dict = None
    wofuer: list = field(default_factory=list)
    hinweis: str = ""
    vorrat_unbekannt: bool = False

    @property
    def kauf_g(self):
        return self.pakete * (self.packung["packung_g"] if self.packung else 0)

    @property
    def zu_kaufen(self):
        return self.bedarf - self.aus_bestand

    @property
    def kosten(self):
        if not self.packung or self.packung.get("preis") is None:
            return 0.0
        return self.pakete * self.packung["preis"]

    @property
    def vorratskauf(self):
        return bool(self.packung) and self.packung["haltbar_tage_offen"] >= config.VORRATSKAUF_AB_TAGEN


@dataclass
class Einkaufsliste:
    datum: dt.date
    zeilen: list = field(default_factory=list)


def berechne(plan, rezepte, db, packungen=None, vorrat=None):
    """Listen je Einkaufstermin, Restbestand nach der Woche, Kontrollwerte."""
    packungen = packungen if packungen is not None else wp.lade_packungen()
    vorrat = vorrat if vorrat is not None else lade_vorrat()
    bestand = {}            # zutat → g (math.inf = vorhanden, Menge unbekannt)
    for v in vorrat:
        bestand[v["zutat"]] = math.inf if v.get("g") is None else bestand.get(v["zutat"], 0) + v["g"]
    start_bestand = dict(bestand)
    termine = sorted(wp.datum(e["datum"]) for e in plan.get("einkauf", [])) or [wp.datum(plan["tage"][0]["datum"])]
    listen = {t: Einkaufsliste(t) for t in termine}
    letzte_nutzung = {}

    def termin_fuer(d):
        vorher = [t for t in termine if t <= d]
        return vorher[-1] if vorher else termine[0]

    nutz = nutzungen(plan, rezepte)
    # pro Termin und Zutat zusammenfassen, chronologisch abarbeiten
    je_termin = {}
    for zutat, liste in nutz.items():
        for n in liste:
            je_termin.setdefault((termin_fuer(n.datum), zutat), []).append(n)
            letzte_nutzung[zutat] = max(letzte_nutzung.get(zutat, n.datum), n.datum)
    for (t, zutat), ns in sorted(je_termin.items(), key=lambda x: (x[0][0], x[0][1])):
        bedarf = sum(n.g for n in ns)
        vorhanden = bestand.get(zutat, 0)
        aus_bestand = min(bedarf, vorhanden)
        rest = bedarf - aus_bestand
        pack = packungen.get(zutat)
        pakete = math.ceil(rest / pack["packung_g"] - EPS) if (pack and rest > EPS) else 0
        if vorhanden != math.inf:
            gekauft = pakete * pack["packung_g"] if pack else 0
            bestand[zutat] = vorhanden - aus_bestand + (gekauft - rest if gekauft else 0)
        z = Zeile(zutat, bedarf, aus_bestand, pakete, pack, list(dict.fromkeys(n.wofuer for n in ns)),
                  vorrat_unbekannt=(vorhanden == math.inf))
        z.hinweis = frische_hinweis(zutat, ns, t, db, pack)
        listen[t].zeilen.append(z)

    reste = {}
    for zutat, g in bestand.items():
        if g == math.inf:
            continue
        if g > EPS and zutat in letzte_nutzung:
            pack = packungen.get(zutat)
            haltbar = letzte_nutzung[zutat] + dt.timedelta(days=pack["haltbar_tage_offen"]) if pack else None
            reste[zutat] = {"g": g, "haltbar_bis": haltbar,
                            "tk": bool(pack) and pack["abteilung"] == config.TK_ABTEILUNG,
                            "lange": bool(pack) and pack["haltbar_tage_offen"] >= 365}
    return list(listen.values()), reste


def frische_hinweis(zutat, ns, termin, db, pack):
    typ = db[zutat]["typ"]
    quelle = typ.split("-")[0]
    if quelle not in config.FLEISCH_FISCH:
        return ""
    if pack and pack["abteilung"] == config.TK_ABTEILUNG:
        return "TK, jeweils am Vorabend im Kühlschrank auftauen"
    max_tage = config.FRISCH_MAX_TAGE if (quelle in config.FISCH_GARNELEN or typ.endswith("-hack")) \
        else config.FLEISCH_FRISCH_MAX_TAGE
    einfr = [n for n in ns if n.einfrieren]
    teile = [f"frisch: bis {(termin + dt.timedelta(days=max_tage)).strftime('%d.%m.')} verbrauchen"]
    if einfr:
        teile.append(f"davon {gramm(sum(n.g for n in einfr))} am Einkaufstag portionsweise einfrieren "
                     f"({', '.join(n.wofuer.split(':')[0] for n in einfr)})")
    return "; ".join(teile)


def kontrolle(plan, rezepte, listen):
    """SPEC 12.2: Summe aller Rezeptmengen = Summe der Liste (zu kaufen) + Bestand."""
    soll = gesamtbedarf(plan, rezepte)
    zu_kaufen = sum(z.zu_kaufen for l in listen for z in l.zeilen)
    aus_bestand = sum(z.aus_bestand for l in listen for z in l.zeilen)
    gekauft_ok = all(z.kauf_g + EPS >= z.zu_kaufen or z.packung is None for l in listen for z in l.zeilen)
    return {"rezeptmengen": soll, "zu_kaufen": zu_kaufen, "aus_bestand": aus_bestand,
            "stimmt": abs(soll - (zu_kaufen + aus_bestand)) < 0.01 and gekauft_ok}


# --- Markdown ----------------------------------------------------------------------------
def abteilung(z):
    return z.packung["abteilung"] if z.packung else "Sonstiges"


def kosten(listen, anzahl_teuer=3):
    """Gesamtkosten der Woche: Wochenbedarf, Vorratskäufe (halten lange) und die teuersten Wochenposten."""
    gekauft = [z for l in listen for z in l.zeilen if z.pakete]
    pro_zutat = {}                                     # beide Einkaufstermine zusammen
    for z in gekauft:
        if not z.vorratskauf:
            pro_zutat[z.zutat] = pro_zutat.get(z.zutat, 0.0) + z.kosten
    teuer = sorted(pro_zutat.items(), key=lambda x: -x[1])[:anzahl_teuer]
    return {"woche": sum(z.kosten for z in gekauft if not z.vorratskauf),
            "vorrat": sum(z.kosten for z in gekauft if z.vorratskauf),
            "teuer": [{"zutat": zutat, "kosten": k} for zutat, k in teuer]}


def budget():
    return config.PROFIL["einkauf"].get("budget_eur_pro_woche")


SPAR_WHEY = "Whey in der größeren 2,5-kg-Packung kaufen (online meist 30–40 % günstiger pro kg)"


def einkauf_markdown(plan, rezepte, db, listen, reste):
    budget_eur = budget()
    reihenfolge = config.PROFIL["einkauf"]["abteilungen"]
    out = [f"<!-- Generiert aus daten/wochenplaene/{plan['name']}.yaml – nicht von Hand bearbeiten. -->",
           f"# Einkaufsliste KW {plan['kw']}/{plan['jahr']}", "",
           f"Zum [Wochenplan](../wochenplaene/{plan['name']}.md). Mengen = Bedarf aller Rezepte × Faktor × Ladungen "
           "plus Extras, abzüglich Vorrat, aufgerundet auf Packungen.", ""]
    for liste in listen:
        tag = config.WOCHENTAGE_LANG[liste.datum.weekday()]
        out += [f"## Einkauf {tag}, {liste.datum.strftime('%d.%m.%Y')}", ""]
        kaufen = [z for z in liste.zeilen if z.pakete > 0]
        kosten_abt = {}
        for abt in reihenfolge + sorted({abteilung(z) for z in kaufen} - set(reihenfolge)):
            teil = sorted((z for z in kaufen if abteilung(z) == abt), key=lambda z: z.zutat)
            if not teil:
                continue
            out += [f"### {abt}", ""]
            for z in teil:
                p = z.packung
                menge = f"{p['packung_text']}" if z.pakete == 1 else f"{z.pakete} × {p['packung_text']}"
                bedarf = gramm(z.bedarf)
                if z.aus_bestand > EPS:
                    bedarf += f" (davon {gramm(z.aus_bestand)} schon da)"
                preis = f" · ca. {zahl(z.kosten, 2)} €" if p.get("preis") is not None else ""
                out.append(f"- [ ] **{z.zutat}** · Bedarf {bedarf} → {menge}{preis}")
                out.append(f"  - wofür: {'; '.join(z.wofuer)}")
                if z.hinweis:
                    out.append(f"  - ⚠️ {z.hinweis}")
                key = "vorrat" if z.vorratskauf else "woche"
                kosten_abt.setdefault(abt, {"woche": 0.0, "vorrat": 0.0})[key] += z.kosten
            out.append("")
        # Vorrat prüfen (Vorrat mit unbekannter Menge oder nicht im Sortiment) / schon da (Reste dieser Woche)
        ohne_kauf = [z for z in liste.zeilen if z.pakete == 0]
        pruefen = sorted((z for z in ohne_kauf if z.vorrat_unbekannt or z.packung is None), key=lambda z: z.zutat)
        schon_da = sorted((z for z in ohne_kauf if z not in pruefen), key=lambda z: z.zutat)
        if pruefen:
            out += ["### Vorrat prüfen", "", "Wird aus dem Vorrat genommen – kurz nachsehen, ob genug da ist:", ""]
            for z in pruefen:
                quelle = " (nicht im Sortiment hinterlegt)" if z.packung is None else ""
                out.append(f"- [ ] {z.zutat}: {gramm(z.bedarf)}{quelle} – {'; '.join(z.wofuer)}")
            out.append("")
        if schon_da:
            out += ["### Schon da (Reste aus dem vorherigen Einkauf)", "",
                    ", ".join(f"{z.zutat} {gramm(z.bedarf)}" for z in schon_da), ""]
        # Kosten
        if kosten_abt:
            woche = sum(v["woche"] for v in kosten_abt.values())
            vor = sum(v["vorrat"] for v in kosten_abt.values())
            out += ["### Kostenschätzung", "", "| Abteilung | Wochenbedarf | Vorratskauf (hält lange) |", "|---|---:|---:|"]
            for abt, v in kosten_abt.items():
                out.append(f"| {abt} | {zahl(v['woche'], 2)} € | {zahl(v['vorrat'], 2)} € |")
            out += [f"| **Summe** | **{zahl(woche, 2)} €** | **{zahl(vor, 2)} €** |", ""]
    # Budget
    if budget_eur:
        k = kosten(listen)
        out += ["## Budget", ""]
        out.append(f"Wochenbedarf gesamt ca. **{zahl(k['woche'], 2)} €**, dazu einmalige Vorratskäufe ca. "
                   f"{zahl(k['vorrat'], 2)} € (z. B. Whey, Gewürze, Öl – reichen mehrere Wochen). Budget: {budget_eur} €.")
        if k["woche"] + k["vorrat"] > budget_eur:
            out += ["", f"⚠️ Mit Vorratskäufen über Budget ({zahl(k['woche'] + k['vorrat'], 2)} €)."
                    if k["woche"] <= budget_eur else "⚠️ Schon der Wochenbedarf liegt über dem Budget.",
                    "", "**Sparvorschläge:**"]
            out += [f"- {t['zutat']} ({zahl(t['kosten'], 2)} €): günstigere Alternative im Plan tauschen oder Eigenmarke wählen"
                    for t in k["teuer"]]
            out.append(f"- {SPAR_WHEY}")
        out.append("")
    # Reste
    if reste:
        out += ["## Reste nach der Woche", "", "Werden mit `python3 tools/einkauf.py "
                f"{plan['name']} --reste-uebernehmen` in `daten/vorrat.yaml` eingetragen und nächste Woche bevorzugt verplant.", ""]
        for zutat, r in sorted(reste.items()):
            out.append(f"- {zutat}: {gramm(r['g'])}{rest_hinweis(zutat, r, db)}")
        out.append("")
    # Kontrolle
    k = kontrolle(plan, rezepte, listen)
    out += ["## Kontrollrechnung", "",
            f"Summe aller Rezeptmengen und Extras: {gramm(k['rezeptmengen'])} = zu kaufen {gramm(k['zu_kaufen'])} + "
            f"aus Vorrat/Resten {gramm(k['aus_bestand'])} → **{'stimmt' if k['stimmt'] else 'STIMMT NICHT'}** "
            "(jede Kaufmenge deckt den Bedarf).", "",
            f"*{config.HINWEIS_SCHAETZWERTE} Preise sind Schätzwerte (Discounter, Stand 10/2026).*"]
    return "\n".join(out) + "\n"


def rest_hinweis(zutat, r, db):
    """Haltbarkeit eines Rests; frisches Fleisch/Hack soll eingefroren werden."""
    teile = []
    bis = r.get("haltbar_bis")
    if r.get("lange"):
        teile.append("lange haltbar")
    elif bis:
        teile.append(f"offen haltbar bis {bis.strftime('%d.%m.%Y')}")
    typ = db[zutat]["typ"]
    if typ.split("-")[0] in config.FLEISCH_FISCH and not r.get("tk"):
        teile.append("**sofort einfrieren** oder am Folgetag verbrauchen")
    return (", " + ", ".join(teile)) if teile else ""


def reste_uebernehmen(reste, pfad=config.VORRAT_YAML):
    """Reste nach der Woche in vorrat.yaml eintragen (Mengen addieren, Haltbarkeit setzen)."""
    daten = {"vorrat": lade_vorrat(pfad)}
    idx = {v["zutat"]: v for v in daten["vorrat"]}
    for zutat, r in reste.items():
        if zutat in idx and idx[zutat].get("g") is None:
            continue      # „vorhanden, Menge unbekannt“ bleibt so
        eintrag = idx.setdefault(zutat, {"zutat": zutat, "g": 0})
        if eintrag not in daten["vorrat"]:
            daten["vorrat"].append(eintrag)
        eintrag["g"] = round(r["g"])
        if r["haltbar_bis"]:
            eintrag["haltbar_bis"] = r["haltbar_bis"].isoformat()
    with open(pfad, "w", encoding="utf-8") as f:
        f.write("# Vorrat zu Hause. g: Menge in Gramm, oder null = „vorhanden, Menge unbekannt“.\n")
        yaml.safe_dump(daten, f, allow_unicode=True, sort_keys=False)


def main(argv):
    if not argv:
        sys.exit("Aufruf: python3 tools/einkauf.py KW-45-2026 [--reste-uebernehmen]")
    plan = wp.lade_plan(argv[0])
    db = nw.lade_zutaten()
    rezepte = nw.lade_alle_rezepte()
    listen, reste = berechne(plan, rezepte, db)
    config.AUSGABE_EINKAUF.mkdir(exist_ok=True)
    ziel = config.AUSGABE_EINKAUF / f"{plan['name']}.md"
    ziel.write_text(einkauf_markdown(plan, rezepte, db, listen, reste), encoding="utf-8")
    k = kontrolle(plan, rezepte, listen)
    print(f"{ziel.relative_to(config.WURZEL)} geschrieben · Kontrollrechnung {'stimmt' if k['stimmt'] else 'STIMMT NICHT'}")
    if "--reste-uebernehmen" in argv:
        reste_uebernehmen(reste)
        print(f"{len(reste)} Reste in daten/vorrat.yaml übernommen.")
    return 0 if k["stimmt"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
