#!/usr/bin/env python3
"""Combien de clés changent de nœud quand on passe de 4 à 5 nœuds ?
Usage : python3 demo_anneau.py [nombre_de_cles] [noeuds_virtuels]"""
import sys
from collections import Counter
from anneau import Anneau, modulo

K = int(sys.argv[1]) if len(sys.argv) > 1 else 10000
V = int(sys.argv[2]) if len(sys.argv) > 2 else 100
cles = ["compte-%d" % i for i in range(K)]
avant4 = ["n%d" % i for i in range(4)]; apres5 = avant4 + ["n4"]

bouge = sum(modulo(avant4, c) != modulo(apres5, c) for c in cles)
print("modulo         : %5.1f %% des clés changent de nœud" % (100 * bouge / K))
a = Anneau(avant4, V); avant = {c: a.responsable(c) for c in cles}
a.ajouter("n4")
bouge = sum(avant[c] != a.responsable(c) for c in cles)
print("anneau (V=%3d) : %5.1f %% des clés changent de nœud (idéal : %.1f %%)" % (V, 100 * bouge / K, 100 / 5))
charge = Counter(a.responsable(c) for c in cles)
print("charge par nœud :", dict(sorted(charge.items())), " rapport max/min : %.2f" % (max(charge.values()) / min(charge.values())))
