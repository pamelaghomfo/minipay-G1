#!/usr/bin/env python3
"""Lab 1 : preuve d'exécution individuelle.

Usage :
    python3 verifier.py --equipe E07 --membre "Nom Prenom"

Le script exécute le scénario du double débit avec les paramètres propres à
votre équipe, mesure votre environnement et écrit le fichier preuve_<membre>.json
à déposer avec la fiche de rendu. Chaque membre de l'équipe exécute le script
dans son propre environnement.
"""
import argparse, hashlib, json, os, platform, socket, subprocess, sys, threading, time, uuid
from datetime import datetime, timezone

SEL = "sysdist-2026-lab1"  # empreinte d'intégrité (détecte les modifications involontaires)


def parametres(equipe):
    """Paramètres déterministes dérivés de l'identifiant d'équipe."""
    graine = int(hashlib.sha256(equipe.strip().upper().encode()).hexdigest(), 16)
    timeout = 1 + graine % 3                       # 1, 2 ou 3 secondes
    return {
        "timeout_s": timeout,
        "delai_serveur_s": timeout + 1,            # plus long que le timeout : force le réessai
        "montant": 1000 * (1 + (graine // 7) % 9),  # 1000 à 9000 FCFA
    }


def parametres_chapitre(equipe, chapitre):
    """Paramètres propres à l'équipe pour les chapitres suivants (dérivés de l'identifiant)."""
    h = int(hashlib.sha256((equipe.strip().upper() + "|ch%d" % chapitre).encode()).hexdigest(), 16)
    if chapitre == 3:
        return {"echecs_avant_succes": 1 + h % 3,      # le service échoue k fois puis répond
                "seuil_disjoncteur": 2 + (h // 5) % 3,  # 2 à 4 échecs consécutifs
                "messages": 2 + (h // 11) % 4}          # 2 à 5 messages
    if chapitre == 4:
        return {"graine_raft": 1 + h % 999,             # graine du simulateur Raft
                "noeuds": 3 + 2 * ((h // 7) % 2),       # 3 ou 5 nœuds
                "graine_trace": (h // 13) % 10**6}      # trace d'événements pour les horloges
    if chapitre == 5:
        return {"repliques": 3 + 2 * (h % 2),            # 3 ou 5 répliques
                "graine": 1 + (h // 3) % 999,
                "montant": 500 * (1 + (h // 11) % 10),   # 500 à 5000
                "etape_en_echec": ["credit", "journal"][(h // 17) % 2],
                "noeuds_anneau": 4 + (h // 23) % 4}     # 4 à 7 nœuds
    return {}


def calcul_empreinte(donnees):
    copie = {k: v for k, v in donnees.items() if k != "empreinte"}
    texte = json.dumps(copie, sort_keys=True, ensure_ascii=False) + SEL
    return hashlib.sha256(texte.encode()).hexdigest()


class ServeurPaiement:
    """Serveur de test : compte les paiements exécutés."""

    def __init__(self, delai, idempotent):
        self.delai, self.idempotent = delai, idempotent
        self.executes, self.vus, self.verrou = 0, set(), threading.Lock()
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(16)
        self.port = self.sock.getsockname()[1]
        self.actif = True
        threading.Thread(target=self._boucle, daemon=True).start()

    def _boucle(self):
        self.sock.settimeout(0.2)
        while self.actif:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                continue
            threading.Thread(target=self._traiter, args=(conn,), daemon=True).start()

    def _traiter(self, conn):
        try:
            msg = conn.recv(1024).decode()
            ident = msg.split("id=")[-1] if "id=" in msg else None
            with self.verrou:
                if not (self.idempotent and ident in self.vus):
                    self.executes += 1
                if ident:
                    self.vus.add(ident)
            time.sleep(self.delai)
            conn.sendall(("OK " + msg).encode())
        except OSError:
            pass
        finally:
            conn.close()

    def arreter(self):
        self.actif = False
        self.sock.close()


def client_avec_reessai(port, montant, timeout, avec_id):
    ident = uuid.uuid4().hex[:8]
    message = "payer %d" % montant + (" id=" + ident if avec_id else "")
    for _ in range(2):
        try:
            c = socket.create_connection(("127.0.0.1", port), timeout=timeout)
            c.sendall(message.encode())
            c.recv(1024)
            return True
        except OSError:
            continue
    return False


def scenario(p, idempotent):
    srv = ServeurPaiement(p["delai_serveur_s"], idempotent)
    t0 = time.time()
    client_avec_reessai(srv.port, p["montant"], p["timeout_s"], avec_id=idempotent)
    duree = time.time() - t0
    time.sleep(0.3)
    executes = srv.executes
    srv.arreter()
    return executes, round(duree, 3)


def latence_connexion(n=20):
    srv = ServeurPaiement(0, False)
    mesures = []
    for _ in range(n):
        t0 = time.perf_counter()
        c = socket.create_connection(("127.0.0.1", srv.port), timeout=2)
        mesures.append((time.perf_counter() - t0) * 1000)
        c.close()
    srv.arreter()
    return round(sum(mesures) / n, 4), round(min(mesures), 4)


def info_git():
    def run(*args):
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True, timeout=5).stdout.strip()
        except Exception:
            return ""
    return {"commits": run("rev-list", "--count", "HEAD"), "auteur": run("config", "user.name")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--equipe", required=True, help="Identifiant d'équipe, par exemple E07")
    ap.add_argument("--membre", required=True, help="Nom et prénom")
    ap.add_argument("--dossier", default=".", help="Dossier contenant serveur.py et client.py")
    a = ap.parse_args()

    p = parametres(a.equipe)
    print("Équipe %s : timeout=%d s, délai serveur=%d s, montant=%d FCFA" % (
        a.equipe.upper(), p["timeout_s"], p["delai_serveur_s"], p["montant"]))
    print("Scénario A (sans idempotence), patientez...")
    exec_a, duree_a = scenario(p, False)
    print("  paiements exécutés :", exec_a)
    print("Scénario B (avec identifiant unique), patientez...")
    exec_b, duree_b = scenario(p, True)
    print("  paiements exécutés :", exec_b)
    lat_moy, lat_min = latence_connexion()

    def lire(nom):
        try:
            return open(os.path.join(a.dossier, nom), encoding="utf-8").read()
        except OSError:
            return None
    serveur, client = lire("serveur.py"), lire("client.py")

    donnees = {
        "version": 1,
        "chapitre": 1,
        "equipe": a.equipe.strip().upper(),
        "membre": a.membre.strip(),
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parametres": p,
        "mesures": {"latence_connexion_ms_moy": lat_moy, "latence_connexion_ms_min": lat_min,
                    "duree_scenario_a_s": duree_a, "duree_scenario_b_s": duree_b},
        "resultats": {"executions_sans_idempotence": exec_a, "executions_avec_idempotence": exec_b},
        "fichiers": {"serveur_py": serveur is not None, "client_py": client is not None,
                     "client_reessaie": bool(client and "timeout" in client and ("range" in client or "while" in client))},
        "environnement": {"python": platform.python_version(), "systeme": platform.system(),
                          "hote": hashlib.sha256(socket.gethostname().encode()).hexdigest()[:10]},
        "git": info_git(),
    }
    donnees["empreinte"] = calcul_empreinte(donnees)
    nom = "preuve_%s_%s.json" % (donnees["equipe"], "".join(ch for ch in a.membre if ch.isalnum()))
    with open(nom, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    print("Fichier de preuve écrit :", nom)
    print("Déposez-le avec votre fiche de rendu.")


if __name__ == "__main__":
    main()
