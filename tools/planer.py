"""Wochenplan automatisch erstellen (SPEC 8.1 „Woche planen“): regelkonform nach 8.2, ohne Extras, möglichst günstig.

Struktur aus dem Schichtplan (profil.yaml):
  - Abendessen wird mit 2 Ladungen gekocht, die zweite ist am Folgetag das Mittagessen.
  - Vor einer Tagschicht wird mittags doppelt gekocht (zweite Ladung = Abendessen am Schichttag),
    Frühstück, Mittag (Rest vom Vorabend) und Snack für die Schicht werden am Vortag vorbereitet.
  - Nachtschicht: Abendessen und Snack als Box.
  - Gleiches Frühstück/gleicher Snack an 2 Tagen wird einmal mit 2 Ladungen zubereitet.
Die lokale Suche wählt Gerichte und Faktoren; bewertet werden harte Regeln, echte Einkaufskosten
(ganze Packungen je Einkaufstermin) und Bequemlichkeit. Übernommen wird nur ein Plan, den
wochenplan.pruefe_plan ohne Fehler akzeptiert.

Aufruf: python3 tools/planer.py KW-46-2026 [--budget 100] [--starts 24] [--behalten]
  --behalten: Einträge mit „fest: true“ (und Auswärts-Termine) aus der vorhandenen Plandatei bleiben.
"""
import argparse
import datetime as dt
import math
import random
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import einkauf as ek  # noqa: E402
import naehrwerte as nw  # noqa: E402
import wochenplan as wp  # noqa: E402

G = config.PLANER_GEWICHT
HAUPT = ("mittag", "abend")


# --- Woche und Struktur ---------------------------------------------------------------
def woche(name):
    m = re.fullmatch(r"KW-(\d{1,2})-(\d{4})", name)
    if not m:
        raise ValueError(f"Planname „{name}“ – erwartet KW-XX-JJJJ")
    kw, jahr = int(m.group(1)), int(m.group(2))
    montag = dt.date.fromisocalendar(jahr, kw, 1)
    return kw, jahr, [montag + dt.timedelta(i) for i in range(7)]


def einkaufstermine(tage):
    """Einkaufstag(e) aus dem Profil: letzter vor Wochenbeginn + alle innerhalb der Woche."""
    wt = [config.WOCHENTAGE.index(t["tag"]) for t in config.PROFIL["einkauf"]["tage"]]
    vorher = max(tage[0] - dt.timedelta(i) for i in range(1, 8) if (tage[0] - dt.timedelta(i)).weekday() in wt)
    return [vorher] + [d for d in tage if d.weekday() in wt]


def struktur(tage, auswaerts=None):
    """Koch-Slots, Reste-Zuordnung, Boxen und Vorbereitung für Hauptgerichte aus dem Schichtplan."""
    auswaerts = auswaerts or {}
    s = {d: wp.schicht(d) for d in tage}
    koch, rest = [], {}
    for i, d in enumerate(tage):
        vor = tage[i - 1] if i else None
        nach_tag = i + 1 < len(tage) and s[tage[i + 1]] == "Tag"
        for slot in HAUPT:
            if auswaerts.get(d) == slot:
                continue
            if slot == "mittag":
                quelle = (vor, "abend")
                if vor and quelle in koch and not nach_tag and quelle not in rest.values():
                    rest[(d, slot)] = quelle
                    continue
            else:
                quelle = (vor, "mittag")
                if s[d] == "Tag" and vor and quelle in koch and quelle not in rest.values():
                    rest[(d, slot)] = quelle
                    continue
            koch.append((d, slot))
    return {"schicht": s, "koch": koch, "rest": rest}


def kochtag(d, s):
    """Mahlzeiten für die Tagschicht werden am Vortag vorbereitet."""
    return d - dt.timedelta(1) if s[d] == "Tag" else d


# --- Kandidaten und Kosten ---------------------------------------------------------------
class Daten:
    def __init__(self, rezepte=None, db=None, packungen=None, vorrat=None):
        self.db = db or nw.lade_zutaten()
        self.rz = rezepte if rezepte is not None else nw.lade_alle_rezepte()
        self.pk = packungen if packungen is not None else wp.lade_packungen()
        self.vorrat = vorrat if vorrat is not None else ek.lade_vorrat()
        ok = {i: r for i, r in self.rz.items() if ((r.get("bewertung") or {}).get("sterne") or 5) > 2}
        self.fr = sorted(i for i, r in ok.items() if r["mahlzeit"] == "Frühstück" and r["geschmack"] == "süß")
        self.h = sorted(i for i, r in ok.items() if r["mahlzeit"] == "Mittag/Abend")
        self.sn = sorted(i for i, r in ok.items() if r["mahlzeit"] == "Snack")
        self.p = {i: nw.rezept_naehrwerte(r, self.db)["portion"] for i, r in self.rz.items()}
        self.kt = {i: r["aufbewahrung"].get("kuehlschrank_tage") or 0 for i, r in self.rz.items()}
        self.quelle = {i: nw.hauptproteinquelle(r, self.db) for i, r in self.rz.items()}
        self.sterne = {i: (r.get("bewertung") or {}).get("sterne") for i, r in self.rz.items()}
        self.zut = {i: [(z["zutat"], z["g"]) for z in nw.zutaten_eintraege(r)] for i, r in self.rz.items()}
        bekannt = {v["zutat"]: v.get("g") for v in self.vorrat}
        self.bestand = {z: (math.inf if g is None else g) for z, g in bekannt.items()}

    def preis(self, zutat):
        p = self.pk.get(zutat)
        if (not p or p["preis"] is None or zutat in config.NICHT_EINKAUFEN
                or p["haltbar_tage_offen"] >= config.VORRATSKAUF_AB_TAGEN):
            return None
        return p


# --- Bewertung eines Kandidaten -------------------------------------------------------------
class Planer:
    def __init__(self, name, daten=None, budget=None, fest=None, auswaerts=None, termine=None):
        self.name = name
        self.kw, self.jahr, self.tage = woche(name)
        self.d = daten or Daten()
        self.budget = budget if budget is not None else ek.budget()
        self.termine = sorted(termine) if termine else einkaufstermine(self.tage)
        self.start_einkauf = bool(termine) and min(termine) >= self.tage[0]   # einmaliger Einkauf in der Woche
        self.auswaerts = auswaerts or {}                       # datum → Slot
        self.st = struktur(self.tage, self.auswaerts)
        self.fest = fest or {}                                 # (datum, slot) → rezept
        self.ziel = config.TAGESZIELE

    # Mahlzeiten: (datum, slot) → dict(rezept, faktor, kochtag, rest_von, ladungen)
    def mahlzeiten(self, w):
        s, out = self.st["schicht"], {}
        for k in self.st["koch"]:
            out[k] = {"rezept": w["h"][k], "faktor": w["hf"][k], "kochtag": kochtag(k[0], s), "rest_von": None, "ladungen": 1}
        for k, q in self.st["rest"].items():
            out[q]["ladungen"] += 1
            out[k] = {"rezept": w["h"][q], "faktor": w["hf"][q], "kochtag": out[q]["kochtag"], "rest_von": q, "ladungen": 0}
        for slot, wahl, fak in (("fruehstueck", w["fr"], w["ff"]), ("snack", w["sn"], None)):
            offen = {}                                          # (rezept, faktor) → Koch-Eintrag mit freier Ladung
            for d in self.tage:
                r = wahl.get(d)
                if not r:
                    continue
                f = fak[d] if fak else 1.0
                kt = kochtag(d, s)
                q = offen.get((r, f))
                if q and (d - out[q]["kochtag"]).days <= self.d.kt[r]:
                    out[q]["ladungen"] = 2
                    out[(d, slot)] = {"rezept": r, "faktor": f, "kochtag": out[q]["kochtag"], "rest_von": q, "ladungen": 0}
                    del offen[(r, f)]
                else:
                    out[(d, slot)] = {"rezept": r, "faktor": f, "kochtag": kt, "rest_von": None, "ladungen": 1}
                    offen[(r, f)] = (d, slot)
        return out

    def termin(self, tag):
        return 0 if tag < self.termine[-1] or len(self.termine) == 1 else len(self.termine) - 1

    def kosten(self, m):
        menge = {}
        for e in m.values():
            if e["rest_von"]:
                continue
            t = self.termin(e["kochtag"])
            for z, g in self.d.zut[e["rezept"]]:
                menge[(t, z)] = menge.get((t, z), 0.0) + g * e["faktor"] * e["ladungen"]
        summe = 0.0
        for (t, z), g in menge.items():
            p = self.d.preis(z)
            if p is None:
                continue
            if t == 0:
                g -= self.d.bestand.get(z, 0)
            if g > 1e-6:
                summe += math.ceil(g / p["packung_g"] - 1e-9) * p["preis"]
        return summe

    def tageswerte(self, m, d):
        v = {k: 0.0 for k in wp.MAKROS}
        for slot in config.SLOTS:
            e = m.get((d, slot))
            if e:
                for k in v:
                    v[k] += self.d.p[e["rezept"]][k] * e["faktor"]
        if d in self.auswaerts:
            for k in v:
                v[k] += config.AUSWAERTS[k]
        return v

    def strafe(self, w, mit_kosten=True):
        m = self.mahlzeiten(w)
        z, rand, s = self.ziel, config.PLANER_RAND, 0.0
        for d in self.tage:
            v = self.tageswerte(m, d)
            s += G["makro"] * (max(0, config.PLAN_PROTEIN_MIN + rand["protein"] - v["protein"]) * 2
                               + max(0, abs(v["kcal"] - z["kcal"]) - (config.PLAN_KCAL_TOLERANZ - rand["kcal"])) / 10
                               + max(0, max(config.PLAN_FETT_MIN, z["fett"] - config.PLAN_FETT_TOLERANZ) + rand["fett"] - v["fett"])
                               + max(0, v["fett"] - (z["fett"] + config.PLAN_FETT_TOLERANZ - rand["fett"]))
                               + max(0, abs(v["kh"] - z["kh"]) - (config.PLAN_KH_TOLERANZ - rand["kh"])))
            s += 0.02 * abs(v["kcal"] - z["kcal"]) + 0.2 * abs(v["fett"] - z["fett"])
        # Abendessen: Küche und Proteinquelle nicht wie am Vortag
        for a, b in zip(self.tage, self.tage[1:]):
            ea, eb = m.get((a, "abend")), m.get((b, "abend"))
            if ea and eb:
                ra, rb = ea["rezept"], eb["rezept"]
                s += G["regel"] * ((self.d.rz[ra]["kueche"] == self.d.rz[rb]["kueche"]) + (self.d.quelle[ra] == self.d.quelle[rb]))
        # Haltbarkeit, Boxen
        for (d, slot), e in m.items():
            alter = (d - e["kochtag"]).days
            if alter > self.d.kt[e["rezept"]]:
                s += G["regel"] * (alter - self.d.kt[e["rezept"]])
        # Wiederholungen, Bewertungen
        haupt = [w["h"][k] for k in self.st["koch"]]
        s += G["regel"] * sum(max(0, haupt.count(r) - config.PLANER_HAUPT_MAX_KOCHEN) for r in set(haupt))
        for wahl, maxi in ((w["fr"], config.PLANER_FRUEHSTUECK_MAX_TAGE), (w["sn"], config.PLANER_SNACK_MAX_TAGE)):
            werte = [r for r in wahl.values() if r]
            s += G["regel"] * sum(max(0, werte.count(r) - maxi) for r in set(werte))
        drei = {e["rezept"] for e in m.values() if self.d.sterne[e["rezept"]] == 3}
        s += G["regel"] * max(0, len(drei) - config.DREI_STERNE_MAX)
        # Bequemlichkeit
        s += G["faktor"] * (sum(f != 1 for f in w["hf"].values()) + sum(f != 1 for f in w["ff"].values()))
        s += G["snack"] * sum(1 for r in w["sn"].values() if r)
        if mit_kosten:
            k = self.kosten(m)
            s += G["kosten"] * k + G["ueber_budget"] * max(0, k - (self.budget or math.inf))
        return s

    # --- Suche -------------------------------------------------------------------------
    def start(self, rnd):
        fak = config.PLANER_FAKTOREN
        w = {"h": {k: self.fest.get(k) or rnd.choice(self.d.h) for k in self.st["koch"]},
             "hf": {k: rnd.choice(fak) for k in self.st["koch"]},
             "fr": {d: self.fest.get((d, "fruehstueck")) or rnd.choice(self.d.fr) for d in self.tage
                    if self.auswaerts.get(d) != "fruehstueck"},
             "ff": {d: rnd.choice(fak) for d in self.tage},
             "sn": {d: self.fest.get((d, "snack")) or rnd.choice([None] + self.d.sn) for d in self.tage}}
        return w

    def zuege(self, w):
        fak = config.PLANER_FAKTOREN
        out = [("h", k, r) for k in self.st["koch"] if k not in self.fest for r in self.d.h]
        out += [("hf", k, f) for k in self.st["koch"] for f in fak]
        out += [("fr", d, r) for d in w["fr"] if (d, "fruehstueck") not in self.fest for r in self.d.fr]
        out += [("ff", d, f) for d in self.tage for f in fak]
        out += [("sn", d, r) for d in self.tage if (d, "snack") not in self.fest for r in [None] + self.d.sn]
        return out

    def verbessern(self, w, rnd, mit_kosten):
        g = self.strafe(w, mit_kosten)
        besser = True
        while besser:
            besser = False
            zuege = self.zuege(w)
            rnd.shuffle(zuege)
            for teil, k, v in zuege:
                alt = w[teil][k]
                if alt == v:
                    continue
                w[teil][k] = v
                n = self.strafe(w, mit_kosten)
                if n < g - 1e-9:
                    g, besser = n, True
                else:
                    w[teil][k] = alt
        return g

    def suche(self, rnd):
        """Erst regelkonform machen (ohne Kosten), dann mit Kosten weiter verbessern."""
        w = self.start(rnd)
        self.verbessern(w, rnd, mit_kosten=False)
        return self.verbessern(w, rnd, mit_kosten=True), w

    # --- Plan schreiben ---------------------------------------------------------------------
    def plan_dict(self, w):
        m, s = self.mahlzeiten(w), self.st["schicht"]
        boxen = config.SCHICHTEN.get("boxen") or {}
        tage = []
        for d in self.tage:
            tag = {"datum": d}
            for slot in config.SLOTS:
                e = m.get((d, slot))
                if not e:
                    tag[slot] = None
                    continue
                x = {"rezept": e["rezept"]}
                if e["rest_von"]:
                    q = e["rest_von"]
                    x["rest_von"] = f"{q[0].isoformat()}/{q[1]}"
                else:
                    x["kochen"] = True
                if e["faktor"] != 1:
                    x["faktor"] = e["faktor"]
                if e["ladungen"] > 1:
                    x["ladungen"] = e["ladungen"]
                if not e["rest_von"] and e["kochtag"] != d:
                    x["gekocht_am"] = e["kochtag"]
                if not e["rest_von"] and self.einfrieren(e):
                    x["einfrieren"] = True
                if slot in boxen.get(s[d], []) or (slot == "snack" and s[d] in boxen):
                    x["box"] = True
                if (d, slot) in self.fest:
                    x["fest"] = True
                notiz = self.notiz(d, slot, e, m)
                if notiz:
                    x["notiz"] = notiz
                tag[slot] = x
            tag["auswaerts"] = {"mahlzeit": self.auswaerts[d]} if d in self.auswaerts else None
            tage.append(tag)
        return {"kw": self.kw, "jahr": self.jahr, "name": self.name,
                "einkauf": [{"tag": config.WOCHENTAGE[t.weekday()], "datum": t,
                             "art": "start" if self.start_einkauf and t == self.termine[0] else "gross"} for t in self.termine],
                "tage": tage}

    def einfrieren(self, e):
        ek_tag = wp.einkauf_fuer(e["kochtag"], {"einkauf": [{"datum": t} for t in self.termine]})
        return any(art == "frisch" and (e["kochtag"] - ek_tag).days > max_tage
                   for _, art, max_tage in wp.frische_typen(self.d.rz[e["rezept"]], self.d.db, self.d.pk))

    def notiz(self, d, slot, e, m):
        s = self.st["schicht"]
        weiter = [k for k, x in m.items() if x["rest_von"] == (d, slot)]
        if slot in HAUPT and weiter:
            k = weiter[0]
            ziel = f"{config.SLOT_NAMEN[k[1]]} {config.WOCHENTAGE[k[0].weekday()]}"
            if s[d] == "Nacht" and slot == "abend":
                return f"nachmittags mitkochen, Box für die Nacht; zweite Ladung = {ziel}"
            return f"zweite Ladung = {ziel}"
        if s[d] == "Nacht" and slot == "mittag" and not e["rest_von"]:
            return "vor der Schicht"
        return None

    def yaml_text(self, plan, kosten):
        s = self.st["schicht"]
        kurz = " · ".join(f"{config.WOCHENTAGE[d.weekday()]} {s[d]}" for d in self.tage)
        prep = [config.WOCHENTAGE[(d - dt.timedelta(1)).weekday()] + " " + (d - dt.timedelta(1)).strftime("%d.%m.")
                for d in self.tage if s[d] == "Tag" and d > self.tage[0]]
        kopf = [f"# Wochenplan KW {self.kw}/{self.jahr} ({wp.tag_kurz(self.tage[0])} – {wp.tag_kurz(self.tage[-1])})",
                f"# Schichten (aus profil.yaml): {kurz}",
                f"# Meal-Prep-Tag: {', '.join(prep) or '–'} (Vorbereitung für die Tagschicht)",
                f"# Erstellt mit tools/planer.py · Einkauf ca. {nw.zahl(kosten, 2)} € (Budget {self.budget} €)",
                f"kw: {plan['kw']}", f"jahr: {plan['jahr']}", "einkauf:"]
        kopf += [f"  - {{tag: {e['tag']}, datum: {e['datum'].isoformat()}, art: {e['art']}}}" for e in plan["einkauf"]]
        kopf.append("tage:")
        for tag in plan["tage"]:
            d = tag["datum"]
            info = f"{s[d]}schicht {config.SCHICHTEN['zeiten'][s[d]]}" if s[d] != "frei" else "frei"
            kopf.append(f"  - datum: {d.isoformat()}          # {info}")
            for slot in config.SLOTS:
                kopf.append(f"    {slot}: {eintrag_text(tag[slot])}")
            kopf.append(f"    auswaerts: {eintrag_text(tag['auswaerts'])}")
        return "\n".join(kopf) + "\n"

    # --- Gesamtlauf --------------------------------------------------------------------------
    def planen(self, starts=None, seed=None, ausgabe=None):
        rnd = random.Random(config.PLANER_SEED if seed is None else seed)
        kandidaten = []
        for i in range(starts or config.PLANER_STARTS):
            g, w = self.suche(rnd)
            plan = self.plan_dict(w)
            pr = wp.pruefe_plan(plan, self.d.rz, self.d.db, self.d.pk)
            listen, _ = ek.berechne(plan, self.d.rz, self.d.db, self.d.pk, self.d.vorrat)
            k = ek.kosten(listen)
            kandidaten.append((len(pr.fehler), k["woche"], i, plan, k, pr))
            if ausgabe:
                ausgabe(f"Start {i + 1}: {len(pr.fehler)} Fehler, Einkauf {nw.zahl(k['woche'], 2)} €")
        kandidaten.sort(key=lambda x: (x[0], x[1]))
        return kandidaten[0]


def eintrag_text(x):
    if not x:
        return "null"
    teile = []
    for k, v in x.items():
        if isinstance(v, bool):
            v = "true" if v else "false"
        elif isinstance(v, dt.date):
            v = v.isoformat()
        elif isinstance(v, float):
            v = f"{v:g}"
        elif isinstance(v, str) and (" " in v or ":" in v or "=" in v or ";" in v):
            v = '"' + v.replace('"', "'") + '"'
        teile.append(f"{k}: {v}")
    return "{" + ", ".join(teile) + "}"


def vorgaben(pfad):
    """Feste Einträge und Auswärts-Termine aus einer vorhandenen Plandatei (--behalten)."""
    if not pfad.exists():
        return {}, {}
    plan = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    fest, aus = {}, {}
    for tag in plan.get("tage", []):
        d = wp.datum(tag["datum"])
        for slot in config.SLOTS:
            e = tag.get(slot)
            if e and e.get("fest"):
                fest[(d, slot)] = e["rezept"]
        if tag.get("auswaerts"):
            aus[d] = tag["auswaerts"].get("mahlzeit", "abend")
    return fest, aus


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("plan")
    a.add_argument("--budget", type=float, default=None)
    a.add_argument("--starts", type=int, default=None)
    a.add_argument("--behalten", action="store_true")
    a.add_argument("--einkauf", nargs="+", type=dt.date.fromisoformat, default=None,
                   help="Einkaufstermine (JJJJ-MM-TT) statt der Samstage aus dem Profil, z. B. Starteinkauf")
    args = a.parse_args(argv)
    pfad = config.WOCHENPLAENE_DIR / f"{args.plan}.yaml"
    fest, aus = vorgaben(pfad) if args.behalten else ({}, {})
    p = Planer(args.plan, budget=args.budget, fest=fest, auswaerts=aus, termine=args.einkauf)
    fehler, kosten, _, plan, k, pr = p.planen(args.starts, ausgabe=print)
    if fehler:
        print(f"Kein regelkonformer Plan gefunden (bester: {fehler} Fehler) – nichts geschrieben:")
        for f in pr.fehler:
            print("  ✗", f)
        return 1
    pfad.write_text(p.yaml_text(plan, kosten), encoding="utf-8")
    print(f"{pfad.relative_to(config.WURZEL)} geschrieben · Einkauf ca. {nw.zahl(k['woche'], 2)} € "
          f"(Budget {p.budget} €), Vorratskäufe {nw.zahl(k['vorrat'], 2)} €")
    return 0


if __name__ == "__main__":
    sys.exit(main())
