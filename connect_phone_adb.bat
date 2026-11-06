@echo off
title Configuration USB Android (Wearia)
echo ==========================================================
echo    Connexion du telephone physique a Wearia Backend
echo ==========================================================
echo.
if exist "%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" (
    set ADB="%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"
) else (
    set ADB=adb
)

echo Verification des peripheriques connectes...
%ADB% devices
echo.
echo Activation du pont reseau USB pour le port 8000 (adb reverse)...
%ADB% reverse tcp:8000 tcp:8000
%ADB% reverse --list
echo.
echo ==========================================================
echo Si votre appareil affiche "device" et "tcp:8000 tcp:8000",
echo la connexion USB est 100%% operationnelle !
echo ==========================================================
pause

