#!/usr/bin/env python3
"""Service notification : simule l'envoi d'un SMS (idempotent par identifiant de virement).
  GET /sante   POST /notifier {"id": "...", "de": "c1", "vers": "c2", "montant": 100}   GET /envoyes"""
import os, threading
from flask import Flask, jsonify, request
app = Flask(__name__)
VUS, verrou = {}, threading.Lock()
FICHIER = os.environ.get("LOG", "notifications.log")

@app.get("/sante")
def sante(): return jsonify(ok=True, service="notification")

@app.post("/notifier")
def notifier():
    d = request.get_json()
    with verrou:
        if d["id"] in VUS: return jsonify(ok=True, deja=True)
        VUS[d["id"]] = d
        with open(FICHIER, "a", encoding="utf-8") as f:
            f.write("SMS : %s a envoyé %s FCFA à %s (virement %s)\n" % (d["de"], d["montant"], d["vers"], d["id"]))
    return jsonify(ok=True, deja=False)

@app.get("/envoyes")
def envoyes(): return jsonify(nombre=len(VUS))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5003)), threaded=True)
