#!/bin/bash

# Spostati nella cartella in cui si trova lo script
cd "$(dirname "$0")"

echo "==================================================="
echo "      STUDY TOOL - INIZIALIZZAZIONE SISTEMA"
echo "==================================================="
echo ""

# --- SEZIONE OLLAMA ---
echo "[1/3] Avvio del server Ollama in background (se chiuso)..."
# 'nohup' e '&' servono per avviare il processo in background senza bloccare il terminale
nohup ollama serve >/dev/null 2>&1 &
echo "...done!"

# --- AMBIENTE VIRTUALE ---
# Se usi un ambiente virtuale (venv), decommenta la riga qui sotto:
# source venv/bin/activate

echo "[2/3] Controllo e installazione delle dipendenze..."
pip3 install -q -r requirements.txt
echo "...done!"

echo "[3/3] Avvio dell'interfaccia grafica. Buono studio!"
# Su Linux/Mac si usa generalmente python3. La '&' finale lo avvia scollegato dal terminale
python3 gui.py &

echo "==================================================="