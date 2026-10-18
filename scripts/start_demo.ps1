# Demonstração do DevOps Pulse AI + MCP em um comando.
# Uso:  .\scripts\start_demo.ps1            # usa DEMO_MODE do pulse.env/.env
#       .\scripts\start_demo.ps1 -ForceDemo # força dados de demonstração
#
# O que faz:
#   1. Carrega o ambiente (.env ou pulse.env)
#   2. Sobe a API FastAPI (que também hospeda o servidor MCP em /mcp) se necessário
#   3. Abre o dashboard no navegador (seção "Demonstração MCP")
# Não apaga dados, não altera o repositório remoto e não modifica o sistema.

param(
    [switch]$ForceDemo
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "Ambiente Python não encontrado. Crie-o primeiro:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

# --- Ambiente (.env ou pulse.env; o start_services já usa esta lógica) ---
foreach ($name in @(".env", "pulse.env")) {
    $candidate = Join-Path $root $name
    if (Test-Path $candidate) {
        Get-Content $candidate | ForEach-Object {
            if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
            $pair = $_.Split('=', 2)
            Set-Item -Path ("Env:" + $pair[0].Trim()) -Value $pair[1].Trim()
        }
        Write-Host "env carregado de $name"
        break
    }
}
if ($ForceDemo) { $env:DEMO_MODE = "true"; Write-Host "DEMO_MODE forçado = true (dados fictícios rotulados)" -ForegroundColor Yellow }
if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = "llama3.2:1b" }

# --- API + servidor MCP (mesmo processo, porta 8000) ---
$api = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($api) {
    Write-Host "API + MCP já ativos em http://127.0.0.1:8000" -ForegroundColor Green
} else {
    Start-Process -FilePath $py -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $root -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "API + MCP iniciados em http://127.0.0.1:8000" -ForegroundColor Green
}

try {
    $health = Invoke-RestMethod http://127.0.0.1:8000/health -TimeoutSec 5
    Write-Host ("health: " + $health.status + " | demo_mode: " + $health.demo_mode)
} catch {
    Write-Host "A API não respondeu em http://127.0.0.1:8000/health — veja logs\app.log" -ForegroundColor Yellow
}

# --- Abre o dashboard (seção "Demonstração MCP") ---
$dash = Join-Path $root "dashboard\index.html"
Start-Process $dash

Write-Host ""
Write-Host "Ambiente da demonstração:" -ForegroundColor Cyan
Write-Host "  Dashboard (botões MCP): $dash"
Write-Host "  API:                    http://127.0.0.1:8000/health"
Write-Host "  Servidor MCP (Streamable HTTP): http://127.0.0.1:8000/mcp"
Write-Host "  Servidor MCP (stdio):   $py -m app.mcp_server"
Write-Host ""
Write-Host "Ferramentas MCP: get_repository_metrics · get_commit_activity ·"
Write-Host "                 get_pull_requests · get_issues · analyze_repository_health"
Write-Host "Guia completo:   docs\mcp-demo.md"
