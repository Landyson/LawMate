from __future__ import annotations

import json
import requests
from lawmate_app.config import AppConfig
from lawmate_app.models import LawmateAnswer

def _ollama_api_url(base_url: str, endpoint: str) -> str:
    """Build a correct Ollama API URL for both local and cloud hosts.

    - local base_url example: http://localhost:11434
    - cloud base_url example: https://ollama.com or https://ollama.com/api
    """
    base = base_url.rstrip("/")
    if base.endswith("/api"):
        return f"{base}{endpoint}"
    return f"{base}/api{endpoint}"


class LLMError(RuntimeError):
    pass

class BaseLLMProvider:
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> LawmateAnswer:
        raise NotImplementedError

class MockProvider(BaseLLMProvider):
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> LawmateAnswer:
        data = {
            "traffic_light": "yellow",
            "risk_score": 45,
            "summary": "Z toho, co píšeš, to vypadá na běžný právní problém, který jde často vyřešit domluvou nebo správným postupem. U detailů ale záleží na dokumentech a termínech.",
            "what_to_do_now": [
                "Sepiš si časovou osu (kdy se co stalo).",
                "Schovej důkazy (smlouvy, screenshoty, fotky).",
                "Komunikuj pokud možno písemně."
            ],
            "what_to_prepare": [
                "Kopie smluv / objednávek / faktur.",
                "Doklad o platbě (výpis, potvrzení).",
                "Kontakty na svědky, pokud existují."
            ],
            "relevant_laws": [
                "Občanský zákoník (zákon č. 89/2012 Sb.) – obecně závazky a smlouvy"
            ],
            "important_deadlines": ["Nejsem si jistý bez detailů (záleží na typu věci)."],
            "when_to_contact_lawyer": [
                "Když hrozí soud / exekuce nebo vysoká částka.",
                "Když protistrana ignoruje výzvy nebo vyhrožuje."
            ],
            "notes": [
                "Neber to jako právní stanovisko – je to orientační pomoc.",
                "U lhůt to raději neodkládej."
            ],
            "sources": []
        }
        return LawmateAnswer.model_validate(data)

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, cfg: AppConfig):
        if not cfg.openai_api_key:
            raise LLMError("OPENAI_API_KEY chybí v .env")
        self.api_key = cfg.openai_api_key
        self.model = cfg.openai_model

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> LawmateAnswer:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            raise LLMError(f"OpenAI API error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return LawmateAnswer.model_validate(parsed)

class OllamaProvider(BaseLLMProvider):
    def __init__(self, cfg: AppConfig):
        self.base_url = cfg.ollama_base_url.strip()
        self.api_key = cfg.ollama_api_key.strip() if hasattr(cfg, 'ollama_api_key') else ''
        self.model = cfg.ollama_model

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> LawmateAnswer:
        url = _ollama_api_url(self.base_url, "/chat")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": temperature},
            "stream": False,
        }
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        if resp.status_code != 200:
            raise LLMError(f"Ollama error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        content = data.get("message", {}).get("content", "")
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMError("Ollama nevrátil JSON. Zkus jiný model.")
        parsed = json.loads(content[start:end+1])
        return LawmateAnswer.model_validate(parsed)

def make_provider(cfg: AppConfig) -> BaseLLMProvider:
    if cfg.llm_provider == "openai":
        return OpenAIProvider(cfg)
    if cfg.llm_provider == "ollama":
        return OllamaProvider(cfg)
    return MockProvider()
