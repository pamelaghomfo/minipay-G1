#!/usr/bin/env python3
"""Service paiement : VERSION DE DÉPART (naïve). C'est à votre équipe de la rendre résiliente.

Ce qui manque, dans l'ordre où le chaos_runner le sanctionne :
  1. Idempotence : un même 'id' rejoué ne doit produire qu'un seul effet (chapitres 1 et 3).
  2. Saga avec journal persistant : débit, crédit, reprise après crash, compensation (chapitre 5).
  3. Réessais avec recul et gigue, délais d'attente, disjoncteur (chapitre 3).
  4. Notification facultative : ne doit jamais bloquer ni faire échouer un virement (chapitre 2).
  5. Réponses rapides et statuts conformes au contrat, même en panne (voir gateway.py).
"""
import os, uuid, requests
from flask import Flask, jsonify, request

COMPTE = os.environ.get("COMPTE_URL", "http://127.0.0.1:5001")
NOTIF = os.environ.get("NOTIF_URL", "http://127.0.0.1:5003")
app = Flask(__name__)


@app.get("/sante")
def sante():
    return jsonify(ok=True, service="paiement")


@app.post("/virement")
def virement():
    d = request.get_json()
    # TODO 1 : retrouver l'id dans un journal persistant et répondre sans rejouer
    r = requests.post(COMPTE + "/debiter", json={"cle": uuid.uuid4().hex, "compte": d["de"], "montant": d["montant"]}, timeout=2)
    if r.status_code != 200:
        return jsonify(statut="REFUSEE"), 409
    # TODO 2 : si le crédit échoue ici, l'argent est perdu (pas de journal, pas de compensation)
    requests.post(COMPTE + "/crediter", json={"cle": uuid.uuid4().hex, "compte": d["vers"], "montant": d["montant"]}, timeout=2)
    # TODO 4 : appel synchrone sans protection
    requests.post(NOTIF + "/notifier", json=d, timeout=5)
    return jsonify(statut="TERMINEE")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5002)), threaded=True)
