"""Cliente Kokoro TTS — texto em áudio (OpenAI-compatible /api/v1/audio/speech)."""

from __future__ import annotations

from pathlib import Path

import httpx

from app.config import PROJECT_ROOT, Settings
from app.logging_config import get_logger

logger = get_logger(__name__)

AUDIO_DIR = PROJECT_ROOT / "data" / "results" / "audio"


def _prepare_speech_text(text: str, max_chars: int = 700) -> str:
    """Prefere a seção RESUMO; limita tamanho para TTS rápido no CPU."""
    raw = (text or "").strip()
    upper = raw.upper()
    start = 0
    for marker in ("RESUMO:", "RESUMO\n", "SUMMARY:"):
        idx = upper.find(marker)
        if idx >= 0:
            start = idx + len(marker)
            break
    rest = raw[start:].strip()
    for stop in ("\nINDICADORES", "\nALERTAS", "\nRECOMENDA", "\nLIMITA"):
        idx = rest.upper().find(stop)
        if idx > 0:
            rest = rest[:idx]
            break
    speech = " ".join(rest.split())
    if not speech:
        speech = " ".join(raw.split())
    return speech[:max_chars]


class TTSClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.kokoro_base_url.rstrip("/")
        self.enabled = settings.kokoro_enabled
        self.voice = settings.kokoro_voice
        self.timeout = settings.kokoro_timeout_seconds

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            with httpx.Client(timeout=3.0) as client:
                # Kokoro FastAPI costuma expor /health ou /v1/models
                for path in ("/health", "/v1/models"):
                    try:
                        resp = client.get(f"{self.base_url}{path}")
                        if resp.status_code < 500:
                            return True
                    except httpx.HTTPError:
                        continue
            return False
        except httpx.HTTPError:
            return False

    def synthesize(self, text: str, execution_id: str) -> tuple[str | None, dict]:
        """Gera WAV e retorna (caminho|None, meta)."""
        if not self.enabled:
            return None, {"success": False, "error": "TTS desabilitado (KOKORO_ENABLED=false)"}

        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        out_path = AUDIO_DIR / f"{execution_id}.wav"
        speech = _prepare_speech_text(text)

        body = {
            "model": "kokoro",
            "input": speech,
            "voice": self.voice,
            "response_format": "wav",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/v1/audio/speech", json=body)
                resp.raise_for_status()
                content = resp.content
                if not content:
                    raise ValueError("Áudio vazio retornado pelo Kokoro")
                out_path.write_bytes(content)
                return str(out_path), {
                    "success": True,
                    "bytes": len(content),
                    "voice": self.voice,
                }
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Kokoro indisponível/falhou: %s", exc)
            return None, {"success": False, "error": str(exc)}
