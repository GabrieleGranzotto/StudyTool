@echo off
cd /d "%~dp0"

echo ===================================================
echo       STUDY TOOL - INIZIALIZZAZIONE SISTEMA
echo ===================================================
echo.

:: --- SEZIONE OLLAMA ---
echo [1/3] Avvio del server Ollama in background (se chiuso)...
start /b ollama serve >nul 2>&1
echo ...done!

:: --- AMBIENTE VIRTUALE ---
echo [2/3] Controllo e installazione delle dipendenze...
pip install -q -r requirements.txt
echo ...done!

echo [3/3] Avvio dell'interfaccia grafica. Buono studio!
start pythonw gui.py
echo ===================================================