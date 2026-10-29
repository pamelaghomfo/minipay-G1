#!/usr/bin/env python3
"""Lab 2B : preuve d'exécution individuelle (microservices MiniPay).

Prérequis : MiniPay tourne (docker compose up --build -d) et la passerelle répond
sur http://localhost:8080. Lancez ce script depuis le dossier contenant
docker-compose.yml :

    python3 verifier_ch2.py --equipe E07 --membre "Nom Prenom"

Le script teste le fonctionnement, l'idempotence, le mode dégradé (arrêt du
service notification), l'isolation (arrêt du service paiement) et la reprise.
Il arrête puis redémarre des services : ne le lancez pas pendant un autre test.
"""
import argparse, hashlib, json, platform, subprocess, time, urllib.error, urllib.request, uuid
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verifier import parametres, calcul_empreinte  # même fonctions que le Lab 1


def http(methode, url, corps=None, timeout=5):
    data = json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(url, data=data, method=methode, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}
    except Exception:
        return 0, {}


def attendre_sante(base, service, max_s=60):
    t0 = time.time()
    while time.time() - t0 < max_s:
        code, etat = http("GET", base + "/sante", timeout=2)
        if code == 200 and etat.get(service) == "up":
            return round(time.time() - t0, 2)
        time.sleep(0.5)
    return None


def solde(base):
    code, d = http("GET", base + "/solde/awa")
    return d.get("solde") if code == 200 else None


def payer(base, montant, ident=None):
    return http("POST", base + "/payer", {"compte": "awa", "montant": montant, "id": ident or uuid.uuid4().hex})


def commande(modele, service, dossier):
    cmd = modele.format(service=service)
    subprocess.run(cmd, shell=True, cwd=dossier, capture_output=True, text=True, timeout=120)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--equipe", required=True)
    ap.add_argument("--membre", required=True)
    ap.add_argument("--gateway", default="http://localhost:8080")
    ap.add_argument("--dossier", default=".")
    ap.add_argument("--arret-cmd", default="docker compose stop {service}")
    ap.add_argument("--demarrage-cmd", default="docker compose start {service}")
    a = ap.parse_args()
    base = a.gateway.rstrip("/")
    p = parametres(a.equipe)
    m = p["montant"]
    res = {}

    code, etat = http("GET", base + "/sante")
    res["sante_initiale"] = code == 200 and all(v == "up" for v in etat.values()) and len(etat) == 3
    print("1. Santé initiale :", "OK" if res["sante_initiale"] else "ECHEC", etat)

    s0 = solde(base)
    ident = uuid.uuid4().hex
    code, _ = payer(base, m, ident)
    s1 = solde(base)
    res["paiement_ok"] = code == 200 and s0 is not None and s1 == s0 - m
    print("2. Paiement de %d FCFA :" % m, "OK" if res["paiement_ok"] else "ECHEC")

    code, _ = payer(base, m, ident)  # même identifiant : doublon
    res["idempotence_ok"] = code == 200 and solde(base) == s1
    print("3. Idempotence (même identifiant rejoué) :", "OK" if res["idempotence_ok"] else "ECHEC")

    commande(a.arret_cmd, "notification", a.dossier)
    time.sleep(1)
    s2 = solde(base)
    code, _ = payer(base, m)
    res["degrade_notification_ok"] = code == 200 and solde(base) == s2 - m
    print("4. Notification arrêtée, paiement toujours possible :", "OK" if res["degrade_notification_ok"] else "ECHEC")
    commande(a.demarrage_cmd, "notification", a.dossier)
    attendre_sante(base, "notification")

    commande(a.arret_cmd, "paiement", a.dossier)
    time.sleep(1)
    code_pay, _ = payer(base, m)
    code_sol, _ = http("GET", base + "/solde/awa")
    res["isolation_paiement_ok"] = code_pay == 503 and code_sol == 200
    print("5. Paiement arrêté : /payer =", code_pay, ", /solde =", code_sol, "->", "OK" if res["isolation_paiement_ok"] else "ECHEC")

    t0 = time.time()
    commande(a.demarrage_cmd, "paiement", a.dossier)
    attente = attendre_sante(base, "paiement")
    redemarrage = round(time.time() - t0, 2) if attente is not None else None
    s3 = solde(base)
    code, _ = payer(base, m)
    res["reprise_ok"] = attente is not None and code == 200 and solde(base) == s3 - m
    print("6. Reprise après redémarrage :", "OK" if res["reprise_ok"] else "ECHEC", "(%s s)" % redemarrage)

    lat = []
    for _ in range(10):
        t = time.perf_counter()
        payer(base, 1)
        lat.append((time.perf_counter() - t) * 1000)

    donnees = {
        "version": 1, "chapitre": 2,
        "equipe": a.equipe.strip().upper(), "membre": a.membre.strip(),
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parametres": p,
        "mesures": {"latence_paiement_ms_moy": round(sum(lat) / len(lat), 3),
                    "redemarrage_paiement_s": redemarrage},
        "resultats": res,
        "environnement": {"python": platform.python_version(), "systeme": platform.system(),
                          "hote": hashlib.sha256(platform.node().encode()).hexdigest()[:10]},
    }
    donnees["empreinte"] = calcul_empreinte(donnees)
    nom = "preuve_ch2_%s_%s.json" % (donnees["equipe"], "".join(ch for ch in a.membre if ch.isalnum()))
    with open(nom, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    print("Fichier de preuve écrit :", nom)


if __name__ == "__main__":
    main()
