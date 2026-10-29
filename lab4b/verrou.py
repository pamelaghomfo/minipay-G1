"""Verrou distribué avec bail (lease) et jeton de clôture (fencing token).

ServiceVerrou : un seul détenteur à la fois ; le verrou expire après 'bail' secondes.
  Chaque attribution renvoie un jeton strictement croissant.
Stockage : accepte une écriture seulement si son jeton est >= au plus grand déjà vu
  (clôture : un ancien détenteur « réveillé » trop tard est refusé).
"""
import time


class ServiceVerrou:
    def __init__(self, horloge=time.monotonic):
        self.horloge = horloge
        self.detenteur, self.expire_a, self.jeton = None, 0.0, 0

    def acquerir(self, client, bail):
        if self.detenteur is not None and self.horloge() < self.expire_a and self.detenteur != client:
            return None                                   # occupé
        if self.detenteur != client or self.horloge() >= self.expire_a:
            self.jeton += 1                               # nouvelle attribution : nouveau jeton
        self.detenteur, self.expire_a = client, self.horloge() + bail
        return self.jeton

    def liberer(self, client, jeton):
        if self.detenteur == client and jeton == self.jeton:
            self.detenteur = None
            return True
        return False


class Stockage:
    def __init__(self, avec_cloture=True):
        self.valeur, self.max_jeton, self.avec_cloture = None, 0, avec_cloture
        self.journal = []

    def ecrire(self, jeton, valeur):
        if self.avec_cloture and jeton < self.max_jeton:
            self.journal.append(("REFUSE", jeton, valeur)); return False
        self.max_jeton = max(self.max_jeton, jeton)
        self.valeur = valeur
        self.journal.append(("ECRIT", jeton, valeur)); return True
