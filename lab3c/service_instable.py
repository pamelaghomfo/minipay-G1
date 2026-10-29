#!/usr/bin/env python3
"""Service de notification instable, pour expérimenter.
Usage : python3 service_instable.py [port] [taux_erreur_%] [latence_ms]
  GET /notifier -> 200 ou 500 (au hasard) après la latence indiquée
  POST /reglage  {"erreur": 100, "latence": 0} -> change le comportement à chaud"""
import random, sys, time
from flask import Flask, jsonify, request
app = Flask(__name__)
R = {"erreur": float(sys.argv[2]) if len(sys.argv) > 2 else 30.0,
     "latence": float(sys.argv[3]) if len(sys.argv) > 3 else 0.0, "appels": 0}

@app.get("/notifier")
def notifier():
    R["appels"] += 1
    time.sleep(R["latence"] / 1000)
    if random.random() * 100 < R["erreur"]:
        return jsonify(erreur="panne simulée"), 500
    return jsonify(ok=True)

@app.post("/reglage")
def reglage():
    R.update(request.get_json()); return jsonify(R)

@app.get("/compteur")
def compteur():
    return jsonify(R)

if __name__ == "__main__":
    app.run(port=int(sys.argv[1]) if len(sys.argv) > 1 else 7100, threaded=True)
