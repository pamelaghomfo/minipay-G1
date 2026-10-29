#!/usr/bin/env python3
"""Chapitre 4 : preuve d'exécution individuelle (horloges, verrou à bail, Raft).

Usage (depuis le dossier lab4c ; lab4a et lab4b doivent être à côté) :
    python3 verifier_ch4.py --equipe E07 --membre "Nom Prenom"

Le script teste vos fichiers horloges.py, verrou.py et raft_sim.py avec les paramètres de
votre équipe, puis écrit preuve_ch4_<EQ>_<Membre>.json. Durée : environ 20 secondes.
"""
import argparse, hashlib, json, os, platform, random, sys, time
from datetime import datetime, timezone
from verifier import calcul_empreinte, parametres, parametres_chapitre, info_git

ICI = os.path.dirname(os.path.abspath(__file__))


def trace_aleatoire(graine, n=3, longueur=14):
    r, trace, en_vol, k = random.Random(graine), [], [], 0
    for _ in range(longueur):
        a = r.random()
        if a < 0.3 or (a < 0.7 and not en_vol):
            trace.append(("local", r.randrange(n)))
        elif a < 0.7 or not en_vol:
            k += 1; p = r.randrange(n); trace.append(("envoi", p, "m%d" % k)); en_vol.append((p, "m%d" % k))
        else:
            p, m = en_vol.pop(r.randrange(len(en_vol)))
            q = r.choice([x for x in range(n) if x != p]); trace.append(("reception", q, m))
    return trace


def reference_avant(trace):
    """Relation 'happens-before' calculée indépendamment (fermeture transitive)."""
    n = len(trace); avant = [[False] * n for _ in range(n)]
    dernier, envoi = {}, {}
    for i, ev in enumerate(trace):
        p = ev[1]
        if p in dernier: avant[dernier[p]][i] = True
        if ev[0] == "envoi": envoi[ev[2]] = i
        if ev[0] == "reception": avant[envoi[ev[2]]][i] = True
        dernier[p] = i
    for k in range(n):
        for i in range(n):
            if avant[i][k]:
                for j in range(n):
                    if avant[k][j]: avant[i][j] = True
    return avant


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--equipe", required=True)
    ap.add_argument("--membre", required=True)
    ap.add_argument("--lab4a", default=os.path.join(ICI, "..", "lab4a"))
    ap.add_argument("--lab4b", default=os.path.join(ICI, "..", "lab4b"))
    a = ap.parse_args()
    eq = a.equipe.strip().upper(); pc = parametres_chapitre(eq, 4)
    sys.path[:0] = [os.path.abspath(a.lab4a), os.path.abspath(a.lab4b), ICI]
    from horloges import lamport, vecteurs, comparer
    from verrou import ServiceVerrou, Stockage
    from raft_sim import Cluster
    res, mes, t0 = {}, {}, time.perf_counter()

    # 1-2. horloges
    trace = trace_aleatoire(pc["graine_trace"])
    L, V = lamport(trace, 3), vecteurs(trace, 3)
    avant = reference_avant(trace)
    recu = {ev[2]: i for i, ev in enumerate(trace) if ev[0] == "reception"}
    envoye = {ev[2]: i for i, ev in enumerate(trace) if ev[0] == "envoi"}
    res["lamport_ok"] = (len(L) == len(trace)
        and all(L[envoye[m]] < L[recu[m]] for m in recu)
        and all(L[i] < L[j] for i in range(len(trace)) for j in range(len(trace)) if avant[i][j]))
    ok = len(V) == len(trace)
    for i in range(len(trace)):
        for j in range(len(trace)):
            if i == j or not ok: continue
            attendu = "avant" if avant[i][j] else ("apres" if avant[j][i] else "concurrent")
            if comparer(V[i], V[j]) != attendu: ok = False
    res["vecteurs_ok"] = ok
    print("1. Horloges de Lamport :", "OK" if res["lamport_ok"] else "ECHEC")
    print("2. Horloges vectorielles (causalité et concurrence) :", "OK" if res["vecteurs_ok"] else "ECHEC")

    # 3-4. verrou à bail et jeton de clôture
    t = {"now": 0.0}; v = ServiceVerrou(horloge=lambda: t["now"])
    ja = v.acquerir("A", 10); occupe = v.acquerir("B", 10) is None
    t["now"] = 11; jb = v.acquerir("B", 10)
    res["verrou_bail_ok"] = ja == 1 and occupe and jb is not None and jb > ja
    s = Stockage(True); s.ecrire(jb, "B"); refuse = s.ecrire(ja, "A") is False and s.valeur == "B"
    s2 = Stockage(False); s2.ecrire(jb, "B"); s2.ecrire(ja, "A")
    res["cloture_ok"] = refuse and s2.valeur == "A"
    print("3. Verrou à bail (exclusion, expiration, jeton croissant) :", "OK" if res["verrou_bail_ok"] else "ECHEC")
    print("4. Jeton de clôture (écriture périmée refusée) :", "OK" if res["cloture_ok"] else "ECHEC")

    # 5-8. Raft avec les paramètres de l'équipe
    n, g = pc["noeuds"], pc["graine_raft"]
    c = Cluster(n, g); c.run(2000)
    l1 = c.leader()
    res["raft_election_ok"] = l1 is not None and not c.invariants()
    mes["election_1er_leader_ms"] = next((int(x.split()[0]) for x in c.lignes if "LEADER" in x), -1)
    print("5. Élection d'un leader unique (%d nœuds, graine %d) :" % (n, g), "OK" if res["raft_election_ok"] else "ECHEC")

    for k in range(3): c.submit("a%d" % k); c.run(100)
    terme1 = c.noeuds[l1].terme; c.crash(l1); t_crash = c.t; c.run(2500)
    l2 = c.leader()
    ok = l2 is not None and l2 != l1 and c.noeuds[l2].terme > terme1
    mes["reelection_ms"] = next((int(x.split()[0]) - t_crash for x in c.lignes if "LEADER" in x and int(x.split()[0]) > t_crash), -1)
    for k in range(3): c.submit("b%d" % k); c.run(100)
    c.restart(l1); c.run(2500)
    ok = ok and c.noeuds[l1].journal == c.noeuds[c.leader()].journal and not c.invariants()
    ok = ok and [x for x in c.commandes_validees()] == ["a0", "a1", "a2", "b0", "b1", "b2"]
    res["raft_panne_leader_ok"] = ok
    print("6. Panne du leader : réélection et rattrapage du journal :", "OK" if ok else "ECHEC")

    c = Cluster(n, g + 1); c.run(2000); ancien = c.leader()
    c.submit("valide"); c.run(300)
    autres = [i for i in range(n) if i != ancien]
    c.partition([[ancien], autres]); c.submit("orpheline", vers=ancien); c.run(2500)
    nouveau = c.leader()
    ok = nouveau is not None and nouveau != ancien
    c.submit("majorite"); c.run(300); c.heal(); c.run(2500)
    ok = ok and all("orpheline" not in [e[1] for e in nd.journal] for nd in c.noeuds)
    ok = ok and "majorite" in c.commandes_validees() and not c.invariants()
    res["raft_partition_ok"] = ok
    print("7. Partition : la minorité ne valide rien, l'entrée orpheline disparaît :", "OK" if ok else "ECHEC")

    c = Cluster(n, g + 2); c.run(2000); l = c.leader(); c.submit("x"); c.run(300)
    commit_avant = max(nd.commit for nd in c.noeuds)
    c.crash(l)
    for i in [i for i in range(n) if i != l][: n // 2]: c.crash(i)
    c.run(4000)
    res["raft_sans_quorum_ok"] = c.leader() is None and max(nd.commit for nd in c.noeuds) == commit_avant
    print("8. Sans quorum, pas de leader et pas de validation :", "OK" if res["raft_sans_quorum_ok"] else "ECHEC")

    # 9. chaos individuel (graine propre au membre : les mesures diffèrent d'un membre à l'autre)
    gm = int(hashlib.sha256(a.membre.strip().lower().encode()).hexdigest(), 16) % 10**6
    elections, valides, ok = 0, 0, True
    for k in range(6):
        r = random.Random(gm + k); nn = r.choice([3, 5]); c = Cluster(nn, gm + k)
        for step in range(15):
            c.run(r.randint(100, 500)); x = r.random()
            if x < 0.2 and c.leader() is not None: c.crash(c.leader())
            elif x < 0.35:
                for nd in c.noeuds:
                    if not nd.vivant: c.restart(nd.i); break
            elif x < 0.5:
                m = r.sample(range(nn), r.randint(1, nn // 2)); c.partition([m, [i for i in range(nn) if i not in m]])
            elif x < 0.6: c.heal()
            c.submit("c%d" % step)
        c.heal()
        for nd in c.noeuds:
            if not nd.vivant: c.restart(nd.i)
        c.run(3000)
        ok = ok and not c.invariants()
        elections += sum(1 for x in c.lignes if "devient LEADER" in x); valides += len(c.commandes_validees())
    res["raft_chaos_ok"] = ok
    mes["chaos_elections"], mes["chaos_commandes_validees"] = elections, valides
    print("9. Épreuve de chaos (6 scénarios aléatoires, %d élections) : sûreté" % elections, "OK" if ok else "ECHEC")
    mes["duree_s"] = round(time.perf_counter() - t0, 2)

    donnees = {
        "version": 1, "chapitre": 4, "equipe": eq, "membre": a.membre.strip(),
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parametres": parametres(eq), "parametres_chapitre": pc,
        "mesures": mes, "resultats": res, "git": info_git(),
        "environnement": {"python": platform.python_version(), "systeme": platform.system(),
                          "hote": hashlib.sha256(platform.node().encode()).hexdigest()[:10]},
    }
    donnees["empreinte"] = calcul_empreinte(donnees)
    nom = "preuve_ch4_%s_%s.json" % (eq, "".join(ch for ch in a.membre if ch.isalnum()))
    with open(nom, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    print("Fichier de preuve écrit :", nom, "| tests réussis : %d/%d" % (sum(res.values()), len(res)))


if __name__ == "__main__":
    main()
