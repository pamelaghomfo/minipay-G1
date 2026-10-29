#!/usr/bin/env python3
"""Chapitre 3 : preuve d'exécution individuelle (courtier, idempotence, réessais, disjoncteur).

Usage (depuis le dossier lab3c, le dossier lab3b étant à côté) :
    python3 verifier_ch3.py --equipe E07 --membre "Nom Prenom"

Le script lance lui-même un courtier sur un port libre, teste votre consommateur.py et
votre resilience.py avec les paramètres de votre équipe, puis écrit preuve_ch3_<EQ>_<Membre>.json.
Durée : environ 30 secondes. Ne modifiez pas le fichier produit.
"""
import argparse, hashlib, json, os, platform, shutil, socket, subprocess, sys, tempfile, time
from datetime import datetime, timezone
import requests
from verifier import calcul_empreinte, parametres, parametres_chapitre, info_git
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resilience import Disjoncteur, DisjoncteurOuvert, reessayer


def port_libre():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def attendre(url, max_s=15):
    t = time.time()
    while time.time() - t < max_s:
        try:
            requests.get(url, timeout=1); return True
        except requests.RequestException:
            time.sleep(0.3)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--equipe", required=True)
    ap.add_argument("--membre", required=True)
    ap.add_argument("--lab3b", default="../lab3b")
    a = ap.parse_args()
    eq = a.equipe.strip().upper()
    pc = parametres_chapitre(eq, 3)
    res, mes = {}, {}
    lab3b = os.path.abspath(a.lab3b)

    # ---- Partie 1 : courtier et consommateur ----
    port = port_libre(); url = "http://127.0.0.1:%d" % port
    broker = subprocess.Popen([sys.executable, os.path.join(lab3b, "broker.py"), str(port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not attendre(url + "/stats/x"):
            sys.exit("Le courtier ne démarre pas (broker.py introuvable dans %s ?)" % lab3b)
        # 1. redistribution : message non acquitté, redélivré après le délai de visibilité
        requests.post(url + "/publier/test", json={"id": "t1"}, timeout=2)
        m1 = requests.get(url + "/consommer/test", params={"visibilite": 1}, timeout=2).json()
        time.sleep(1.3)
        m2 = requests.get(url + "/consommer/test", params={"visibilite": 1}, timeout=2).json()
        res["redistribution_ok"] = m1["msg_id"] == m2["msg_id"] and m2["essai"] == 2
        requests.post("%s/ack/test/%d" % (url, m2["msg_id"]), timeout=2)
        print("1. Redistribution d'un message non acquitté :", "OK" if res["redistribution_ok"] else "ECHEC")

        def lancer_consommateur(options):
            tmp = tempfile.mkdtemp()
            for _ in range(pc["messages"]):
                requests.post(url + "/publier/paiements",
                              json={"id": "ev-%s-%s" % (eq, os.urandom(3).hex()), "montant": 100}, timeout=2)
            t = time.perf_counter()
            subprocess.run([sys.executable, os.path.join(lab3b, "consommateur.py"), url] + options,
                           cwd=tmp, capture_output=True, text=True, timeout=60)
            duree = time.perf_counter() - t
            import sqlite3
            n = sqlite3.connect(os.path.join(tmp, "consommateur.db")).execute("SELECT COUNT(*) FROM sms").fetchone()[0]
            shutil.rmtree(tmp, ignore_errors=True)
            return n, round(duree, 2)

        n_id, d_id = lancer_consommateur(["--plante-avant-ack"])
        res["idempotence_consommateur_ok"] = n_id == pc["messages"]
        print("2. Consommateur idempotent (%d messages, crash avant ack) : %d SMS" % (pc["messages"], n_id),
              "OK" if res["idempotence_consommateur_ok"] else "ECHEC")
        n_sans, d_sans = lancer_consommateur(["--plante-avant-ack", "--sans-idempotence"])
        res["doublon_sans_idempotence_ok"] = n_sans == 2 * pc["messages"]
        print("3. Sans idempotence : %d SMS (attendu %d)" % (n_sans, 2 * pc["messages"]),
              "OK" if res["doublon_sans_idempotence_ok"] else "ECHEC")
        mes["duree_consommation_s"] = d_id
        t = time.perf_counter()
        for i in range(20):
            requests.post(url + "/publier/mesure", json={"id": i}, timeout=2)
        mes["latence_publication_ms_moy"] = round((time.perf_counter() - t) * 1000 / 20, 3)
    finally:
        broker.terminate()

    # ---- Partie 2 : réessais ----
    k = pc["echecs_avant_succes"]; compteur = {"n": 0}
    def instable():
        compteur["n"] += 1
        if compteur["n"] <= k: raise ConnectionError("panne simulée")
        return "ok"
    delais = []
    try:
        val = reessayer(instable, essais=k + 1, base=0.2, plafond=2.0, dormir=lambda s: None, delais=delais)
    except Exception:
        val = None
    bornes = all(0 <= d <= min(2.0, 0.2 * 2 ** i) + 1e-9 for i, d in enumerate(delais))
    res["reessais_ok"] = val == "ok" and compteur["n"] == k + 1 and len(delais) == k and bornes
    print("4. Réessais (%d échecs puis succès) :" % k, "OK" if res["reessais_ok"] else "ECHEC", "délais:", [round(d, 3) for d in delais])
    compteur["n"] = 0
    def toujours():
        compteur["n"] += 1; raise ConnectionError("panne")
    try:
        reessayer(toujours, essais=3, dormir=lambda s: None); abandon = False
    except ConnectionError:
        abandon = compteur["n"] == 3
    res["reessais_abandon_ok"] = abandon
    print("5. Abandon après 3 essais :", "OK" if abandon else "ECHEC")

    # ---- Partie 3 : disjoncteur ----
    seuil = pc["seuil_disjoncteur"]; t_fictif = {"t": 0.0}; appels = {"n": 0}; panne = {"on": True}
    dj = Disjoncteur(seuil=seuil, delai=5.0, horloge=lambda: t_fictif["t"])
    def cible():
        appels["n"] += 1
        if panne["on"]: raise ConnectionError("panne")
        return "ok"
    for _ in range(seuil):
        try: dj.appeler(cible)
        except ConnectionError: pass
    res["disjoncteur_ouvre_ok"] = dj.etat == "OUVERT"
    avant = appels["n"]
    try: dj.appeler(cible); rapide = False
    except DisjoncteurOuvert: rapide = appels["n"] == avant
    res["disjoncteur_rapide_ok"] = rapide
    t_fictif["t"] = 5.0; panne["on"] = False
    try: r2 = dj.appeler(cible)
    except Exception: r2 = None
    res["disjoncteur_reprise_ok"] = r2 == "ok" and dj.etat == "FERME"
    print("6. Disjoncteur (seuil %d) : ouverture %s, échec rapide %s, reprise %s" % (
        seuil, res["disjoncteur_ouvre_ok"], rapide, res["disjoncteur_reprise_ok"]))

    donnees = {
        "version": 1, "chapitre": 3, "equipe": eq, "membre": a.membre.strip(),
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parametres": parametres(eq), "parametres_chapitre": pc,
        "mesures": mes, "resultats": res, "git": info_git(),
        "environnement": {"python": platform.python_version(), "systeme": platform.system(),
                          "hote": hashlib.sha256(platform.node().encode()).hexdigest()[:10]},
    }
    donnees["empreinte"] = calcul_empreinte(donnees)
    nom = "preuve_ch3_%s_%s.json" % (eq, "".join(ch for ch in a.membre if ch.isalnum()))
    with open(nom, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    print("Fichier de preuve écrit :", nom, "| tests réussis : %d/%d" % (sum(res.values()), len(res)))


if __name__ == "__main__":
    main()
