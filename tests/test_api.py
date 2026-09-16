"""Testes da API FastAPI com modo demo."""

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def test_health_returns_components():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "components" in data
    assert "github" in data["components"]
    assert "ollama" in data["components"]
    assert "kokoro" in data["components"]


def test_api_pulse_demo_mode():
    # settings padrão tem demo_mode=true
    resp = client.get("/api/pulse?hours=24")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"success", "partial"}
    assert data["data_source"] == "demo"
    assert "metrics" in data
    assert "alerts" in data
    assert data["execution_id"].startswith("PULSE-")
    assert data["collection_latency_ms"] >= 0


def test_api_pulse_metrics_shape():
    resp = client.get("/api/pulse")
    m = resp.json()["metrics"]
    for key in (
        "commits",
        "issues_opened",
        "pull_requests_opened",
        "workflow_runs",
        "workflow_success_rate",
    ):
        assert key in m


def test_pipeline_run_without_external_services():
    """Pipeline com LLM/TTS desligados deve funcionar só com demo + SQLite."""
    resp = client.post("/api/pipeline/run?hours=24&with_llm=false&with_tts=false&persist=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["execution_id"].startswith("PULSE-")
    assert data["timings"]["total_pipeline_latency_ms"] >= 0
    assert data["status"] in {"success", "partial"}


def test_executions_endpoint():
    resp = client.get("/api/executions?limit=5")
    assert resp.status_code == 200
    assert "items" in resp.json()
