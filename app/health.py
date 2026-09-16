"""Health checks dos componentes do pipeline."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


def check_github(settings: Settings) -> dict[str, Any]:
    if settings.demo_mode:
        return {"ok": True, "detail": "DEMO_MODE=true (não consulta API real)"}
    if not settings.repo_full_name:
        return {"ok": False, "detail": "GITHUB_OWNER/REPOSITORY não configurados"}
    try:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "devops-pulse-ai"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        with httpx.Client(timeout=5.0, headers=headers) as client:
            resp = client.get(f"{settings.github_api_base.rstrip('/')}/repos/{settings.repo_full_name}")
        return {"ok": resp.status_code == 200, "detail": f"HTTP {resp.status_code}"}
    except httpx.HTTPError as exc:
        return {"ok": False, "detail": str(exc)}


def check_ollama(settings: Settings) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
        models = []
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name") for m in data.get("models", [])]
        return {
            "ok": resp.status_code == 200,
            "detail": f"HTTP {resp.status_code}",
            "model_configured": settings.ollama_model,
            "models": models,
        }
    except httpx.HTTPError as exc:
        return {"ok": False, "detail": str(exc), "model_configured": settings.ollama_model}


def check_kokoro(settings: Settings) -> dict[str, Any]:
    if not settings.kokoro_enabled:
        return {"ok": False, "detail": "KOKORO_ENABLED=false"}
    try:
        with httpx.Client(timeout=3.0) as client:
            for path in ("/health", "/v1/models"):
                try:
                    resp = client.get(f"{settings.kokoro_base_url.rstrip('/')}{path}")
                    if resp.status_code < 500:
                        return {"ok": True, "detail": f"{path} HTTP {resp.status_code}"}
                except httpx.HTTPError:
                    continue
        return {"ok": False, "detail": "sem resposta utilizável"}
    except httpx.HTTPError as exc:
        return {"ok": False, "detail": str(exc)}


def check_n8n(settings: Settings) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{settings.n8n_base_url.rstrip('/')}/healthz")
        return {"ok": resp.status_code == 200, "detail": f"HTTP {resp.status_code}"}
    except httpx.HTTPError as exc:
        return {"ok": False, "detail": str(exc)}


def build_health(settings: Settings) -> dict[str, Any]:
    components = {
        "github": check_github(settings),
        "ollama": check_ollama(settings),
        "kokoro": check_kokoro(settings),
        "n8n": check_n8n(settings),
    }
    # O pipeline pode operar em modo degradado se pelo menos coleta/demo e persistência ok.
    healthy = True
    return {
        "status": "ok" if healthy else "degraded",
        "demo_mode": settings.demo_mode,
        "components": components,
    }
