@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
title Hong Ming Global PM Portal - Contract ^& Document Hub

echo ==============================================================================
echo    KHOI DONG HONG MING GLOBAL PM PORTAL (PYTHON 3.12)
echo ==============================================================================
echo.

cd /d "%~dp0"

REM Kiem tra va uu tien Python 3.12
py -3.12 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [*] Tim thay Python 3.12. Dang khoi dong server tren cong 8032...
    start "" http://127.0.0.1:8032/contracts
    py -3.12 run.py
) else (
    echo [*] Su dung python mac dinh tren he thong tren cong 8032...
    start "" http://127.0.0.1:8032/contracts
    python run.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Co loi xay ra khi chay chuong trinh.
    pause
)
