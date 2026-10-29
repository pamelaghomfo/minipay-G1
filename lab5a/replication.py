"""Réplication : magasin à quorums (sans leader) et réplication asynchrone primaire-secondaires.

Magasin(n, w, r) : n répliques ; une écriture réussit si au moins w répliques l'acceptent ;
une lecture interroge r répliques vivantes tirées au hasard et renvoie la version la plus récente.
Si r + w > n, toute lecture rencontre au moins une réplique qui a vu la dernière écriture réussie.
"""
import random


class Magasin:
    def __init__(self, n=3, w=2, r=2, graine=0):
        self.n, self.w, self.r = n, w, r
        self.rng = random.Random(graine)
        self.rep = [{} for _ in range(n)]            # cle -> (version, valeur)
        self.vivant = [True] * n
        self.version = 0

    def tomber(self, i): self.vivant[i] = False
    def revenir(self, i): self.vivant[i] = True       # sans rattrapage : la réplique reste en retard

    def ecrire(self, cle, valeur):
        self.version += 1
        acks = 0
        for i in range(self.n):
            if self.vivant[i]:
                self.rep[i][cle] = (self.version, valeur); acks += 1
        return acks >= self.w

    def lire(self, cle, reparation=False):
        vivants = [i for i in range(self.n) if self.vivant[i]]
        if len(vivants) < self.r: return None            # lecture impossible : quorum indisponible
        choisies = self.rng.sample(vivants, self.r)
        meilleure = max((self.rep[i].get(cle, (0, None)) for i in choisies), key=lambda t: t[0])
        if reparation:                                   # réparation à la lecture
            for i in choisies: self.rep[i][cle] = meilleure
        return meilleure[1]


class PrimaireSecondaires:
    """Réplication asynchrone : le primaire répond tout de suite ; les secondaires reçoivent
    l'écriture 'retard' ms plus tard. Le temps est fourni par l'appelant (en ms)."""

    def __init__(self, secondaires=2, retard=100):
        self.retard = retard
        self.primaire = {}
        self.secondaires = [{} for _ in range(secondaires)]
        self.en_route = []                               # (instant d'arrivée, cle, version, valeur)
        self.version = 0

    def ecrire(self, t, cle, valeur):
        self.version += 1
        self.primaire[cle] = (self.version, valeur)
        self.en_route.append((t + self.retard, cle, self.version, valeur))
        return self.version

    def _livrer(self, t):
        for e in [e for e in self.en_route if e[0] <= t]:
            for s in self.secondaires: s[e[1]] = (e[2], e[3])
            self.en_route.remove(e)

    def lire(self, t, cle, sur="secondaire", jeton=0):
        """sur = 'primaire' ou 'secondaire'. Avec un jeton (dernière version écrite par ce client),
        on ne lit sur un secondaire que s'il a rattrapé cette version (lecture de ses propres écritures)."""
        self._livrer(t)
        if sur == "primaire": return self.primaire.get(cle, (0, None))[1]
        s = self.secondaires[0]
        if jeton and s.get(cle, (0, None))[0] < jeton:
            return self.primaire.get(cle, (0, None))[1]
        return s.get(cle, (0, None))[1]
