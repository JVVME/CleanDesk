param(
    [switch]$Installer
)

$ErrorActionPreference = "Stop"

Write-Host "Building CleanDesk (PyInstaller)" -ForegroundColor Cyan
uv run --extra build -- python -m PyInstaller cleandesk.spec

if ($Installer) {
    Write-Host "Building installer (NSIS)" -ForegroundColor Cyan
    makensis installer\cleandesk.nsi
}
