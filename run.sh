#!/usr/bin/env bash
set -e

echo "==================================================="
echo "  Evidence-Grounded AI Research Assistant"
echo "==================================================="

if [ ! -f .env ] && [ -f .env.example ]; then
    echo "Copying .env.example to .env..."
    cp .env.example .env
fi

if command -v uv >/dev/null 2>&1; then
    if [ ! -d .venv ]; then
        echo "Creating virtual environment with uv..."
        uv venv .venv
    fi
    echo "Ensuring dependencies are installed..."
    uv pip install -r requirements.txt --quiet
    .venv/bin/python run_app.py
else
    if [ ! -d .venv ]; then
        echo "Creating virtual environment with python..."
        python3 -m venv .venv
    fi
    echo "Ensuring dependencies are installed..."
    .venv/bin/pip install -r requirements.txt --quiet
    .venv/bin/python run_app.py
fi

