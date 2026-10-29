"""Partitionnement par hachage : modulo versus anneau de hachage cohérent (avec nœuds virtuels)."""
import bisect, hashlib


def h(texte):
    return int(hashlib.md5(texte.encode()).hexdigest(), 16)


def modulo(noeuds, cle):
    return noeuds[h(cle) % len(noeuds)]


class Anneau:
    def __init__(self, noeuds=(), virtuels=100):
        self.virtuels, self.points, self.proprietaire = virtuels, [], {}
        for n in noeuds: self.ajouter(n)

    def ajouter(self, noeud):
        for k in range(self.virtuels):
            p = h("%s#%d" % (noeud, k)); self.proprietaire[p] = noeud
            bisect.insort(self.points, p)

    def retirer(self, noeud):
        for k in range(self.virtuels):
            p = h("%s#%d" % (noeud, k)); self.proprietaire.pop(p, None)
            i = bisect.bisect_left(self.points, p)
            if i < len(self.points) and self.points[i] == p: self.points.pop(i)

    def responsable(self, cle):
        i = bisect.bisect(self.points, h(cle)) % len(self.points)
        return self.proprietaire[self.points[i]]
