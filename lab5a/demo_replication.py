#!/usr/bin/env python3
"""Trois expériences sur la réplication. Usage : python3 demo_replication.py"""
from replication import Magasin, PrimaireSecondaires

print("== 1. Quorums : n=3, une réplique manque l'écriture, 1000 lectures ==")
for w, r in ((1, 1), (2, 1), (1, 2), (2, 2)):
    perimees = 0
    for g in range(1000):
        m = Magasin(3, w, r, g); m.ecrire("solde", 100)
        m.tomber(1); m.tomber(2) if w == 1 else None
        m.ecrire("solde", 150)
        m.revenir(1); m.revenir(2)
        perimees += m.lire("solde") != 150
    print("  w=%d r=%d (w+r=%d %s n) : lectures périmées %4d / 1000" % (w, r, w + r, ">" if w + r > 3 else "<=", perimees))

print("\n== 2. Primaire et secondaires (retard de réplication 100 ms) ==")
p = PrimaireSecondaires(retard=100)
p.ecrire(-200, "solde", 100)        # valeur initiale, déjà répliquée
v = p.ecrire(0, "solde", 150)
print("  t=10 ms, lecture sur le secondaire  :", p.lire(10, "solde", sur="secondaire"), "(ancienne valeur)")
print("  t=10 ms, lecture sur le primaire    :", p.lire(10, "solde", sur="primaire"))
print("  t=10 ms, secondaire avec jeton      :", p.lire(10, "solde", jeton=v), "(lecture de ses propres écritures)")
print("  t=200 ms, lecture sur le secondaire :", p.lire(200, "solde"))
