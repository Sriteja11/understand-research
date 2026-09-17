@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   Evidence-Grounded AI Research Assistant
echo ===================================================

if not exist .env (
    if exist .env.example (
        echo Copying .env.example to .env...
        copy .env.example .env >nul
    )
)

where uv >nul 2>nul
if %ERRORLEVEL% equ 0 (
    if not exist .venv (
        echo Creating virtual environment with uv...
        uv venv .venv
    )
    echo Ensuring dependencies are installed...
    uv pip install -r requirements.txt --quiet
    .\.venv\Scripts\python run_app.py
) else (
    if not exist .venv (
        echo Creating virtual environment with python...
        python -m venv .venv
    )
    echo Ensuring dependencies are installed...
    .\.venv\Scripts\python -m pip install -r requirements.txt --quiet
    .\.venv\Scripts\python run_app.py
)

