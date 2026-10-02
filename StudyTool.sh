#!/bin/bash
cd "$(dirname "$0")"

# Installa le librerie silenziosamente se mancano
pip install -q -r requirements.txt

# Avvia l'interfaccia grafica in background e chiudi lo script
python3 gui.py &