@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Instalacija (radi se samo jednom) ===
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo [1/3] Instaliram Git...
  winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements
) else (
  echo [1/3] Git vec postoji.
)

where py >nul 2>nul
if errorlevel 1 (
  echo [2/3] Instaliram Python...
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  where py >nul 2>nul
  if errorlevel 1 (
    echo.
    echo Python je instaliran, ali ovaj prozor ga jos ne vidi.
    echo Zatvori ovaj prozor i ponovo pokreni setup.bat
    pause
    exit /b 1
  )
) else (
  echo [2/3] Python vec postoji.
)

echo [3/3] Instaliram Python biblioteke...
py -3 -m pip install --upgrade pip
py -3 -m pip install -r requirements.txt
if errorlevel 1 (
  echo GRESKA pri instalaciji biblioteka.
  pause
  exit /b 1
)

py -3 -m lidovi --help >nul
if errorlevel 1 (
  echo GRESKA: alat ne radi. Posalji ovu poruku Claude-u.
) else (
  echo.
  echo GOTOVO. Python deo radi.
)

where claude >nul 2>nul
if errorlevel 1 (
  echo.
  echo Claude Code nije pronadjen. Instaliraj ga u PowerShell-u:
  echo     irm https://claude.ai/install.ps1 ^| iex
)
echo.
pause
