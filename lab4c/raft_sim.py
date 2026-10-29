#!/usr/bin/env python3
"""Simulation pédagogique de Raft (élection de leader et réplication du journal).

Le temps est simulé (millisecondes) : une exécution de 20 s dure une fraction de seconde
et reste reproductible grâce à la graine aléatoire.

Usage :
    python3 raft_sim.py --scenario normal|panne_leader|partition [--noeuds 5] [--graine 1] [--verbeux]

Classe utilisable depuis un script : Cluster(n, graine) avec run(ms), leader(), crash(i),
restart(i), partition(groupes), heal(), submit(cmd), invariants().
"""
import argparse, random

SUIVEUR, CANDIDAT, LEADER = "SUIVEUR", "CANDIDAT", "LEADER"
HEARTBEAT = 50                      # ms
TIMEOUT_MIN, TIMEOUT_MAX = 150, 300  # ms, délai d'élection aléatoire
LATENCE_MIN, LATENCE_MAX = 5, 15     # ms


class Noeud:
    def __init__(self, i, n, cluster):
        self.i, self.n, self.cl = i, n, cluster
        self.terme, self.vote = 0, None
        self.journal = []                       # liste de (terme, commande) ; indices Raft à partir de 1
        self.commit = 0
        self.vivant = True
        self.redevenir_suiveur()

    # ----- état et minuteurs -----
    def redevenir_suiveur(self):
        self.etat = SUIVEUR
        self.rearmer()

    def rearmer(self):
        self.echeance = self.cl.t + self.cl.rng.randint(TIMEOUT_MIN, TIMEOUT_MAX)

    def dernier(self):
        return (self.journal[-1][0] if self.journal else 0), len(self.journal)

    def tick(self):
        if not self.vivant: return
        if self.etat == LEADER:
            if self.cl.t >= self.prochain_hb:
                self.diffuser_ae(); self.prochain_hb = self.cl.t + HEARTBEAT
        elif self.cl.t >= self.echeance:
            self.devenir_candidat()

    # ----- élection -----
    def devenir_candidat(self):
        self.etat, self.terme, self.vote, self.votes = CANDIDAT, self.terme + 1, self.i, {self.i}
        self.rearmer()
        self.cl.log("N%d devient CANDIDAT (terme %d)" % (self.i, self.terme))
        lt, li = self.dernier()
        for p in range(self.n):
            if p != self.i:
                self.cl.envoyer(self.i, p, ("RV", self.terme, self.i, li, lt))

    def devenir_leader(self):
        self.etat = LEADER
        self.cl.leaders.setdefault(self.terme, set()).add(self.i)
        self.cl.log("N%d devient LEADER (terme %d)" % (self.i, self.terme))
        self.next = {p: len(self.journal) + 1 for p in range(self.n)}
        self.match = {p: 0 for p in range(self.n)}
        self.journal.append((self.terme, "noop"))      # permet de valider les entrées des termes précédents
        self.diffuser_ae(); self.prochain_hb = self.cl.t + HEARTBEAT

    def diffuser_ae(self):
        for p in range(self.n):
            if p == self.i: continue
            prev = self.next[p] - 1
            pt = self.journal[prev - 1][0] if prev > 0 else 0
            self.cl.envoyer(self.i, p, ("AE", self.terme, self.i, prev, pt, list(self.journal[prev:]), self.commit))

    # ----- messages -----
    def recevoir(self, src, m):
        if not self.vivant: return
        genre, terme = m[0], m[1]
        if terme > self.terme:
            self.terme, self.vote = terme, None
            if self.etat != SUIVEUR: self.cl.log("N%d repasse SUIVEUR (terme %d)" % (self.i, terme))
            self.etat = SUIVEUR
            if genre != "AE": self.rearmer()
        if genre == "RV":
            _, _, cand, li, lt = m
            mt, mi = self.dernier()
            a_jour = lt > mt or (lt == mt and li >= mi)
            ok = terme == self.terme and self.vote in (None, cand) and a_jour
            if ok:
                self.vote = cand; self.rearmer()
            self.cl.envoyer(self.i, src, ("RVR", self.terme, ok))
        elif genre == "RVR":
            if self.etat == CANDIDAT and terme == self.terme and m[2]:
                self.votes.add(src)
                if len(self.votes) > self.n // 2: self.devenir_leader()
        elif genre == "AE":
            _, _, ld, prev, pt, entrees, lc = m
            if terme < self.terme:
                self.cl.envoyer(self.i, src, ("AER", self.terme, False, 0)); return
            self.etat = SUIVEUR; self.rearmer()
            if prev > 0 and (len(self.journal) < prev or self.journal[prev - 1][0] != pt):
                self.cl.envoyer(self.i, src, ("AER", self.terme, False, 0)); return
            for k, e in enumerate(entrees):
                idx = prev + k + 1
                if len(self.journal) >= idx and self.journal[idx - 1][0] != e[0]:
                    del self.journal[idx - 1:]            # conflit : on tronque
                if len(self.journal) < idx: self.journal.append(e)
            self.commit = max(self.commit, min(lc, prev + len(entrees)))
            self.cl.envoyer(self.i, src, ("AER", self.terme, True, prev + len(entrees)))
        elif genre == "AER":
            if self.etat != LEADER or terme != self.terme: return
            if m[2]:
                self.match[src] = max(self.match[src], m[3]); self.next[src] = self.match[src] + 1
                for idx in range(len(self.journal), self.commit, -1):
                    nb = 1 + sum(1 for p in range(self.n) if p != self.i and self.match[p] >= idx)
                    if self.journal[idx - 1][0] == self.terme and nb > self.n // 2:
                        self.commit = idx; break
            else:
                self.next[src] = max(1, self.next[src] - 1)


class Cluster:
    def __init__(self, n=5, graine=1, verbeux=False):
        self.n, self.t, self.rng, self.verbeux = n, 0, random.Random(graine), verbeux
        self.file, self.leaders, self.groupes, self.lignes = [], {}, None, []
        self.noeuds = [Noeud(i, n, self) for i in range(n)]

    def log(self, s):
        self.lignes.append("%6d ms  %s" % (self.t, s))
        if self.verbeux: print(self.lignes[-1])

    def communiquent(self, a, b):
        if not (self.noeuds[a].vivant and self.noeuds[b].vivant): return False
        return self.groupes is None or self.groupes[a] == self.groupes[b]

    def envoyer(self, a, b, m):
        if self.communiquent(a, b):
            self.file.append((self.t + self.rng.randint(LATENCE_MIN, LATENCE_MAX), a, b, m))

    def run(self, ms):
        fin = self.t + ms
        while self.t < fin:
            self.t += 1
            prets = [e for e in self.file if e[0] <= self.t]
            if prets:
                self.file = [e for e in self.file if e[0] > self.t]
                for _, a, b, m in sorted(prets, key=lambda e: e[0]):
                    if self.communiquent(a, b): self.noeuds[b].recevoir(a, m)
            for nd in self.noeuds: nd.tick()

    # ----- actions du scénario -----
    def leader(self):
        c = [nd for nd in self.noeuds if nd.vivant and nd.etat == LEADER]
        return max(c, key=lambda nd: nd.terme).i if c else None

    def crash(self, i):
        self.noeuds[i].vivant = False; self.log("*** N%d tombe en panne ***" % i)

    def restart(self, i):
        nd = self.noeuds[i]; nd.vivant = True; nd.redevenir_suiveur(); self.log("*** N%d redémarre ***" % i)

    def partition(self, groupes):
        self.groupes = {i: g for g, membres in enumerate(groupes) for i in membres}
        self.log("*** partition réseau : %s ***" % (groupes,))

    def heal(self):
        self.groupes = None; self.log("*** réseau rétabli ***")

    def submit(self, cmd, vers=None):
        i = self.leader() if vers is None else vers
        if i is None or self.noeuds[i].etat != LEADER: return None
        nd = self.noeuds[i]; nd.journal.append((nd.terme, cmd))
        self.log("commande %r soumise à N%d (index %d)" % (cmd, i, len(nd.journal)))
        return i, len(nd.journal)

    def commandes_validees(self):
        """Commandes (hors noop) validées chez au moins un nœud, dans l'ordre, selon le nœud le plus avancé."""
        best = max(self.noeuds, key=lambda nd: nd.commit)
        return [e[1] for e in best.journal[:best.commit] if e[1] != "noop"]

    def invariants(self):
        """Propriétés de sûreté de Raft : retourne la liste des violations (vide si tout va bien)."""
        v = []
        for terme, ls in self.leaders.items():
            if len(ls) > 1: v.append("deux leaders dans le terme %d : %s" % (terme, sorted(ls)))
        for a in self.noeuds:
            for b in self.noeuds:
                k = min(a.commit, b.commit)
                if a.journal[:k] != b.journal[:k]: v.append("journaux validés divergents entre N%d et N%d" % (a.i, b.i))
        return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="normal", choices=["normal", "panne_leader", "partition"])
    ap.add_argument("--noeuds", type=int, default=5)
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--verbeux", action="store_true", default=True)
    a = ap.parse_args()
    c = Cluster(a.noeuds, a.graine, verbeux=True)
    c.run(1500)
    for k in range(3): c.submit("cmd%d" % (k + 1)); c.run(100)
    if a.scenario == "panne_leader":
        c.crash(c.leader()); c.run(1500)
        for k in range(3, 5): c.submit("cmd%d" % (k + 1)); c.run(100)
        for nd in c.noeuds:
            if not nd.vivant: c.restart(nd.i)
        c.run(1500)
    elif a.scenario == "partition":
        ancien = c.leader(); autres = [i for i in range(a.noeuds) if i != ancien]
        c.partition([[ancien], autres]); c.submit("orpheline", vers=ancien); c.run(1500)
        for k in range(3, 5): c.submit("cmd%d" % (k + 1)); c.run(100)
        c.heal(); c.run(1500)
    else:
        c.run(1000)
    print("\nCommandes validées :", c.commandes_validees())
    for nd in c.noeuds:
        print("N%d %-8s terme %d journal %s validé=%d" % (nd.i, nd.etat, nd.terme, [e[1] for e in nd.journal], nd.commit))
    print("Violations de sûreté :", c.invariants() or "aucune")


if __name__ == "__main__":
    main()
