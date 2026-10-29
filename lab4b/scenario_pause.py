#!/usr/bin/env python3
"""Le client A prend le verrou, subit une longue pause (ramasse-miettes, réseau, VM suspendue),
le bail expire, B prend le verrou et écrit, puis A se réveille et écrit à son tour.
Usage : python3 scenario_pause.py            (horloge simulée, instantané)"""
from verrou import ServiceVerrou, Stockage

def jouer(avec_cloture):
    t = {"now": 0.0}
    v = ServiceVerrou(horloge=lambda: t["now"])
    s = Stockage(avec_cloture)
    ja = v.acquerir("A", bail=10)
    print("  t=0   A obtient le verrou (jeton %d)" % ja)
    t["now"] = 15                                           # A est en pause : le bail expire
    jb = v.acquerir("B", bail=10)
    print("  t=15  le bail de A a expiré ; B obtient le verrou (jeton %d)" % jb)
    s.ecrire(jb, "ecriture de B")
    print("  t=16  B écrit")
    ok = s.ecrire(ja, "ecriture de A (périmée)")
    print("  t=20  A se réveille, croit toujours détenir le verrou et écrit :", "ACCEPTÉ" if ok else "REFUSÉ")
    print("  valeur finale :", s.valeur)

print("Sans jeton de clôture :"); jouer(False)
print("\nAvec jeton de clôture :"); jouer(True)
