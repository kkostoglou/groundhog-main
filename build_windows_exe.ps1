[CmdletBinding()]
param(
    [string]$Python = "py",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BuildEnvironment = Join-Path $PackageRoot ".build-venv"
$ReleaseRoot = Join-Path $PackageRoot "release\GroundhogDesktop"
$SourceRoot = Join-Path $ReleaseRoot "source"

Set-Location $PackageRoot

if (-not (Test-Path $BuildEnvironment)) {
    if ($Python -eq "py") {
        & py -3 -m venv $BuildEnvironment
    } else {
        & $Python -m venv $BuildEnvironment
    }
}

$BuildPython = Join-Path $BuildEnvironment "Scripts\python.exe"
if (-not $SkipInstall) {
    & $BuildPython -m pip install --upgrade pip
    & $BuildPython -m pip install -r requirements-build.txt
    & $BuildPython -m pip install --no-deps -e .
}

& $BuildPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name GroundhogDesktop `
    --paths $PackageRoot `
    --add-data "notebooks\Data\cpt.xlsx;notebooks\Data" `
    --collect-submodules groundhog `
    GroundhogDesktopGUI.py

New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null
New-Item -ItemType Directory -Force -Path $SourceRoot | Out-Null

Copy-Item "dist\GroundhogDesktop.exe" $ReleaseRoot -Force
Copy-Item "GroundhogDesktopGUI.py" $SourceRoot -Force
Copy-Item "setup.py", "requirements.txt", "optional-requirements.txt", `
    "requirements-desktop.txt", "requirements-build.txt", "run_groundhog.bat", `
    "build_windows_exe.ps1" `
    $SourceRoot -Force
Copy-Item "groundhog" (Join-Path $SourceRoot "groundhog") -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $SourceRoot "notebooks\Data") | Out-Null
Copy-Item "notebooks\Data\cpt.xlsx" (Join-Path $SourceRoot "notebooks\Data") -Force
Copy-Item "README.md", "USER_GUIDE.md", "RELEASE_GUIDE.md", "LICENSE" $ReleaseRoot -Force

$ExecutableHash = (Get-FileHash (Join-Path $ReleaseRoot "GroundhogDesktop.exe") -Algorithm SHA256).Hash
Set-Content -Path (Join-Path $ReleaseRoot "SHA256SUMS.txt") `
    -Value "$ExecutableHash  GroundhogDesktop.exe" -Encoding Ascii

$SourceLauncher = @'
@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
call ".venv\Scripts\python.exe" -m pip install -r requirements-desktop.txt
call ".venv\Scripts\python.exe" -m pip install --no-deps -e .
start "Groundhog Desktop" ".venv\Scripts\pythonw.exe" "GroundhogDesktopGUI.py"
'@
Set-Content -Path (Join-Path $SourceRoot "install_and_run.bat") -Value $SourceLauncher -Encoding Ascii

$Archive = Join-Path $PackageRoot "release\GroundhogDesktop-Windows.zip"
if (Test-Path $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}
Compress-Archive -Path "$ReleaseRoot\*" -DestinationPath $Archive -CompressionLevel Optimal

Write-Host ""
Write-Host "Build complete:"
Write-Host "  Executable: $ReleaseRoot\GroundhogDesktop.exe"
Write-Host "  Bundle:     $Archive"
