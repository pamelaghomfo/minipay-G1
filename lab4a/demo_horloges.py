#!/usr/bin/env python3
"""Affiche, pour un scénario de trois processus, les estampilles de Lamport et vectorielles.
Usage : python3 demo_horloges.py"""
from horloges import lamport, vecteurs, comparer

TRACE = [
    ("local", 0), ("envoi", 0, "m1"), ("local", 2), ("reception", 1, "m1"),
    ("envoi", 1, "m2"), ("envoi", 2, "m3"), ("reception", 0, "m3"), ("reception", 2, "m2"),
]
L, V = lamport(TRACE, 3), vecteurs(TRACE, 3)
print("%-3s %-22s %-8s %s" % ("#", "événement", "Lamport", "vectorielle"))
for i, ev in enumerate(TRACE):
    print("%-3d %-22s %-8d %s" % (i, ev, L[i], V[i]))
print("\nPaires d'événements concurrents (vectorielles) :")
for i in range(len(TRACE)):
    for j in range(i + 1, len(TRACE)):
        if comparer(V[i], V[j]) == "concurrent":
            print("  #%d || #%d   (estampilles %d et %d : Lamport seul ne permet pas de le savoir)" % (i, j, L[i], L[j]))
