@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Lidovi: 50 novih lidova ===
echo.
set /p DELATNOST=Delatnost (npr. frizer, vodoinstalater, auto servis): 
set /p GRAD=Grad (npr. Beograd, Novi Sad, Nis): 
if "%DELATNOST%"=="" goto prazno
if "%GRAD%"=="" goto prazno

echo.
echo Pokrecem Claude Code sa Chrome-om... (Chrome mora biti otvoren)
claude --chrome "/lidovi delatnost: %DELATNOST%, grad: %GRAD%"
goto kraj

:prazno
echo Delatnost i grad su obavezni.
:kraj
pause
