#!/usr/bin/env python3
"""Serveur TCP minimal : lit une ligne JSON, répond une ligne JSON.
Usage : python3 tcp_serveur.py [port]"""
import json, socket, sys, threading

def traiter(conn):
    with conn, conn.makefile("rw", encoding="utf-8") as f:
        for ligne in f:                       # TCP est un flux : on délimite par '\n'
            req = json.loads(ligne)
            rep = {"ok": True, "echo": req, "solde": 1_000_000 - req.get("montant", 0)}
            f.write(json.dumps(rep) + "\n"); f.flush()

def main(port):
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port)); s.listen(16)
    print("TCP en écoute sur", port, flush=True)
    while True:
        conn, adr = s.accept()
        threading.Thread(target=traiter, args=(conn,), daemon=True).start()

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6000)
