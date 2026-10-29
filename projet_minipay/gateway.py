#!/usr/bin/env python3
"""Passerelle d'API de MiniPay (port 8080). Contrat public :
  GET  /sante                                   -> 200 si la plateforme répond
  GET  /solde/<compte>                          -> {"compte": "c1", "solde": 100000}
  POST /virement {"id","de","vers","montant"}   -> {"statut": "TERMINEE" | "REFUSEE" | "COMPENSEE" | "EN_COURS"}
Statuts : TERMINEE (200), REFUSEE ou COMPENSEE (409, aucun effet), EN_COURS (503, se terminera plus tard,
rejouer avec le même id). Le contrat est le même pour toutes les équipes : le chaos_runner s'y appuie."""
import os, requests
from flask import Flask, jsonify, request

PAIEMENT = os.environ.get("PAIEMENT_URL", "http://127.0.0.1:5002")
COMPTE = os.environ.get("COMPTE_URL", "http://127.0.0.1:5001")
NOTIF = os.environ.get("NOTIF_URL", "http://127.0.0.1:5003")
app = Flask(__name__)


def appel(m, url, **kw):
    try:
        r = requests.request(m, url, timeout=kw.pop("timeout", 5), **kw)
        return r.json(), r.status_code
    except (requests.RequestException, ValueError):
        return None, 503


@app.get("/sante")
def sante():
    etat = {}
    for nom, u in (("compte", COMPTE), ("paiement", PAIEMENT), ("notification", NOTIF)):
        j, c = appel("GET", u + "/sante", timeout=1); etat[nom] = (c == 200)
    critique = etat["compte"] and etat["paiement"]
    return jsonify(ok=critique, services=etat), (200 if critique else 503)


@app.get("/solde/<c>")
def solde(c):
    j, code = appel("GET", COMPTE + "/solde/" + c, timeout=2)
    return (jsonify(j), code) if j is not None else (jsonify(erreur="service compte indisponible"), 503)


@app.post("/virement")
def virement():
    j, code = appel("POST", PAIEMENT + "/virement", json=request.get_json(), timeout=8)
    return (jsonify(j), code) if j is not None else (jsonify(statut="EN_COURS", erreur="service paiement indisponible"), 503)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), threaded=True)
