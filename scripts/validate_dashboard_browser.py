"""Validação do navegador: botões MCP novos + status WhatsApp + QR.

Uso: python scripts/validate_dashboard_browser.py
Requer a API em http://127.0.0.1:8000 (scripts/start_demo.ps1).
Salva evidências em evidence/.

Cobre também a transição de status "não conectado → conectado" via
mock do /api/whatsapp/status (page.route), sem precisar de celular:
valida o poll rápido (5s) e o auto-ocultar do QR.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = PROJECT_ROOT / "evidence"
DASHBOARD = (PROJECT_ROOT / "dashboard" / "index.html").as_uri()

WA_CONNECTED = {
    "enabled": True,
    "instance": "devops-pulse",
    "evolution_url": "http://127.0.0.1:18080",
    "ready": True,
    "ok": True,
    "connected": True,
    "state": "open",
    "target": "120363412036540372@g.us",
}


def main() -> int:
    results: dict[str, object] = {}
    errors: list[str] = []
    wa_mock = {"connected": False}

    def wa_status_handler(route, request):
        if wa_mock["connected"]:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(WA_CONNECTED),
            )
        else:
            route.continue_()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1360, "height": 1000})
        page.route("**/api/whatsapp/status*", wa_status_handler)
        page.goto(DASHBOARD)

        # 1) Status do WhatsApp em background (verificação automática da página).
        page.wait_for_function(
            "() => !document.getElementById('wa-status-badge').textContent.includes('verificando')",
            timeout=15_000,
        )
        wa_badge = page.locator("#wa-status-badge").inner_text()
        wa_detail = page.locator("#wa-status-detail").inner_text()
        results["wa_status_badge"] = wa_badge
        results["wa_status_detail"] = wa_detail
        if "não conectado" not in wa_badge.lower():
            errors.append(f"badge WhatsApp inesperado: {wa_badge!r}")

        # 1b) Botão "Verificar agora" força nova checagem sem F5.
        if page.locator("#btn-wa-check").count() != 1:
            errors.append("botão #btn-wa-check ausente")
        else:
            page.click("#btn-wa-check")
            page.wait_for_function(
                "() => !document.getElementById('wa-status-badge').textContent.includes('verificando')",
                timeout=15_000,
            )

        # 2) Botão QR visível quando não conectado; clique → QR renderizado.
        qr_btn = page.locator("#btn-wa-qr")
        if not qr_btn.is_visible():
            errors.append("botão 'Mostrar QR do WhatsApp' não apareceu")
        else:
            qr_btn.click()
            page.wait_for_function(
                "() => { const i = document.getElementById('wa-qr-img');"
                " return i && i.src && i.src.startsWith('data:image/'); }",
                timeout=60_000,
            )
            results["qr_rendered"] = True
            if "Atualizar QR" not in qr_btn.inner_text():
                errors.append(f"rótulo do botão QR não virou 'Atualizar QR': {qr_btn.inner_text()!r}")

            # 2b) Transição mockada para CONECTADO: o poll rápido (5s) deve
            #     refletir em <10s e some com o QR — sem F5.
            wa_mock["connected"] = True
            page.wait_for_function(
                "() => document.getElementById('wa-status-badge').textContent === 'WhatsApp conectado'"
                " && document.getElementById('wa-qr-area').hidden",
                timeout=10_000,
            )
            results["fast_poll_connected"] = True
            page.screenshot(path=str(EVIDENCE / "16-whatsapp-connected-mock.png"), full_page=False)

            # 2c) Desmock → "Verificar agora" volta a mostrar a estado real honesto.
            wa_mock["connected"] = False
            page.click("#btn-wa-check")
            page.wait_for_function(
                "() => document.getElementById('wa-status-badge').textContent !== 'WhatsApp conectado'"
                " && !document.getElementById('btn-wa-qr').hidden",
                timeout=15_000,
            )
            results["disconnect_restored"] = True

        # 3) Botão de estresse → eco do resultado na página.
        page.click("#btn-mcp-stress")
        page.wait_for_function(
            "() => [...document.querySelectorAll('.mcp-result-title span')]"
            ".some(s => s.textContent.includes('run_stress_test'))",
            timeout=120_000,
        )
        stress_text = page.locator("#mcp-results .mcp-json").first.inner_text()
        stress = json.loads(stress_text)
        results["stress"] = {
            "total_requests": stress.get("total_requests"),
            "overall_success_rate": stress.get("overall_success_rate"),
            "endpoint": stress.get("endpoint"),
        }
        if stress.get("total_success") != stress.get("total_requests"):
            errors.append("stress teve falhas: " + json.dumps(stress.get("batches"))[:300])

        # 4) Screenshot da evidência (painel MCP completo).
        page.locator("#mcp-panel").scroll_into_view_if_needed()
        page.screenshot(path=str(EVIDENCE / "15-mcp-stress-qr.png"), full_page=True)

        # 5) Botões dos 5 tools + completo presentes.
        for btn in (
            "btn-mcp-metrics",
            "btn-mcp-full",
            "btn-mcp-stress",
            "btn-wa-qr",
            "btn-wa-check",
        ):
            if page.locator(f"#{btn}").count() != 1:
                errors.append(f"botão #{btn} ausente")

        browser.close()

    (EVIDENCE / "mcp" / "browser-stress-qr.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if errors:
        print("FALHAS:")
        for e in errors:
            print(" -", e)
        return 1
    print("OK:", json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
