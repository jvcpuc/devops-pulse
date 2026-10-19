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


def test_whatsapp_status_endpoint_without_evolution(monkeypatch):
    """Evolution indisponível → status 200 com erro controlado (não 500)."""
    import app.main as main_mod

    def fake_down(self):
        return False, {"ok": False, "connected": False, "error": "connection refused"}

    monkeypatch.setattr(main_mod.WhatsAppClient, "connection_state", fake_down)
    resp = client.get("/api/whatsapp/status")
    assert resp.status_code == 200
    data = resp.json()
    assert set(["enabled", "ready", "ok", "instance", "evolution_url"]) <= set(data)
    # Evolution fora do ar: ok=False e erro presente; ready nunca vira True.
    assert data["ready"] is False
    assert data["ok"] is False
    assert data["error"]


def test_whatsapp_status_reports_connected(monkeypatch):
    """Quando a instância está 'open', o status marca ready=true."""
    import app.main as main_mod

    def fake_state(self):
        return True, {"ok": True, "connected": True, "state": "open", "instance": self.instance}

    monkeypatch.setattr(main_mod.WhatsAppClient, "connection_state", fake_state)
    resp = client.get("/api/whatsapp/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert data["state"] == "open"


def test_whatsapp_qr_endpoint(monkeypatch):
    """QR indisponível → 502 com detalhe; disponível → base64 + pairing code."""
    import app.main as main_mod

    def fake_unavailable(self):
        return False, {"success": False, "error": "Evolution API fora do ar"}

    monkeypatch.setattr(main_mod.WhatsAppClient, "fetch_qr", fake_unavailable)
    resp = client.get("/api/whatsapp/qr")
    assert resp.status_code == 502
    assert "Evolution API fora do ar" in resp.json()["detail"]

    def fake_ok(self):
        return True, {
            "success": True,
            "qr_base64": "data:image/png;base64,dGVzdGU=",
            "pairing_code": "ABCD-EFGH",
            "instance": "devops-pulse",
            "manager_url": "http://127.0.0.1:18080",
        }

    monkeypatch.setattr(main_mod.WhatsAppClient, "fetch_qr", fake_ok)
    resp = client.get("/api/whatsapp/qr")
    assert resp.status_code == 200
    data = resp.json()
    assert data["qr_base64"].startswith("data:image/")
    assert data["pairing_code"] == "ABCD-EFGH"
