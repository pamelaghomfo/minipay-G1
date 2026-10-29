#!/usr/bin/env python3
"""Compare trois formats pour un même paiement : JSON, JSON compact, binaire (struct).
Usage : python3 serialisation.py"""
import json, struct, time

paiement = {"id": "p-000123", "compte": "awa", "montant": 5000, "devise": "XAF", "ts": 1767225600}

def json_pretty(d): return json.dumps(d, indent=2).encode()
def json_compact(d): return json.dumps(d, separators=(",", ":")).encode()
FMT = "!8s8sIIq"   # id(8) compte(8) montant(4) devise-code(4) horodatage(8), ordre réseau
def binaire(d):
    return struct.pack(FMT, d["id"].encode(), d["compte"].encode(), d["montant"], 950, d["ts"])
def debinaire(b):
    i, c, m, dv, ts = struct.unpack(FMT, b)
    return {"id": i.rstrip(b"\0").decode(), "compte": c.rstrip(b"\0").decode(), "montant": m, "devise": "XAF" if dv == 950 else "?", "ts": ts}

assert debinaire(binaire(paiement)) == paiement
print("%-14s %8s %14s" % ("format", "octets", "ms / 100 000"))
for nom, f in (("JSON indenté", json_pretty), ("JSON compact", json_compact), ("binaire struct", binaire)):
    t = time.perf_counter()
    for _ in range(100_000): f(paiement)
    print("%-14s %8d %14.0f" % (nom, len(f(paiement)), (time.perf_counter() - t) * 1000))
print("\nCompromis : le binaire est compact et rapide mais illisible et fragile aux évolutions ;")
print("Protocol Buffers (gRPC) garde la compacité avec un schéma versionné.")
