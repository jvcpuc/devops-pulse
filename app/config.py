"""Configuração central via variáveis de ambiente."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_port: int = 8000
    app_host: str = "127.0.0.1"
    demo_mode: bool = True
    log_level: str = "INFO"
    request_timeout_seconds: float = 30.0

    # GitHub
    github_owner: str = ""
    github_repository: str = ""
    github_token: str = ""
    github_api_base: str = "https://api.github.com"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_timeout_seconds: float = 60.0

    # Kokoro
    kokoro_base_url: str = "http://localhost:8880"
    kokoro_enabled: bool = True
    kokoro_voice: str = "pf_dora"
    kokoro_timeout_seconds: float = 60.0

    # Edge TTS (voz neural pt-BR — áudio de apresentação)
    edge_tts_enabled: bool = True
    edge_tts_voice: str = "pt-BR-AntonioNeural"
    edge_tts_rate: str = "-8%"

    # n8n
    n8n_base_url: str = "http://localhost:5678"

    # Persistência
    persistence_backend: str = "sqlite"
    sqlite_path: str = "data/results/pulse.db"
    google_sheet_id: str = ""

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_to: str = ""
    smtp_use_tls: bool = True

    # WhatsApp / Evolution API
    whatsapp_enabled: bool = False
    whatsapp_provider: str = "evolution"
    whatsapp_api_url: str = "http://127.0.0.1:8080"
    whatsapp_token: str = ""
    whatsapp_to: str = ""
    whatsapp_group: str = ""
    whatsapp_timeout_seconds: float = 20.0
    evolution_instance: str = "devops-pulse"
    evolution_api_key: str = ""

    # Alert thresholds
    stale_pr_days: int = 3
    low_ci_success_rate: float = 80.0
    high_issue_volume: int = 10
    unusual_activity_multiplier: float = 2.0

    @property
    def repo_full_name(self) -> str:
        if self.github_owner and self.github_repository:
            return f"{self.github_owner}/{self.github_repository}"
        return ""

    @property
    def sqlite_abs_path(self) -> Path:
        path = Path(self.sqlite_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
