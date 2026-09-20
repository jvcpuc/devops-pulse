"""Envio de WhatsApp via Evolution API (self-hosted)."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.logging_config import get_logger

logger = get_logger(__name__)


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
