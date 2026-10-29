#!/usr/bin/env python3
"""Publie N événements « paiement_effectue » dans la file 'paiements'.
Usage : python3 producteur.py [N] [URL_courtier]"""
import sys, uuid, requests
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
URL = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:7000"
for i in range(N):
    ev = {"id": "ev-%s" % uuid.uuid4().hex[:8], "compte": "awa", "montant": 100 * (i + 1)}
    r = requests.post(URL + "/publier/paiements", json=ev, timeout=2)
    print("publié", ev["id"], "->", r.json())
