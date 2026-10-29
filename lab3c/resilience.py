"""Briques de résilience : réessais avec recul exponentiel et gigue, disjoncteur.

reessayer(fonction, essais=4, base=0.2, plafond=2.0, dormir=time.sleep)
    Rappelle 'fonction' en cas d'exception. Délai avant l'essai k : aléa dans [0, min(plafond, base * 2**k)]
    (« full jitter »). Relève la dernière exception si tous les essais échouent.

class Disjoncteur(seuil, delai, horloge=time.monotonic)
    FERME  : les appels passent ; 'seuil' échecs consécutifs -> OUVERT.
    OUVERT : les appels échouent immédiatement (DisjoncteurOuvert) pendant 'delai' secondes.
    SEMI-OUVERT : après 'delai', UN appel d'essai passe ; succès -> FERME, échec -> OUVERT.
"""
import random, time


class DisjoncteurOuvert(Exception):
    pass


def reessayer(fonction, essais=4, base=0.2, plafond=2.0, dormir=time.sleep, delais=None):
    derniere = None
    for k in range(essais):
        try:
            return fonction()
        except DisjoncteurOuvert:
            raise                               # inutile d'insister : le disjoncteur protège
        except Exception as e:
            derniere = e
            if k < essais - 1:
                d = random.uniform(0, min(plafond, base * 2 ** k))
                if delais is not None: delais.append(d)
                dormir(d)
    raise derniere


class Disjoncteur:
    FERME, OUVERT, SEMI = "FERME", "OUVERT", "SEMI-OUVERT"

    def __init__(self, seuil=3, delai=5.0, horloge=time.monotonic):
        self.seuil, self.delai, self.horloge = seuil, delai, horloge
        self.etat, self.echecs, self.ouvert_a = self.FERME, 0, 0.0

    def appeler(self, fonction):
        if self.etat == self.OUVERT:
            if self.horloge() - self.ouvert_a >= self.delai:
                self.etat = self.SEMI                 # on laisse passer un appel d'essai
            else:
                raise DisjoncteurOuvert("circuit ouvert")
        try:
            res = fonction()
        except Exception:
            self.echecs += 1
            if self.etat == self.SEMI or self.echecs >= self.seuil:
                self.etat, self.ouvert_a = self.OUVERT, self.horloge()
            raise
        self.echecs, self.etat = 0, self.FERME
        return res
