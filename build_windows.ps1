$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    & (Join-Path $ProjectRoot "setup_windows.ps1")
}

& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements-dev.txt")
Push-Location $ProjectRoot
try {
    & $VenvPython -m PyInstaller `
        --noconfirm `
        --clean `
        --windowed `
        --name "MultiFormatMarkdown" `
        --collect-all tkinterdnd2 `
        "doc_to_md_gui.py"
}
finally {
    Pop-Location
}

Write-Host "Build complete: dist\MultiFormatMarkdown\MultiFormatMarkdown.exe" -ForegroundColor Green
