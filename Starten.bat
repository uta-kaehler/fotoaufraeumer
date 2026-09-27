@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Fotoaufraeumer

rem Python suchen: erst der Starter "py", dann "python"
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY (where python >nul 2>nul && set PY=python)
if not defined PY (
  echo Python ist noch nicht installiert. Bitte zuerst Schritt 1 der ANLEITUNG erledigen.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Beim ersten Start wird eingerichtet, das dauert ein paar Minuten ...
  %PY% -m venv .venv
)
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
".venv\Scripts\python.exe" fotoaufraeumer.py %*
pause
