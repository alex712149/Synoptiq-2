$ErrorActionPreference = 'Stop'
$root = 'D:\SIH2026\Synoptiq'
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw "Required Python interpreter not found: $python" }
Set-Location $root
$env:PYTHONPATH = Join-Path $root 'backend'
$env:SYNOPTIQ_MODE = 'real'
$env:SYNOPTIQ_DATABASE_ROLE = 'TRAINING'
$env:TRAINING_DATABASE_URL = 'sqlite:///./data/real/training.sqlite3'
$env:DATABASE_URL = 'postgresql+psycopg://user:password@host:5432/synoptiq'
$env:SYNOPTIQ_MODEL_VERSION = 'synoptiq-real-12m-20260929'
$env:SYNOPTIQ_ARTIFACTS_DIR = Join-Path $root 'artifacts\real_12m'
$env:SYNOPTIQ_MODELS_DIR = Join-Path $root 'artifacts\real_12m\models'
$env:SYNOPTIQ_CALIBRATION_DIR = Join-Path $root 'artifacts\real_12m\calibration'
$env:SYNOPTIQ_METRICS_DIR = Join-Path $root 'artifacts\real_12m\metrics'
$env:SYNOPTIQ_LIVE_DATA_DIR = Join-Path $root 'data\real\live'
$env:SYNOPTIQ_LIVE_REFRESH_MINUTES = '15'
$env:SYNOPTIQ_LIVE_FRESHNESS_MINUTES = '45'
$env:VITE_APP_MODE = 'LIVE'
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'

Start-Process -FilePath $python -ArgumentList '-m uvicorn app.main:app --host 127.0.0.1 --port 8000' -WorkingDirectory $root
Start-Process -FilePath $python -ArgumentList 'training\realdata\live_refresh.py' -WorkingDirectory $root
Start-Process -FilePath 'npm.cmd' -ArgumentList 'run dev -- --host 127.0.0.1 --port 5173' -WorkingDirectory (Join-Path $root 'frontend')

for ($i = 0; $i -lt 60; $i++) {
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8000/health'
        $status = Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/system/status'
        if ($health.status -eq 'ok') {
            Write-Output "Backend: http://127.0.0.1:8000"
            Write-Output "Frontend: http://127.0.0.1:5173"
            Write-Output ("Live state: " + $status.live_state)
            Write-Output ("Provider statuses: " + (($status.providers.PSObject.Properties | ForEach-Object { $_.Name + '=' + $_.Value.status }) -join ', '))
            exit 0
        }
    } catch { }
    Start-Sleep -Seconds 2
}
throw 'Backend did not become healthy within 120 seconds.'
