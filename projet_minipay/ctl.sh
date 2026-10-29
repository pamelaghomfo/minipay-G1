#!/usr/bin/env bash
# ./ctl.sh start|stop <service> : démarre ou arrête un service local (utilisé par le chaos_runner en mode local)
cd "$(dirname "$0")"; mkdir -p run
act=$1; s=$2
case $s in compte) port=5001;; paiement) port=5002;; notification) port=5003;; gateway) port=8080;; *) echo "service inconnu"; exit 1;; esac
export COMPTE_URL=http://127.0.0.1:5001 PAIEMENT_URL=http://127.0.0.1:5002 NOTIF_URL=http://127.0.0.1:5003
case $act in
  start)
    [ -f run/$s.pid ] && kill -0 $(cat run/$s.pid) 2>/dev/null && exit 0
    DB=run/$s.db LOG=run/$s.log PORT=$port nohup python3 $s.py > run/$s.out 2>&1 &
    echo $! > run/$s.pid
    for i in $(seq 1 50); do curl -s -o /dev/null localhost:$port/sante && exit 0; sleep 0.2; done ;;
  stop)
    [ -f run/$s.pid ] && kill -9 $(cat run/$s.pid) 2>/dev/null; rm -f run/$s.pid ;;
esac
