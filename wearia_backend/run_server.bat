@echo off
title Serveur Backend Wearia
cd /d "%~dp0"
echo ======================================================
echo    Demarrage du serveur Backend Wearia (FastAPI)
echo ======================================================
echo.
echo Configuration du pont USB Android (adb reverse)...
where adb >nul 2>&1 && adb reverse tcp:8000 tcp:8000
if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" (
    "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" reverse tcp:8000 tcp:8000
)
echo.
echo Documentation Swagger : http://localhost:8000/docs
echo IP pour telephone reel: http://0.0.0.0:8000
echo.

if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
) else (
    python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
)

pause

