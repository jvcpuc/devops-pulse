# Sobe dependências locais do DevOps Pulse AI no Windows
# Uso: .\scripts\start_services.ps1

$ErrorActionPreference = "Continue"

Write-Host "== Ollama ==" -ForegroundColor Cyan
$ollama = "C:\Users\jonec\AppData\Local\Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollama)) {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { $ollama = $cmd.Source }
}
if ($ollama) {
    $up = $false
    try {
        Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 2 | Out-Null
        $up = $true
    } catch {}
    if (-not $up) {
        Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
        Write-Host "  ollama serve iniciado"
    } else {
        Write-Host "  ollama já ativo"
    }
} else {
    Write-Host "  ollama não encontrado" -ForegroundColor Yellow
}

Write-Host "== Kokoro (Docker) ==" -ForegroundColor Cyan
$kokoro = docker ps --filter name=kokoro --format "{{.Names}}" 2>$null
if ($kokoro -ne "kokoro") {
    $exists = docker ps -a --filter name=kokoro --format "{{.Names}}" 2>$null
    if ($exists -eq "kokoro") {
        docker start kokoro | Out-Null
    } else {
        docker run -d --name kokoro -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu:latest | Out-Null
    }
    Write-Host "  kokoro container iniciado (warmup ~15s)"
    Start-Sleep -Seconds 15
} else {
    Write-Host "  kokoro já ativo"
}

Write-Host "== n8n (Docker) ==" -ForegroundColor Cyan
$n8n = docker ps --filter name=n8n --format "{{.Names}}" 2>$null
if ($n8n -eq "n8n") {
    Write-Host "  n8n já ativo em http://localhost:5678"
} else {
    Write-Host "  n8n não está rodando — inicie o container n8n" -ForegroundColor Yellow
}

Write-Host "== Evolution API + Postgres (WhatsApp) ==" -ForegroundColor Cyan
$evo = docker ps --filter name=evolution-api --format "{{.Names}}" 2>$null
if ($evo -ne "evolution-api") {
    $compose = Join-Path (Split-Path -Parent $PSScriptRoot) "docker-compose.evolution.yml"
    if (Test-Path $compose) {
        docker compose -f $compose up -d 2>&1 | Out-Null
        Write-Host "  evolution-api + postgres iniciados via compose"
        Start-Sleep -Seconds 12
    } else {
        Write-Host "  docker-compose.evolution.yml não encontrado" -ForegroundColor Yellow
    }
} else {
    Write-Host "  evolution-api já ativo em http://localhost:8080"
}
Write-Host "  Manager/QR: http://localhost:8080  |  apikey: devops-pulse-evolution-key-2026"

Write-Host "== Microsserviço ==" -ForegroundColor Cyan
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $root ".venv\Scripts\python.exe"
# Bitdefender pode bloquear o nome literal .env — use pulse.env como fallback
$envFile = $null
foreach ($name in @(".env", "pulse.env")) {
    $candidate = Join-Path $root $name
    if (Test-Path $candidate) { $envFile = $candidate; break }
}
if ($envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
        $pair = $_.Split('=', 2)
        Set-Item -Path ("Env:" + $pair[0].Trim()) -Value $pair[1].Trim()
    }
    Write-Host "  env carregado de $(Split-Path -Leaf $envFile)"
}
if ($env:OLLAMA_MODE -eq "" -and $env:OLLAMA_MODEL -eq "") { $env:OLLAMA_MODEL = "llama3.2:1b" }
if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = "llama3.2:1b" }
if (Test-Path $py) {
    $api = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($api) {
        Write-Host "  API já está na porta 8000"
    } else {
        Start-Process -FilePath $py -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $root -WindowStyle Hidden
        Start-Sleep -Seconds 3
        Write-Host "  uvicorn iniciado em http://127.0.0.1:8000" -ForegroundColor Green
    }
} else {
    Write-Host "  crie o venv: python -m venv .venv && pip install -r requirements.txt" -ForegroundColor Yellow
}

Write-Host "`nHealth checks:" -ForegroundColor Cyan
foreach ($svc in @(
    @{n="ollama"; u="http://127.0.0.1:11434/api/tags"},
    @{n="kokoro"; u="http://127.0.0.1:8880/health"},
    @{n="n8n"; u="http://127.0.0.1:5678/healthz"},
    @{n="evolution"; u="http://127.0.0.1:8080/"}
)) {
    try {
        Invoke-RestMethod $svc.u -TimeoutSec 5 | Out-Null
        Write-Host "  [$($svc.n)] OK"
    } catch {
        Write-Host "  [$($svc.n)] FALHOU" -ForegroundColor Yellow
    }
}
