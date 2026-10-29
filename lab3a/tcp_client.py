#!/usr/bin/env python3
"""Client TCP : envoie N requêtes sur UNE connexion puis sur N connexions, et compare.
Usage : python3 tcp_client.py [port] [N]"""
import json, socket, sys, time

port = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
N = int(sys.argv[2]) if len(sys.argv) > 2 else 200

def une_connexion():
    t = time.perf_counter()
    with socket.create_connection(("127.0.0.1", port), timeout=2) as s, s.makefile("rw", encoding="utf-8") as f:
        for i in range(N):
            f.write(json.dumps({"id": i, "montant": 10}) + "\n"); f.flush()
            f.readline()
    return (time.perf_counter() - t) * 1000

def n_connexions():
    t = time.perf_counter()
    for i in range(N):
        with socket.create_connection(("127.0.0.1", port), timeout=2) as s, s.makefile("rw", encoding="utf-8") as f:
            f.write(json.dumps({"id": i, "montant": 10}) + "\n"); f.flush()
            f.readline()
    return (time.perf_counter() - t) * 1000

a, b = une_connexion(), n_connexions()
print("%d requêtes, une connexion : %.1f ms (%.2f ms/req)" % (N, a, a / N))
print("%d requêtes, une connexion chacune : %.1f ms (%.2f ms/req)" % (N, b, b / N))
print("rapport : x%.1f" % (b / a))
