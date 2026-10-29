#!/usr/bin/env python3
"""Scénarios de saga et de 2PC. Usage : python3 demo_saga.py"""
from saga import Comptes, Journal, Orchestrateur, Crash
from deux_pc import Participant, deux_pc

def etat(c, j): return "soldes %s, journal %d ligne(s)" % (c.soldes, len(j.lignes))

print("== 1. Succès ==")
c, j = Comptes({"awa": 10000, "paul": 5000}), Journal(); o = Orchestrateur(c, j)
print("  ", o.executer("s1", "awa", "paul", 3000), "|", etat(c, j))

print("== 2. Le crédit échoue : compensation du débit ==")
c, j = Comptes({"awa": 10000, "paul": 5000}), Journal(); o = Orchestrateur(c, j); c.panne.add("credit")
print("  ", o.executer("s2", "awa", "paul", 3000), "|", etat(c, j))

print("== 3. L'orchestrateur tombe après le débit, puis reprend ==")
c, j = Comptes({"awa": 10000, "paul": 5000}), Journal(); o = Orchestrateur(c, j)
try: o.executer("s3", "awa", "paul", 3000, crash_apres="debit")
except Crash: print("   crash ; état intermédiaire :", etat(c, j))
print("  ", o.reprendre("s3"), "|", etat(c, j))
print("  rejeu de la reprise :", o.reprendre("s3"), "|", etat(c, j), "(aucun effet en double)")

print("== 4. 2PC : le coordinateur tombe entre les deux phases ==")
ps = [Participant("compte"), Participant("journal")]
print("  ", deux_pc(ps, crash_apres_votes=True))
print("  ", [(p.nom, p.etat, "verrou" if p.verrou else "libre") for p in ps], "-> bloqués jusqu'au retour du coordinateur")
