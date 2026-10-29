"""Lab 2A : répartiteur de charge minimal (round-robin avec reprise sur panne).

Usage : python3 lb.py 8000 5001 5002
        (port d'écoute, puis ports des instances)
"""
import itertools, sys
import requests
from flask import Flask, Response, request

ECOUTE = int(sys.argv[1])
CIBLES = ["http://127.0.0.1:%s" % p for p in sys.argv[2:]]
tour = itertools.cycle(range(len(CIBLES)))
app = Flask(__name__)


@app.route("/<path:chemin>", methods=["GET", "POST"])
def relayer(chemin):
    debut = next(tour)                         # instance de départ (round-robin)
    for i in range(len(CIBLES)):               # essaie chaque instance au plus une fois
        cible = CIBLES[(debut + i) % len(CIBLES)]
        try:
            r = requests.request(request.method, cible + "/" + chemin, json=request.get_json(silent=True), timeout=3)
            return Response(r.content, r.status_code, {"Content-Type": r.headers.get("Content-Type", "application/json")})
        except requests.RequestException:
            continue                           # instance en panne : on passe à la suivante
    return Response('{"erreur": "aucune instance disponible"}', 503, {"Content-Type": "application/json"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=ECOUTE, threaded=True)
