"""Service paiement : orchestre un paiement (idempotent) et notifie."""
import os, sqlite3
import requests
from flask import Flask, jsonify, request

DB = os.environ.get("DB", "paiement.db")
COMPTE_URL = os.environ.get("COMPTE_URL", "http://compte:5001")
NOTIF_URL = os.environ.get("NOTIF_URL", "http://notification:5003")
app = Flask(__name__)


def sql(requete, args=(), ecriture=False):
    c = sqlite3.connect(DB)
    try:
        c.execute("CREATE TABLE IF NOT EXISTS paiements(id TEXT PRIMARY KEY, compte TEXT, montant INTEGER)")
        cur = c.execute(requete, args)
        res = cur.fetchall()
        if ecriture:
            c.commit()
        return res
    finally:
        c.close()


@app.get("/sante")
def sante():
    return jsonify(ok=True)


@app.post("/payer")
def payer():
    d = request.get_json()
    if sql("SELECT id FROM paiements WHERE id=?", (d["id"],)):
        return jsonify(ok=True, deja_traite=True)           # idempotence : doublon ignoré
    try:
        r = requests.post(COMPTE_URL + "/debiter", json=d, timeout=2)
    except requests.RequestException:
        return jsonify(erreur="service compte indisponible"), 503
    if r.status_code != 200:
        return jsonify(erreur="débit refusé"), 409
    sql("INSERT INTO paiements VALUES(?,?,?)", (d["id"], d["compte"], d["montant"]), ecriture=True)
    try:                                                    # notification facultative : mode dégradé
        requests.post(NOTIF_URL + "/notifier", json=d, timeout=1)
    except requests.RequestException:
        pass
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5002)), threaded=True)
