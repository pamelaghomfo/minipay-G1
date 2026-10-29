#!/usr/bin/env python3
"""Service de verrou et stockage exposés en HTTP (pour expérimenter avec curl).
Usage : python3 verrou_serveur.py [port] [--sans-cloture]
  POST /acquerir {"client": "A", "bail": 10}  -> {"jeton": n} ou 409
  POST /liberer  {"client": "A", "jeton": n}
  POST /ecrire   {"jeton": n, "valeur": "x"} -> 200 ou 409 (jeton périmé)
  GET  /etat"""
import sys
from flask import Flask, jsonify, request
from verrou import ServiceVerrou, Stockage

app = Flask(__name__)
V, S = ServiceVerrou(), Stockage("--sans-cloture" not in sys.argv)

@app.post("/acquerir")
def acquerir():
    d = request.get_json(); j = V.acquerir(d["client"], float(d.get("bail", 10)))
    return (jsonify(jeton=j), 200) if j else (jsonify(erreur="verrou occupé"), 409)

@app.post("/liberer")
def liberer():
    d = request.get_json(); return jsonify(ok=V.liberer(d["client"], d["jeton"]))

@app.post("/ecrire")
def ecrire():
    d = request.get_json(); ok = S.ecrire(d["jeton"], d["valeur"])
    return (jsonify(ok=True), 200) if ok else (jsonify(erreur="jeton périmé"), 409)

@app.get("/etat")
def etat():
    return jsonify(detenteur=V.detenteur, jeton=V.jeton, valeur=S.valeur, max_jeton=S.max_jeton, journal=S.journal)

if __name__ == "__main__":
    app.run(port=int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 7200)
