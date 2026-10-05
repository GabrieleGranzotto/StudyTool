@echo off
cd /d "%~dp0"
title Setup StudyTool

echo ===================================================
echo       STUDY TOOL - INSTALLAZIONE SISTEMA
echo ===================================================
echo.

:: --- 1. VERIFICA PYTHON ---
echo [1/4] Verifica presenza di Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRORE] Python non e' installato o non e' nelle variabili d'ambiente (PATH).
    echo Scarica Python da https://www.python.org/downloads/
    echo Assicurati di spuntare "Add Python to PATH" durante l'installazione!
    echo.
    pause
    exit /b
)
echo Python trovato con successo.
echo.

:: --- 2. AMBIENTE VIRTUALE E DIPENDENZE ---
echo [2/4] Creazione ambiente virtuale isolato (venv)...
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate

echo Aggiornamento pip e installazione librerie (requirements.txt)...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
echo Dipendenze Python installate.
echo.

:: --- 3. VERIFICA OLLAMA ---
echo [3/4] Verifica presenza di Ollama...
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Ollama non trovato. Avvio installazione tramite Windows Package Manager (winget)...
    winget install Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
    
    echo.
    echo [ATTENZIONE] Ollama e' stato installato. 
    echo Per permettere al sistema di riconoscerlo, CHIUDI QUESTA FINESTRA, 
    echo riavvia il computer (o fai logout/login) e avvia di nuovo questo file install.bat.
    pause
    exit /b
)
echo Ollama trovato.
echo.

:: --- 4. DOWNLOAD MODELLO ---
echo [4/4] Download del modello IA...
echo (L'operazione potrebbe richiedere alcuni minuti in base alla connessione)
:: Assicurati che il server sia acceso per il download
start /b ollama serve >nul 2>&1
timeout /t 3 >nul
ollama pull gemma4:e4b
echo.

echo ===================================================
echo  SETUP COMPLETATO CON SUCCESSO!
echo  Ora puoi avviare il programma usando StudyTool.bat
echo ===================================================
pause