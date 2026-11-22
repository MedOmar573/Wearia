@echo off
title Backend Wearia (FastAPI)
color 0B
echo ==========================================================
echo           Lancement du serveur Backend Wearia
echo ==========================================================
echo.

cd /d "%~dp0wearia_backend"

if not exist "venv\Scripts\python.exe" (
    echo [ERREUR] L'environnement virtuel (venv) est introuvable dans wearia_backend !
    pause
    exit /b 1
)

echo Environnement virtuel detecte.
echo Demarrage du serveur Uvicorn sur http://0.0.0.0:8000 ...
echo Documentation Swagger : http://localhost:8000/docs
echo (Appuyez sur CTRL+C pour arreter le serveur)
echo.

venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo ==========================================================
echo Le serveur s'est arrete.
echo ==========================================================
pause
