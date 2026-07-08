param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000,
    [string]$LlmProvider = "disabled"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $projectRoot "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null

$env:LLM_PROVIDER = $LlmProvider
Set-Location $projectRoot

python -m app.utils.seed_db
python -m uvicorn app.main:app --host $HostName --port $Port --log-level info
