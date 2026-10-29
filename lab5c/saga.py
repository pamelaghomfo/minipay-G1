"""Saga orchestrée pour un virement MiniPay : débit, crédit, journalisation.

Chaque étape est idempotente (clé = identifiant de saga) et possède une compensation idempotente.
L'orchestrateur écrit dans son journal avant et après chaque étape : après un crash,
reprendre(saga_id) relit le journal et termine (ou compense) sans rien appliquer deux fois.
"""


class ServiceIndisponible(Exception):
    pass


class FondsInsuffisants(Exception):
    pass


class Crash(Exception):
    """Simule la chute de l'orchestrateur."""


class Comptes:
    def __init__(self, soldes):
        self.soldes = dict(soldes)
        self.faits = set()                       # (saga, operation) déjà appliquées : idempotence
        self.panne = set()                       # opérations qui échouent : {"debit", "credit", ...}

    def _une_fois(self, saga, op, effet):
        if op in self.panne: raise ServiceIndisponible(op)
        if (saga, op) in self.faits: return      # rejeu : aucun effet
        effet(); self.faits.add((saga, op))

    def debiter(self, saga, compte, montant):
        def e():
            if self.soldes[compte] < montant: raise FondsInsuffisants(compte)
            self.soldes[compte] -= montant
        self._une_fois(saga, "debit", e)

    def crediter(self, saga, compte, montant):
        def e(): self.soldes[compte] += montant
        self._une_fois(saga, "credit", e)

    def annuler_debit(self, saga, compte, montant):
        if (saga, "debit") in self.faits and (saga, "annul_debit") not in self.faits:
            self.soldes[compte] += montant; self.faits.add((saga, "annul_debit"))

    def annuler_credit(self, saga, compte, montant):
        if (saga, "credit") in self.faits and (saga, "annul_credit") not in self.faits:
            self.soldes[compte] -= montant; self.faits.add((saga, "annul_credit"))


class Journal:
    def __init__(self):
        self.lignes = []                         # paiements enregistrés (une ligne par saga)
        self.panne = False

    def ecrire(self, saga, ligne):
        if self.panne: raise ServiceIndisponible("journal")
        if not any(l[0] == saga for l in self.lignes): self.lignes.append((saga, ligne))

    def effacer(self, saga):
        self.lignes = [l for l in self.lignes if l[0] != saga]


class Orchestrateur:
    ETAPES = ["debit", "credit", "journal"]

    def __init__(self, comptes, journal):
        self.comptes, self.journal = comptes, journal
        self.log = {}                            # saga -> {"args": ..., "evenements": [...], "statut": ...}

    # ----- actions et compensations -----
    def _action(self, etape, saga, a):
        if etape == "debit": self.comptes.debiter(saga, a["de"], a["montant"])
        elif etape == "credit": self.comptes.crediter(saga, a["vers"], a["montant"])
        elif etape == "journal": self.journal.ecrire(saga, a)

    def _compenser(self, etape, saga, a):
        if etape == "debit": self.comptes.annuler_debit(saga, a["de"], a["montant"])
        elif etape == "credit": self.comptes.annuler_credit(saga, a["vers"], a["montant"])
        elif etape == "journal": self.journal.effacer(saga)

    # ----- exécution -----
    def executer(self, saga, de, vers, montant, crash_apres=None):
        self.log[saga] = {"args": {"de": de, "vers": vers, "montant": montant}, "faites": [], "statut": "EN_COURS"}
        return self._avancer(saga, crash_apres)

    def reprendre(self, saga):
        """Après un crash : relit le journal de l'orchestrateur et continue."""
        return self._avancer(saga, None)

    def _avancer(self, saga, crash_apres):
        s = self.log[saga]; a = s["args"]
        if s["statut"] != "EN_COURS": return s["statut"]
        for etape in self.ETAPES:
            if etape in s["faites"]: continue
            try:
                self._action(etape, saga, a)
            except (ServiceIndisponible, FondsInsuffisants):
                return self._annuler(saga)
            s["faites"].append(etape)
            if crash_apres == etape: raise Crash(etape)
        s["statut"] = "TERMINEE"
        return s["statut"]

    def _annuler(self, saga):
        s = self.log[saga]
        for etape in reversed(self.ETAPES):
            self._compenser(etape, saga, s["args"])      # compensations idempotentes : sans effet si rien à annuler
        s["statut"] = "COMPENSEE"
        return s["statut"]
