from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
import os

import requests
from PySide6.QtCore import QThread, Signal

from lawmate_app.config import AppConfig


def _ollama_api_url(base_url: str, endpoint: str) -> str:
    base = base_url.rstrip('/')
    if base.endswith('/api'):
        return f"{base}{endpoint}"
    return f"{base}/api{endpoint}"


@dataclass
class OllamaSetupResult:
    ok: bool
    message: str


def _find_ollama_cli() -> str | None:
    """Try to find ollama CLI executable.

    On Windows, PATH may not be set correctly. We also try common install locations.
    """
    # 1) Standard PATH lookup
    path = shutil.which("ollama")
    if path:
        return path

    # 2) Optional env override
    env_path = os.getenv("OLLAMA_CLI_PATH", "").strip()
    if env_path and Path(env_path).exists():
        return env_path

    # 3) Common Windows install paths (best-effort)
    candidates: list[Path] = []
    program_files = os.getenv("ProgramFiles", "")
    if program_files:
        candidates.append(Path(program_files) / "Ollama" / "ollama.exe")

    local_app_data = os.getenv("LOCALAPPDATA", "")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe")

    for c in candidates:
        if c.exists():
            return str(c)

    return None


def _is_ollama_cli_available() -> bool:
    return _find_ollama_cli() is not None


def _ollama_api_tags(base_url: str, timeout: float = 2.0) -> dict:
    """Call Ollama /api/tags and return json or raise."""
    url = base_url.rstrip("/") + "/api/tags"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _ollama_model_exists(base_url: str, model_name: str) -> bool:
    try:
        data = _ollama_api_tags(base_url, timeout=2.0)
        models = data.get("models", [])
        for m in models:
            name = (m.get("name") or "").strip().lower()
            if name == model_name.strip().lower():
                return True
        return False
    except Exception:
        return False


def _try_start_ollama_server() -> bool:
    """Try to start Ollama server in background.

    On Windows, Ollama is usually installed as a background app/service.
    This is a best-effort helper (won't crash if it fails).
    """
    cli = _find_ollama_cli()
    if not cli:
        return False

    try:
        # Best-effort: start server (if already running, this may exit quickly)
        creationflags = 0
        try:
            # Hide console on Windows
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        except Exception:
            creationflags = 0

        subprocess.Popen(
            [cli, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        return True
    except Exception:
        return False



def ensure_ollama_ready(cfg: AppConfig, progress_cb=None) -> OllamaSetupResult:
    """Ensure Ollama is reachable.

    Local mode (localhost):
      - If server isn't reachable, tries to start it.
      - If model is missing, runs `ollama pull <model>`.

    Cloud mode (ollama.com):
      - Requires OLLAMA_API_KEY (Bearer token).
      - No local server / no model download needed.
      - Only checks connectivity via /api/tags.
    """

    base_url = cfg.ollama_base_url.strip()
    model = cfg.ollama_model.strip()
    api_key = getattr(cfg, "ollama_api_key", "").strip()

    def log(line: str) -> None:
        if progress_cb:
            progress_cb(line)

    is_cloud = "ollama.com" in base_url.lower()

    if is_cloud:
        if not api_key:
            return OllamaSetupResult(
                ok=False,
                message=(
                    "Používáš Ollama Cloud (ollama.com), ale chybí OLLAMA_API_KEY v .env.\n"
                    "Vytvoř API key na ollama.com a vlož ho do .env jako OLLAMA_API_KEY=...\n"
                    "Pak restartuj aplikaci."
                ),
            )

        try:
            log("Kontroluji připojení k Ollama Cloud…")
            url = _ollama_api_url(base_url, "/tags")
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                return OllamaSetupResult(
                    ok=False,
                    message=f"Ollama Cloud vrací {resp.status_code}: {resp.text[:300]}",
                )
            # Optional: basic model availability hint
            log("✅ Ollama Cloud je dostupná.")
            return OllamaSetupResult(ok=True, message=f"Ollama Cloud připravena (model: {model}).")
        except Exception as e:
            return OllamaSetupResult(
                ok=False,
                message=f"Nelze se připojit k Ollama Cloud: {type(e).__name__}: {e}",
            )

    # --- Local Ollama (localhost) ---
    cli = _find_ollama_cli()
    if not cli:
        return OllamaSetupResult(
            ok=False,
            message=(
                "Ollama není nainstalovaná nebo ji nemohu najít.\n"
                "Nainstaluj Ollama pro Windows a zkus to znovu."
            ),
        )

    # 1) Check server
    try:
        log("Kontroluji Ollama server…")
        resp = requests.get(_ollama_api_url(base_url, "/tags"), timeout=5)
        if resp.status_code == 200:
            log("✅ Server běží.")
        else:
            raise RuntimeError(f"Server vrací {resp.status_code}")
    except Exception:
        log("Server neběží, zkouším spustit…")
        ok = _start_ollama_server(cli)
        if not ok:
            return OllamaSetupResult(ok=False, message="Nepodařilo se spustit Ollama server.")
        # wait a moment
        time.sleep(1.5)
        try:
            resp = requests.get(_ollama_api_url(base_url, "/tags"), timeout=10)
            if resp.status_code != 200:
                return OllamaSetupResult(ok=False, message="Ollama server neběží ani po spuštění.")
        except Exception:
            return OllamaSetupResult(ok=False, message="Ollama server je nedostupný.")

    # 2) Check model presence
    try:
        data = requests.get(_ollama_api_url(base_url, "/tags"), timeout=10).json()
        models = [m.get("name", "") for m in data.get("models", [])]
        if model not in models:
            log(f"Model '{model}' není stažený, stahuji…")
            subprocess.check_call([cli, "pull", model])
            log("✅ Model stažen.")
        else:
            log("✅ Model už je k dispozici.")
    except Exception as e:
        return OllamaSetupResult(
            ok=False,
            message=(
                "Nepodařilo se ověřit/stáhnout model automaticky.\n"
                f"Chyba: {type(e).__name__}: {e}"
            ),
        )

    return OllamaSetupResult(ok=True, message=f"Ollama připravena (model: {model}).")


    log(f"Chybí model {model} – stahuji… (může to trvat)")

    try:
        # Pull model (this can take minutes depending on network / disk)
        proc = subprocess.Popen(
            [cli, "pull", model],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if line:
                log(line)
        code = proc.wait()
        if code != 0:
            return OllamaSetupResult(
                ok=False,
                message=(
                    f"Stažení modelu selhalo (exit code {code}).\n"
                    "Zkus otevřít terminál a spustit: "
                    f"ollama pull {model}"
                ),
            )

        # Re-check existence
        if _ollama_model_exists(base_url, model):
            return OllamaSetupResult(ok=True, message=f"Model {model} byl stažen a je připraven.")

        return OllamaSetupResult(
            ok=False,
            message=(
                "Model se po stažení neobjevil v seznamu.\n"
                "Zkus aplikaci restartovat nebo změnit OLLAMA_MODEL v .env."
            ),
        )
    except Exception as e:
        return OllamaSetupResult(
            ok=False,
            message=(
                "Nepodařilo se stáhnout model automaticky.\n"
                f"Chyba: {type(e).__name__}: {e}"
            ),
        )


class OllamaSetupWorker(QThread):
    """Runs Ollama setup in a background thread so the UI doesn't freeze."""

    progress = Signal(str)
    finished_ok = Signal(str)
    finished_error = Signal(str)

    def __init__(self, cfg: AppConfig):
        super().__init__()
        self.cfg = cfg

    def run(self) -> None:
        res = ensure_ollama_ready(self.cfg, progress_cb=self.progress.emit)
        if res.ok:
            self.finished_ok.emit(res.message)
        else:
            self.finished_error.emit(res.message)
