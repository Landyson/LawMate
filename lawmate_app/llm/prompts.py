from __future__ import annotations

SYSTEM_BASE = (
    "Jsi Lawmate – AI právní asistent pro laiky v České republice.\n"
    "Cíl: pomoci uživateli se zorientovat (ne dávat závazné právní stanovisko).\n\n"
    "DŮLEŽITÉ:\n"
    "- NIKDY netvrď, že jsi advokát. Nejde o právní službu.\n"
    "- Pokud hrozí škoda, trestní řízení, soud, exekuce, vysoké částky nebo krátké lhůty, "
    "zvedni riziko a doporuč právníka.\n"
    "- Vysvětluj jednoduše (jako pro neznalce).\n"
    "- Pokud si nejsi jistý, řekni to a napiš co ověřit.\n"
    "- Nepiš žádné osobní údaje (anonymizace).\n"
)

def make_user_prompt(category: str, question: str, sources_block: str) -> str:
    return f"""Oblast: {category}

Uživatelův dotaz:
{question}

Dostupné zdroje / judikatura (může být prázdné):
{sources_block}

Vrať odpověď ve STRIKTNÍM JSON podle této struktury:
{{
  "traffic_light": "green|yellow|red",
  "risk_score": 0-100,
  "summary": "krátké shrnutí v češtině (2-4 věty)",
  "what_to_do_now": ["kroky hned teď", "..."],
  "what_to_prepare": ["co si připravit (smlouvy, fotky, svědci...)", "..."],
  "relevant_laws": ["zákon č. ... Sb., § ...", "..."],
  "important_deadlines": ["lhůty / termíny (pokud nevíš, napiš 'nejsem si jistý')", "..."],
  "when_to_contact_lawyer": ["konkrétní situace kdy už je vhodný advokát", "..."],
  "notes": ["upozornění, nejčastější chyby", "..."],
  "sources": [
    {{
      "title": "název",
      "url": "https://...",
      "why_relevant": "proč je to relevantní"
    }}
  ]
}}
"""
