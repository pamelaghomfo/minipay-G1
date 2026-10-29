"""Test de charge simple (bibliothèque standard uniquement).

Usage : python3 charge.py http://127.0.0.1:5001 [nb_requetes] [nb_clients]
Envoie des paiements de 1 FCFA avec des identifiants uniques et mesure
le débit, la latence moyenne et le nombre d'erreurs.
"""
import json, sys, threading, time, urllib.request, uuid

base = sys.argv[1].rstrip("/")
total = int(sys.argv[2]) if len(sys.argv) > 2 else 200
clients = int(sys.argv[3]) if len(sys.argv) > 3 else 10
latences, erreurs, verrou = [], [0], threading.Lock()


def travailleur(n):
    for _ in range(n):
        corps = json.dumps({"compte": "awa", "montant": 1, "id": uuid.uuid4().hex}).encode()
        req = urllib.request.Request(base + "/payer", data=corps, headers={"Content-Type": "application/json"})
        t0 = time.perf_counter()
        try:
            urllib.request.urlopen(req, timeout=5).read()
            ok = True
        except Exception:
            ok = False
        dt = (time.perf_counter() - t0) * 1000
        with verrou:
            latences.append(dt)
            if not ok:
                erreurs[0] += 1


t0 = time.time()
fils = [threading.Thread(target=travailleur, args=(total // clients,)) for _ in range(clients)]
[f.start() for f in fils]
[f.join() for f in fils]
duree = time.time() - t0
n = len(latences)
print("requetes : %d, erreurs : %d" % (n, erreurs[0]))
print("debit : %.1f req/s" % (n / duree))
print("latence moyenne : %.1f ms" % (sum(latences) / n))
