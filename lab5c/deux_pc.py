"""Validation en deux phases (2PC) : le coordinateur qui tombe bloque les participants."""


class Participant:
    def __init__(self, nom, vote_oui=True):
        self.nom, self.vote_oui, self.etat, self.verrou = nom, vote_oui, "INIT", False

    def preparer(self):
        if self.vote_oui:
            self.etat, self.verrou = "PREPARE", True       # promesse : je peux valider, ressources verrouillées
            return True
        self.etat = "ANNULE"; return False

    def decider(self, commit):
        self.etat, self.verrou = ("VALIDE" if commit else "ANNULE"), False


def deux_pc(participants, crash_apres_votes=False):
    """Phase 1 : le coordinateur collecte les votes. Phase 2 : il diffuse la décision.
    Si crash_apres_votes, il tombe entre les deux phases et ne diffuse rien."""
    votes = [p.preparer() for p in participants]
    if crash_apres_votes:
        return "COORDINATEUR EN PANNE"
    decision = all(votes)
    for p in participants: p.decider(decision)
    return "VALIDE" if decision else "ANNULE"
