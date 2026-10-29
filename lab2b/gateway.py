"""Passerelle d'API : point d'entrée unique de MiniPay."""
import os
import requests
from flask import Flask, Response, jsonify, request

SERVICES = {
    "compte": os.environ.get("COMPTE_URL", "http://compte:5001"),
    "paiement": os.environ.get("PAIEMENT_URL", "http://paiement:5002"),
    "notification": os.environ.get("NOTIF_URL", "http://notification:5003"),
}
app = Flask(__name__)


def relayer(service, methode, chemin, corps=None):
    try:
        r = requests.request(methode, SERVICES[service] + chemin, json=corps, timeout=3)
        return Response(r.content, r.status_code, {"Content-Type": "application/json"})
    except requests.RequestException:
        return jsonify(erreur="service indisponible : " + service), 503


@app.get("/sante")
def sante():
    etat = {}
    for nom, url in SERVICES.items():
        try:
            etat[nom] = "up" if requests.get(url + "/sante", timeout=1).status_code == 200 else "down"
        except requests.RequestException:
            etat[nom] = "down"
    return jsonify(etat)


@app.get("/solde/<compte>")
def solde(compte):
    return relayer("compte", "GET", "/solde/" + compte)


@app.post("/payer")
def payer():
    return relayer("paiement", "POST", "/payer", request.get_json())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), threaded=True)
