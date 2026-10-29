"""Service notification : enregistre les notifications (simulation d'un SMS)."""
import os
from flask import Flask, jsonify, request

LOG = os.environ.get("LOG", "notifications.log")
app = Flask(__name__)


@app.get("/sante")
def sante():
    return jsonify(ok=True)


@app.post("/notifier")
def notifier():
    d = request.get_json()
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("SMS a %s : paiement de %s FCFA\n" % (d.get("compte"), d.get("montant")))
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5003)), threaded=True)
