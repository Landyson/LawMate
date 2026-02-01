# Lawmate (PC aplikace – právní poradce s AI)

**Lawmate** je jednoduchá desktop aplikace (Windows), která pomáhá laikům zorientovat se v právních otázkách.
Aplikace **nenahrazuje advokáta**, ale dá:
- srozumitelné vysvětlení situace,
- doporučené kroky,
- upozornění na rizika a lhůty,
- „semafor“ (zelená / žlutá / červená),
- orientační odkazy na judikaturu (Opendata rozhodnutí justice.cz).

## Funkce
- 3 oblasti: **Trestní**, **Občanské**, **Právní řád ČR (obecně)**
- Chat + historie uživatele (SQLite)
- Semafor rizikovosti odpovědi
- Doporučení „kdy už jít k právníkovi“
- Tlačítko „Najít advokáta“ (ČAK vyhledávač)
- Podpora AI providerů:
  - **OpenAI** (API klíč)
  - **Ollama** (lokální model) – při prvním spuštění se aplikace pokusí:
    - zkontrolovat, že běží Ollama server,
    - a pokud chybí model, automaticky spustí `ollama pull ...`.
  - **Mock režim** (funguje i bez klíče – pro demo)
 
## Spuštění (uživatel)
- otevřete složku /dist/Lawmate zde naleznete Lawmate.exe to otevřte a tímto máte spuštěného právního chatbota

## Spuštění (vývoj)
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```


## Nastavení AI (doporučeno: Ollama Cloud bez stahování modelu)

1) Zkopíruj `.env.example` -> `.env`
```bash
copy .env.example .env
```

2) Otevři `.env` a vyber jednu variantu:

### Varianta A – Ollama Cloud (bez stahování modelů do PC) ✅
Vyžaduje **Ollama API key** z ollama.com.

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=https://ollama.com/api
OLLAMA_API_KEY=SEM_VLOZ_TVŮJ_KLÍČ
OLLAMA_MODEL=gpt-oss:20b
```

### Varianta B – Ollama lokálně (model běží na tvém PC)
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_API_KEY=
OLLAMA_MODEL=qwen3:8b
```

### Varianta C – OpenAI API
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=SEM_VLOZ_TVŮJ_KLÍČ
OPENAI_MODEL=gpt-4o-mini
```

Potom aplikaci spusť znovu.

## Build do EXE (Windows)
```bash
pip install pyinstaller
pyinstaller --noconsole --onedir --name Lawmate main.py
```

Výstup je ve `dist/Lawmate/`.

## Poznámky k právním zdrojům
- MVP vyhledává v otevřených datech rozhodnutí (rozhodnuti.justice.cz) v posledních N dnech.
- Přímé načítání plných znění zákonů přes e‑Sbírku / ELI je připravené na rozšíření.

## Licence
Pro školní použití (uprav dle potřeby).
