$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        & $PyLauncher.Source -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
        if ($LASTEXITCODE -ne 0) {
            throw "Python 3.10 or newer is required."
        }
        & $PyLauncher.Source -3 -m venv (Join-Path $ProjectRoot ".venv")
    }
    else {
        $Python = Get-Command python -ErrorAction Stop
        & $Python.Source -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
        if ($LASTEXITCODE -ne 0) {
            throw "Python 3.10 or newer is required."
        }
        & $Python.Source -m venv (Join-Path $ProjectRoot ".venv")
    }
}

& $VenvPython -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "The project virtual environment must use Python 3.10 or newer."
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

Write-Host "Setup complete. Double-click run_gui.bat to start the app." -ForegroundColor Green
