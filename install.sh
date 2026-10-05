#!/bin/bash

# Spostati nella cartella in cui si trova lo script
cd "$(dirname "$0")"

echo "==================================================="
echo "      STUDY TOOL - INSTALLAZIONE SISTEMA"
echo "==================================================="
echo ""

# --- 1. VERIFICA PYTHON ---
echo "[1/4] Verifica presenza di Python3..."
if ! command -v python3 &> /dev/null; then
    echo "[ERRORE] Python3 non è installato."
    echo "Installalo usando il gestore pacchetti del tuo sistema (es. 'sudo apt install python3 python3-venv' su Ubuntu o 'brew install python' su Mac)."
    exit 1
fi
echo "Python3 trovato con successo."
echo ""

# --- 2. AMBIENTE VIRTUALE E DIPENDENZE ---
echo "[2/4] Creazione ambiente virtuale isolato (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "Aggiornamento pip e installazione librerie (requirements.txt)..."
pip install --upgrade pip >/dev/null 2>&1
pip install -r requirements.txt
echo "Dipendenze Python installate."
echo ""

# --- 3. VERIFICA OLLAMA ---
echo "[3/4] Verifica presenza di Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "Ollama non trovato. Avvio installazione ufficiale in background..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama trovato."
fi
echo ""

# --- 4. DOWNLOAD MODELLO E PERMESSI ---
echo "[4/4] Avvio server Ollama e download del modello IA..."
# Avvia il server in background per permettere il pull
nohup ollama serve >/dev/null 2>&1 &
sleep 3
ollama pull gemma4:e4b

echo ""
echo "Impostazione permessi di esecuzione per gli script..."
chmod +x StudyTool.sh
# Nel caso l'utente avesse avviato questo file con 'bash install.sh', gli diamo i permessi per il futuro
chmod +x install.sh

echo "==================================================="
echo "  SETUP COMPLETATO CON SUCCESSO!"
echo "  Ora puoi avviare il programma eseguendo: ./StudyTool.sh"
echo "==================================================="