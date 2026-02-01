@echo off
cd /d "%~dp0"

REM Ensure venv exists
if not exist ".venv\Scripts\python.exe" (
  echo Vytvarim virtualni prostredi...
  python -m venv .venv
)

REM Activate venv
call ".venv\Scripts\activate.bat"

REM Install dependencies + PyInstaller into venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

REM Build EXE
python -m PyInstaller --noconsole --onedir --name Lawmate main.py --clean

REM Copy .env next to exe if present
if exist ".env" (
  copy /Y ".env" "dist\Lawmate\.env" >nul
)

echo.
echo Hotovo. Vystup najdes v dist\Lawmate\
pause
