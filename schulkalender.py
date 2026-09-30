"""Schulkalender Schleswig-Holstein: Unterrichtstage, Ferien, Feiertage."""
import json
from datetime import date, timedelta
from pathlib import Path

from dateutil.easter import easter

_DATEI = Path(__file__).parent / "ferien_sh.json"


def lade_ferien() -> dict:
    with open(_DATEI, encoding="utf-8") as f:
        return json.load(f)


def feiertage_sh(jahr: int) -> dict:
    """Gesetzliche Feiertage in Schleswig-Holstein."""
    o = easter(jahr)
    return {
        date(jahr, 1, 1): "Neujahr",
        o - timedelta(days=2): "Karfreitag",
        o + timedelta(days=1): "Ostermontag",
        date(jahr, 5, 1): "Tag der Arbeit",
        o + timedelta(days=39): "Christi Himmelfahrt",
        o + timedelta(days=50): "Pfingstmontag",
        date(jahr, 10, 3): "Tag der Deutschen Einheit",
        date(jahr, 10, 31): "Reformationstag",
        date(jahr, 12, 25): "1. Weihnachtstag",
        date(jahr, 12, 26): "2. Weihnachtstag",
    }


def _d(s: str) -> date:
    return date.fromisoformat(s)


def finde_schuljahr(tag: date, daten: dict):
    for name, sj in daten["schuljahre"].items():
        if _d(sj["beginn"]) <= tag <= _d(sj["ende"]):
            return name, sj
    return None, None


def freie_tage(sj: dict, zusatz: list[date] | None = None) -> dict:
    """Alle unterrichtsfreien Tage (außer Wochenenden) eines Schuljahres."""
    frei = {}
    for name, von, bis in sj["ferien"]:
        t = _d(von)
        while t <= _d(bis):
            frei[t] = name
            t += timedelta(days=1)
    for jahr in {_d(sj["beginn"]).year, _d(sj["ende"]).year}:
        frei.update(feiertage_sh(jahr))
    for t in zusatz or []:
        frei[t] = "Schulinterner freier Tag"
    return frei


def ist_unterrichtstag(t: date, frei: dict) -> bool:
    return t.weekday() < 5 and t not in frei


def schuljahr_info(tag: date, zusatz: list[date] | None = None) -> dict:
    """Wo im Schuljahr liegt das Datum? Grundlage für die Themen-Schätzung."""
    daten = lade_ferien()
    name, sj = finde_schuljahr(tag, daten)
    if not sj:
        return {"gefunden": False}

    frei = freie_tage(sj, zusatz)
    beginn, ende = _d(sj["beginn"]), _d(sj["ende"])

    bisher, gesamt = 0, 0
    t = beginn
    while t <= ende:
        if ist_unterrichtstag(t, frei):
            gesamt += 1
            if t < tag:
                bisher += 1
        t += timedelta(days=1)

    hj2_start = date(beginn.year + 1, 2, 1)
    hj_beginn = beginn if tag < hj2_start else hj2_start
    hj_ende = hj2_start - timedelta(days=1) if tag < hj2_start else ende
    hj_bisher = hj_gesamt = 0
    t = hj_beginn
    while t <= hj_ende:
        if ist_unterrichtstag(t, frei):
            hj_gesamt += 1
            if t < tag:
                hj_bisher += 1
        t += timedelta(days=1)

    # Letzte Ferien vor dem Datum (relevant: nach Ferien wird oft wiederholt)
    letzte = None
    for fname, von, bis in sj["ferien"]:
        if _d(bis) < tag:
            letzte = (fname, _d(bis))
    tage_seit_ferien = None
    if letzte:
        tage_seit_ferien = sum(
            1 for i in range((tag - letzte[1]).days)
            if ist_unterrichtstag(letzte[1] + timedelta(days=i + 1), frei)
            and letzte[1] + timedelta(days=i + 1) < tag
        )

    return {
        "gefunden": True,
        "schuljahr": name,
        "unterrichtstag": ist_unterrichtstag(tag, frei),
        "grund_frei": frei.get(tag, "Wochenende" if tag.weekday() >= 5 else None),
        "tage_bisher": bisher,
        "tage_gesamt": gesamt,
        "anteil": bisher / gesamt if gesamt else 0,
        "wochen_bisher": round(bisher / 5, 1),
        "halbjahr": 1 if tag < hj2_start else 2,
        "hj_tage_bisher": hj_bisher,
        "hj_tage_gesamt": hj_gesamt,
        "letzte_ferien": letzte[0] if letzte else None,
        "unterrichtstage_seit_ferien": tage_seit_ferien,
    }
