"""Clientes TTS — Kokoro (local/spec) e Edge Neural (apresentação)."""

from __future__ import annotations

import asyncio
import html
import re
from pathlib import Path

import httpx

from app.config import PROJECT_ROOT, Settings
from app.logging_config import get_logger

logger = get_logger(__name__)

AUDIO_DIR = PROJECT_ROOT / "data" / "results" / "audio"

# Termos de TI em inglês que a voz pt-BR leria com fonemas portugueses
# (ex.: "pull requests" saía como "pɔl ɔkʷists"). O SSML <phoneme alphabet="ipa">
# dita a pronúncia inglesa correta mantendo a mesma voz (servidor Kokoro FastAPI).
# Mantenha os plurais separados — o regex usa a palavra inteira (\b).
_EN_G2P: dict[str, str] = {
    "devops": "ˈdɛvɑps",
    "github": "ˈɡɪthʌb",
    "git": "ɡɪt",
    "pipeline": "ˈpaɪpaɪl",
    "commit": "kəˈmɪt",
    "commits": "kəˈmɪts",
    "pull": "pʊl",
    "request": "rɪˈkwest",
    "requests": "rɪˈkwests",
    "workflow": "ˈwɝkfloʊ",
    "workflows": "ˈwɝkfloʊz",
    "health": "hɛlθ",
    "check": "tʃɛk",
    "checks": "tʃɛks",
    "ci": "siːˈaɪ",
    "cd": "siːˈdiː",
    "docker": "ˈdɑkər",
    "kubernetes": "ˌkubərˈnɛtɪs",
    "mcp": "ɛm siː piː",
    "n8n": "ɛn eɪt ɛn",
    "json": "ˈdʒeɪsən",
    "api": "eɪ piː ˈaɪ",
    "sla": "ɛs ɛl ˈeɪ",
    "qa": "kjuː ˈeɪ",
    "llm": "ɛl ɛl ˈɛm",
    "merge": "mɝdʒ",
    "merged": "mɝdʒd",
    "release": "rɪˈliːs",
    "releases": "rɪˈliːsɪz",
    "bug": "bʌɡ",
    "bugs": "bʌɡz",
    "deploy": "dɪˈplɔɪ",
    "deployed": "dɪˈplɔɪd",
    "run": "rʌn",
    "runs": "rʌnz",
    "action": "ˈækʃən",
    "actions": "ˈækʃənz",
    "server": "ˈsɝvər",
    "servers": "ˈsɝvərz",
    "branch": "bræntʃ",
    "branches": "ˈbræntʃɪz",
    "test": "tɛst",
    "tests": "tɛsts",
    "status": "ˈsteɪtəs",
    "webhook": "ˈwɛbʊk",
    "webhooks": "ˈwɛbʊks",
}

_EN_WORDS_RE = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, _EN_G2P), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def _ssml_speech(text: str) -> str:
    """SSML com os termos de TI marcados para pronúncia inglesa (IPA)."""
    escaped = html.escape(text, quote=False)

    def _wrap(match: re.Match[str]) -> str:
        word = match.group(0)
        return f'<phoneme alphabet="ipa" ph="{_EN_G2P[word.lower()]}">{word}</phoneme>'

    return f"<speak>{_EN_WORDS_RE.sub(_wrap, escaped)}</speak>"


def _prepare_speech_text(text: str, max_chars: int = 1200) -> str:
    """Usa o texto do boletim falado; só extrai RESUMO se vier do LLM."""
    raw = (text or "").strip()
    upper = raw.upper()
    start = 0
    for marker in ("RESUMO:", "RESUMO\n", "SUMMARY:"):
        idx = upper.find(marker)
        if idx >= 0:
            start = idx + len(marker)
            break
    rest = raw[start:].strip() if start else raw
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
        self.edge_enabled = settings.edge_tts_enabled
        self.edge_voice = settings.edge_tts_voice
        self.edge_rate = settings.edge_tts_rate

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            with httpx.Client(timeout=3.0) as client:
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

    def _ssml_to_native(self, ssml: str) -> str | None:
        """Traduz SSML para o formato nativo do Kokoro ([palavra](/ipa/)).

        Fallback=None: se o endpoint não existir, sintetiza o texto puro.
        """
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/dev/ssml",
                    json={"text": ssml, "voice": self.voice},
                )
                resp.raise_for_status()
                return ((resp.json() or {}).get("text") or "") or None
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("SSML indisponível, usando texto puro: %s", exc)
            return None

    def synthesize(self, text: str, execution_id: str) -> tuple[str | None, dict]:
        """Kokoro local → MP3 (comprimido, ~10x menor que WAV). Retorna (caminho|None, meta)."""
        if not self.enabled:
            return None, {"success": False, "error": "TTS desabilitado (KOKORO_ENABLED=false)"}

        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        out_path = AUDIO_DIR / f"{execution_id}.mp3"
        speech = _prepare_speech_text(text)

        # Termos em inglês com pronúncia IPA correta (o resto segue em pt-BR).
        ssml_used = False
        payload_input = speech
        native = self._ssml_to_native(_ssml_speech(speech))
        if native:
            payload_input = native
            ssml_used = True

        body = {
            "model": "kokoro",
            "input": payload_input,
            "voice": self.voice,
            "response_format": "mp3",
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
                    "engine": "kokoro",
                    "ssml": ssml_used,
                }
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Kokoro indisponível/falhou: %s", exc)
            return None, {"success": False, "error": str(exc), "engine": "kokoro"}

    def synthesize_edge(self, text: str, execution_id: str) -> tuple[str | None, dict]:
        """Edge Neural pt-BR → MP3 (apresentação). Retorna (caminho|None, meta)."""
        if not self.edge_enabled:
            return None, {"success": False, "error": "Edge TTS desabilitado", "engine": "edge"}
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        out_path = AUDIO_DIR / f"{execution_id}-antonio.mp3"
        speech = _prepare_speech_text(text)

        async def _run() -> None:
            import edge_tts

            communicate = edge_tts.Communicate(
                speech, voice=self.edge_voice, rate=self.edge_rate
            )
            await communicate.save(str(out_path))

        try:
            asyncio.run(_run())
            if not out_path.exists() or out_path.stat().st_size < 2000:
                raise ValueError("Edge TTS não gerou áudio")
            return str(out_path), {
                "success": True,
                "bytes": out_path.stat().st_size,
                "voice": self.edge_voice,
                "engine": "edge",
            }
        except Exception as exc:  # noqa: BLE001
            # remove arquivo parcial (ex.: 0 bytes quando o serviço bloqueia)
            # para não deixar um mp3 vazio que confunde quem olha o diretório.
            out_path.unlink(missing_ok=True)
            logger.warning("Edge TTS falhou: %s", exc)
            return None, {"success": False, "error": str(exc), "engine": "edge"}
