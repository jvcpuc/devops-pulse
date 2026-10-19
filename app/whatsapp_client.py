"""Envio de WhatsApp via Evolution API (self-hosted)."""

from __future__ import annotations

import base64
import time
from pathlib import Path

import httpx

from app.config import Settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def _audio_mimetype(path: Path) -> str:
    """Mimetype do áudio a partir da extensão (Kokoro e Edge geram .mp3)."""
    return {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".opus": "audio/ogg",
    }.get(path.suffix.lower(), "audio/mpeg")


class WhatsAppClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = settings.whatsapp_enabled
        self.base_url = (settings.whatsapp_api_url or "").rstrip("/")
        self.instance = settings.evolution_instance or "devops-pulse"
        self.apikey = settings.evolution_api_key or settings.whatsapp_token
        # grupo do projeto se configurado; senão whatsapp_to
        self.to = settings.whatsapp_group or settings.whatsapp_to
        self.timeout = settings.whatsapp_timeout_seconds

    def send_text(self, text: str) -> tuple[bool, dict]:
        if not self.enabled:
            return False, {"success": False, "error": "WHATSAPP_ENABLED=false"}
        if not self.base_url or not self.apikey or not self.to:
            return False, {
                "success": False,
                "error": "WhatsApp incompleto (api_url/instance/to/apikey)",
            }
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {"number": self.to, "text": text}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    url,
                    json=payload,
                    headers={
                        "apikey": self.apikey,
                        "Content-Type": "application/json; charset=utf-8",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            key = ((data.get("key") or {}).get("id")) or ""
            return True, {
                "success": True,
                "key": key,
                "status": data.get("status"),
                "to": self.to,
                "instance": self.instance,
            }
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("WhatsApp falhou: %s", exc)
            return False, {"success": False, "error": str(exc)}

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.apikey or "",
            "Content-Type": "application/json; charset=utf-8",
        }

    def connection_state(self) -> tuple[bool, dict]:
        """Estado da conexão da instância (open = conectado).

        Retorna (ok, meta). ``ok=False`` quando a instância não existe, a
        Evolution API está fora do ar ou a configuração está incompleta.
        """
        if not self.base_url or not self.apikey:
            return False, {"ok": False, "connected": False, "error": "WhatsApp incompleto (api_url/apikey)"}
        url = f"{self.base_url}/instance/connectionState/{self.instance}"
        try:
            with httpx.Client(timeout=min(self.timeout, 10.0)) as client:
                resp = client.get(url, headers={"apikey": self.apikey})
                if resp.status_code == 404:
                    return False, {
                        "ok": False,
                        "connected": False,
                        "error": f"Instância '{self.instance}' não existe na Evolution API",
                    }
                resp.raise_for_status()
                data = resp.json()
            state = ((data.get("instance") or {}).get("state")) or "desconhecido"
            return True, {
                "ok": True,
                "connected": state == "open",
                "state": state,
                "instance": self.instance,
                "target": self.to or None,
            }
        except (httpx.HTTPError, ValueError) as exc:
            return False, {"ok": False, "connected": False, "error": str(exc)}

    def fetch_qr(self) -> tuple[bool, dict]:
        """QR code (base64) + pairing code para parear o WhatsApp.

        A Evolution API devolve ``base64`` (data URI PNG) e ``pairingCode``
        enquanto a instância não está conectada.
        """
        if not self.base_url or not self.apikey:
            return False, {"success": False, "error": "WhatsApp incompleto (api_url/apikey)"}
        url = f"{self.base_url}/instance/connect/{self.instance}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                created = False
                resp = None
                # A connect pode devolver 5xx enquanto a Evolution sobe o socket
                # (principalmente logo após criar a instância) — re-tenta com espera curta.
                for attempt in range(5):
                    if attempt:
                        time.sleep(2.0)
                    resp = client.get(url, headers={"apikey": self.apikey})
                    if resp.status_code == 404 and not created:
                        # Instância ainda não existe — cria (Baileys) e tenta de novo.
                        create = client.post(
                            f"{self.base_url}/instance/create",
                            json={
                                "instanceName": self.instance,
                                "integration": "WHATSAPP-BAILEYS",
                            },
                            headers={
                                "apikey": self.apikey,
                                "Content-Type": "application/json",
                            },
                        )
                        if create.status_code >= 400 and create.status_code != 409:
                            return False, {
                                "success": False,
                                "error": (
                                    f"Criação da instância '{self.instance}' falhou "
                                    f"(HTTP {create.status_code}): {create.text[:200]}"
                                ),
                            }
                        created = True
                        continue
                    if resp.status_code >= 500:
                        continue  # transiente (instância subindo/reiniciando)
                    break
                assert resp is not None
                if resp.status_code == 404:
                    return False, {
                        "success": False,
                        "error": f"Instância '{self.instance}' não existe — crie-a antes de parear.",
                    }
                resp.raise_for_status()
                data = resp.json()
            qr = data.get("base64") or ""
            # pairingCode vem vazio nesta versão da Evolution — mostra só o QR.
            pairing = data.get("pairingCode") or data.get("pairing_code") or ""
            if not qr:
                return False, {
                    "success": False,
                    "error": "Evolution API não retornou QR — a instância já está conectada ou ainda está iniciando.",
                }
            return True, {
                "success": True,
                "qr_base64": qr,
                "pairing_code": pairing or None,
                "instance": self.instance,
                "manager_url": self.base_url,
            }
        except (httpx.HTTPError, ValueError) as exc:
            return False, {"success": False, "error": str(exc)}

    def send_audio(self, audio_path: str | Path, caption: str = "") -> tuple[bool, dict]:
        """Envia um arquivo de áudio (MP3) como mídia no WhatsApp."""
        if not self.enabled:
            return False, {"success": False, "error": "WHATSAPP_ENABLED=false"}
        if not self.base_url or not self.apikey or not self.to:
            return False, {"success": False, "error": "WhatsApp incompleto (api_url/instance/to/apikey)"}
        path = Path(audio_path)
        if not path.is_file():
            return False, {"success": False, "error": f"Áudio não encontrado: {path}"}
        if path.stat().st_size == 0:
            return False, {"success": False, "error": f"Áudio vazio (0 bytes): {path.name}"}
        try:
            payload = {
                "number": self.to,
                "mediatype": "audio",
                # Evolução v2.3.x: mídia vai no campo "media" (base64 puro ou URL).
                "media": base64.b64encode(path.read_bytes()).decode("ascii"),
                "mimetype": _audio_mimetype(path),
                "fileName": path.name,
            }
            if caption:
                payload["caption"] = caption
            url = f"{self.base_url}/message/sendMedia/{self.instance}"
            with httpx.Client(timeout=max(self.timeout, 60.0)) as client:
                # O socket do Baileys oscila (keep-alive/WSL2) e já derrubou o
                # envio do áudio logo após o texto — re-tenta em 5xx/queda.
                resp = None
                for attempt in range(3):
                    if attempt:
                        time.sleep(2.0)
                    try:
                        resp = client.post(url, json=payload, headers=self._headers())
                    except httpx.HTTPError as exc:
                        logger.warning("sendAudio falhou (tentativa %d): %s", attempt + 1, exc)
                        continue
                    if resp.status_code >= 500:
                        logger.warning(
                            "sendAudio HTTP %d (tentativa %d)", resp.status_code, attempt + 1
                        )
                        continue
                    break
                assert resp is not None
                resp.raise_for_status()
                data = resp.json()
            key = ((data.get("key") or {}).get("id")) or ""
            return True, {
                "success": True,
                "key": key,
                "status": data.get("status"),
                "to": self.to,
                "instance": self.instance,
                "file": path.name,
                "bytes": path.stat().st_size,
            }
        except (httpx.HTTPError, ValueError, OSError) as exc:
            logger.warning("WhatsApp áudio falhou: %s", exc)
            return False, {"success": False, "error": str(exc)}
