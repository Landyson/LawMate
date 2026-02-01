from __future__ import annotations

import requests
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Dict, Any

from lawmate_app.utils import extract_keywords, normalize_text

BASE = "https://rozhodnuti.justice.cz/api"

@dataclass
class JusticeDecision:
    jednaci_cislo: str
    soud: str
    predmet_rizeni: str
    datum_vydani: str
    datum_zverejneni: str
    klicova_slova: List[str]
    zminena_ustanoveni: List[str]
    odkaz: str
    score: float

def _safe_get_json(url: str, timeout: int = 30) -> Any:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()

def fetch_day(year: int, month: int, day: int, page: int = 0) -> Dict[str, Any]:
    return _safe_get_json(f"{BASE}/opendata/{year}/{month}/{day}?page={page}")

def search_recent_decisions(question: str, lookback_days: int = 14, max_items_per_day: int = 200) -> List[JusticeDecision]:
    keywords = extract_keywords(question)
    if not keywords or lookback_days <= 0:
        return []

    today = date.today()
    candidates: List[JusticeDecision] = []

    for i in range(lookback_days):
        d = today - timedelta(days=i)
        try:
            data = fetch_day(d.year, d.month, d.day, page=0)
        except Exception:
            continue

        items = data.get("items", [])
        if not isinstance(items, list):
            continue

        items = items[:max_items_per_day]

        for it in items:
            predmet = normalize_text(str(it.get("predmetRizeni", "")))
            klic = it.get("klicovaSlova", []) or []
            ust = it.get("zminenaUstanoveni", []) or []
            blob = " ".join([predmet] + [str(x) for x in klic] + [str(x) for x in ust]).lower()

            overlap = sum(1 for kw in keywords if kw in blob)
            if overlap == 0:
                continue

            score = overlap / max(len(keywords), 1)

            candidates.append(
                JusticeDecision(
                    jednaci_cislo=str(it.get("jednaciCislo", "")),
                    soud=str(it.get("soud", "")),
                    predmet_rizeni=predmet,
                    datum_vydani=str(it.get("datumVydani", "")),
                    datum_zverejneni=str(it.get("datumZverejneni", "")),
                    klicova_slova=[str(x) for x in klic][:10],
                    zminena_ustanoveni=[str(x) for x in ust][:10],
                    odkaz=str(it.get("odkaz", "")),
                    score=float(score),
                )
            )

    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates[:5]

def decisions_to_sources(decisions: List[JusticeDecision]) -> List[Dict[str, str]]:
    sources=[]
    for d in decisions:
        title = f"{d.soud} – {d.jednaci_cislo} ({d.datum_vydani})"
        why = f"Předmět řízení: {d.predmet_rizeni}. Klíčová slova: {', '.join(d.klicova_slova[:5])}."
        sources.append({"title": title, "url": d.odkaz, "why_relevant": why})
    return sources
