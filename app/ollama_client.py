"""Cliente Ollama — geração de resumo executivo via LLM local."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings
from app.logging_config import get_logger
from app.schemas import Metrics

logger = get_logger(__name__)

SYSTEM_PROMPT = """Você é um analista de operações de desenvolvimento de software.

Analise os indicadores fornecidos abaixo.

Objetivos:
1. Produzir um resumo executivo curto.
2. Destacar alterações relevantes.
3. Identificar riscos operacionais somente quando houver evidência nos dados.
4. Não inventar informações.
5. Não atribuir causas que não estejam presentes nos dados.
6. Diferenciar fatos de interpretações.
7. Sugerir ações objetivas quando houver evidência suficiente.

Formato obrigatório:

RESUMO:
...

INDICADORES:
...

ALERTAS:
...

RECOMENDAÇÕES:
...

LIMITAÇÕES:
...
"""

FALLBACK_TEMPLATE = """RESUMO:
Resumo técnico gerado sem LLM (Ollama indisponível). Dados brutos dos indicadores abaixo.

INDICADORES:
{indicators}

ALERTAS:
{alerts}

RECOMENDAÇÕES:
Revise manualmente os alertas listados. Confirme o estado do CI/CD e PRs antigos.

LIMITAÇÕES:
Este texto NÃO foi produzido por modelo de linguagem. Ollama indisponível ou com erro.
"""


class OllamaClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout_seconds

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    def generate_summary(self, metrics: Metrics, alerts: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        """Retorna (texto, meta). meta.success=False se houve fallback."""
        payload = {
            "metrics": metrics.as_dict(),
            "alerts": alerts,
            "instruction": (
                "Interprete apenas os dados acima. Não invente incidentes, causas ou pessoas."
            ),
        }
        body = {
            "model": self.model,
            "prompt": f"{SYSTEM_PROMPT}\n\nDados:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n",
            "stream": False,
            "options": {"temperature": 0.2},
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/generate", json=body)
                resp.raise_for_status()
                data = resp.json()
                text = (data.get("response") or "").strip()
                if not text:
                    raise ValueError("Resposta vazia do Ollama")
                meta = {
                    "success": True,
                    "model": self.model,
                    "eval_count": data.get("eval_count"),
                    "total_duration_ms": (data.get("total_duration") or 0) / 1e6,
                }
                return text, meta
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Ollama indisponível/falhou: %s", exc)
            fallback = FALLBACK_TEMPLATE.format(
                indicators=json.dumps(metrics.as_dict(), ensure_ascii=False, indent=2),
                alerts=json.dumps(alerts, ensure_ascii=False, indent=2) if alerts else "Nenhum alerta.",
            )
            return fallback, {"success": False, "error": str(exc), "fallback": True}
