#!/usr/bin/env bash
# Lance MiniPay en processus locaux (sans Docker) : ./lancer_local.sh [dossier_du_code]
# Journaux et bases dans ./run. Arrêt/démarrage d'un service : ./ctl.sh stop|start compte|paiement|notification|gateway
cd "$(dirname "$0")"; mkdir -p run
export COMPTE_URL=http://127.0.0.1:5001 PAIEMENT_URL=http://127.0.0.1:5002 NOTIF_URL=http://127.0.0.1:5003
for s in compte paiement notification gateway; do ./ctl.sh start $s; done
echo "MiniPay démarré : curl localhost:8080/sante"
