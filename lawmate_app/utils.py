from __future__ import annotations

import re
from typing import List

_CZ_STOPWORDS = set("""
a aby ať ale ani ano až be bez bude budou byl byla byli byste bych bychom bys by
co do kdo kde když které která které který
je jeho její jen ještě jestli jsem jsme jste jsou
k ke komu kolik kolem ku kvůli kde která které který když
na nad nebo než ni nic
o od okolo pak po pod podle protože proti pro
se si s spolu stejně svůj své svého svým svémi
ta tak taky tam tady ten tento to tu tuto
u už v ve vám vás vy váš vaše
z za ze že
""".split())

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())

def extract_keywords(text: str, max_keywords: int = 12) -> List[str]:
    text = normalize_text(text).lower()
    words = re.findall(r"[a-zá-ž0-9]{3,}", text, flags=re.IGNORECASE)
    words = [w for w in words if w not in _CZ_STOPWORDS]
    seen=set()
    out=[]
    for w in words:
        if w in seen:
            continue
        seen.add(w)
        out.append(w)
        if len(out) >= max_keywords:
            break
    return out

def traffic_light_from_score(score: int) -> str:
    if score >= 70:
        return "red"
    if score >= 35:
        return "yellow"
    return "green"


def infer_category(user_text: str) -> str:
    """Heuristicky odhadne oblast práva podle textu (rychlé + offline).

    Vrací jeden z oficiálních názvů kategorií:
    - "Trestní právo"
    - "Občanské právo"
    - "Právní řád ČR (obecně)"
    """
    t = normalize_text(user_text).lower()

    trest_terms = [
        "policie", "trestní", "trestný", "trestní oznámení", "obviněn", "obžaloba", "výpověď",
        "zadržení", "předvolání", "soud", "státní zástupce", "kriminálka",
        "napadení", "ublížení", "násilí", "vyhrožuje", "vydírání",
        "krádež", "loupež", "podvod", "drogy", "alkohol", "řízení pod vlivem",
        "vražda", "zavraždil", "zabil", "smrt", "usmrcení",
    ]
    obc_terms = [
        "smlouva", "faktura", "nezaplatil", "neplatí", "dluh", "půjčka", "peníze",
        "žaloba", "výzva k úhradě", "náhrada škody", "škoda",
        "reklamace", "vrácení", "záruka", "spotřebitel",
        "pronájem", "nájem", "kauce", "soused", "plot", "hluk",
        "rozvod", "dědictví", "opatrovnictví", "péče o dítě",
        "zaměstnavatel", "výpověď z práce", "pracovní smlouva",
    ]
    legal_terms = [
        "jaký je zákon", "jaký zákon platí", "paragraf", "sbírka", "ústav",
        "jak to říká zákon", "co říká zákon", "právní předpis", "vyhláška",
        "judikatura", "nejvyšší soud", "nss", "ústavní soud",
    ]

    def score_for(terms: list[str]) -> int:
        sc = 0
        for term in terms:
            if term in t:
                sc += 2
        return sc

    scores = {
        "Trestní právo": score_for(trest_terms),
        "Občanské právo": score_for(obc_terms),
        "Právní řád ČR (obecně)": score_for(legal_terms),
    }

    # fallback: pokud není nic jasného, ber "Právní řád..." (obecné dotazy)
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        return "Právní řád ČR (obecně)"
    return best


def heuristic_risk_score(user_text: str, category: str) -> int:
    t = user_text.lower()
    score = 10

    red_terms = [
        "policie", "trestní oznámení", "obviněn", "obžaloba", "výpověď", "zadržení",
        "soud", "exekuce", "předvolání", "insolvence", "správní řízení",
        "vyhrožuje", "násilí", "napadení", "ublížení", "zabil", "vražda", "usmrcení", "krádež", "podvod",
        "dluh", "žaloba", "výzva k úhradě"
    ]
    yellow_terms = [
        "smlouva", "výpověď", "reklamace", "vrácení", "pokuta", "náhrada škody",
        "pronájem", "nájem", "rozvod", "dědictví", "dohoda", "zaměstnavatel",
        "odstoupení", "půjčka"
    ]

    for term in red_terms:
        if term in t:
            score += 30

    for term in yellow_terms:
        if term in t:
            score += 15

    money = re.findall(r"\b(\d{1,3}(?:[ .]\d{3})+|\d{4,})\b", t)
    if money:
        score += 15

    if "do zítra" in t or "dnes" in t or "lhůt" in t:
        score += 15

    if category.lower().startswith("trest"):
        score += 10

    return min(score, 100)
