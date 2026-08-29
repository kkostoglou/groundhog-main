@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" (
    start "Groundhog Desktop" ".venv\Scripts\pythonw.exe" "GroundhogDesktopGUI.py"
    exit /b 0
)

where pyw >nul 2>nul
if not errorlevel 1 (
    start "Groundhog Desktop" pyw -3 "GroundhogDesktopGUI.py"
    exit /b 0
)

echo Python was not found.
echo Install Python 3, create the .venv, and install the requirements first.
echo See USER_GUIDE.md for detailed instructions.
pause
exit /b 1
