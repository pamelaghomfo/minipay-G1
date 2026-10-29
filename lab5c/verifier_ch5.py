#!/usr/bin/env python3
"""Chapitre 5 : preuve d'exécution individuelle (réplication, partitionnement, saga, 2PC).

Usage (depuis le dossier lab5c ; lab5a et lab5b doivent être à côté) :
    python3 verifier_ch5.py --equipe E07 --membre "Nom Prenom"

Écrit preuve_ch5_<EQ>_<Membre>.json. Durée : quelques secondes.
"""
import argparse, hashlib, json, os, platform, random, sys, time
from datetime import datetime, timezone
from verifier import calcul_empreinte, parametres, parametres_chapitre, info_git

ICI = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--equipe", required=True)
    ap.add_argument("--membre", required=True)
    ap.add_argument("--lab5a", default=os.path.join(ICI, "..", "lab5a"))
    ap.add_argument("--lab5b", default=os.path.join(ICI, "..", "lab5b"))
    a = ap.parse_args()
    eq = a.equipe.strip().upper(); pc = parametres_chapitre(eq, 5)
    sys.path[:0] = [os.path.abspath(a.lab5a), os.path.abspath(a.lab5b), ICI]
    from replication import Magasin, PrimaireSecondaires
    from anneau import Anneau, modulo
    from saga import Comptes, Journal, Orchestrateur, Crash
    from deux_pc import Participant, deux_pc
    res, mes, t0 = {}, {}, time.perf_counter()
    def ok(nom, cond, txt):
        res[nom] = bool(cond); print("%s :" % txt, "OK" if cond else "ECHEC")

    # 1-2. quorums
    n = pc["repliques"]; q = n // 2 + 1
    frais = True
    for g in range(200):
        m = Magasin(n, q, q, g); m.ecrire("k", 1)
        for i in range(n - q): m.tomber(i)               # n - q répliques manquent la 2e écriture
        m.ecrire("k", 2)
        for i in range(n - q): m.revenir(i)
        frais = frais and m.lire("k") == 2
    ok("quorum_frais_ok", frais, "1. Quorums w=r=%d sur %d répliques : lectures toujours fraîches" % (q, n))
    perimees = 0
    for g in range(200):
        m = Magasin(n, 1, 1, g); m.ecrire("k", 1)
        for i in range(1, n): m.tomber(i)
        m.ecrire("k", 2)
        for i in range(1, n): m.revenir(i)
        perimees += m.lire("k") != 2
    mes["lectures_perimees_w1r1_sur_200"] = perimees
    ok("lecture_perimee_ok", perimees > 0, "2. Avec w=1, r=1 des lectures périmées apparaissent (%d/200)" % perimees)

    # 3. réplication asynchrone
    p = PrimaireSecondaires(retard=100); p.ecrire(-500, "k", "ancien"); v = p.ecrire(0, "k", "nouveau")
    ok("retard_replication_ok",
       p.lire(10, "k", "secondaire") == "ancien" and p.lire(10, "k", "primaire") == "nouveau"
       and p.lire(10, "k", "secondaire", jeton=v) == "nouveau" and p.lire(200, "k", "secondaire") == "nouveau",
       "3. Retard de réplication, lecture de ses propres écritures")

    # 4. anneau
    k = pc["noeuds_anneau"]; cles = ["c%d" % i for i in range(5000)]
    avant = ["n%d" % i for i in range(k)]
    mod = sum(modulo(avant, c) != modulo(avant + ["nx"], c) for c in cles) / len(cles)
    an = Anneau(avant, 100); ancien = {c: an.responsable(c) for c in cles}; an.ajouter("nx")
    bouge = sum(ancien[c] != an.responsable(c) for c in cles) / len(cles)
    charge = {}
    for c in cles: charge[an.responsable(c)] = charge.get(an.responsable(c), 0) + 1
    an.retirer("nx"); revenu = all(an.responsable(c) == ancien[c] for c in cles)
    mes["cles_deplacees_modulo_pct"], mes["cles_deplacees_anneau_pct"] = round(100 * mod, 1), round(100 * bouge, 1)
    ok("anneau_ok", mod > 0.5 and bouge < 1.6 / (k + 1) and max(charge.values()) / min(charge.values()) < 2.5 and revenu,
       "4. Anneau cohérent (%d nœuds) : %.1f %% déplacées contre %.1f %% en modulo" % (k, 100 * bouge, 100 * mod))

    # 5-8. saga
    M = pc["montant"]
    def monde(): c, j = Comptes({"awa": 10000, "paul": 5000}), Journal(); return c, j, Orchestrateur(c, j)
    c, j, o = monde()
    ok("saga_succes_ok", o.executer("s", "awa", "paul", M) == "TERMINEE" and c.soldes == {"awa": 10000 - M, "paul": 5000 + M} and len(j.lignes) == 1,
       "5. Saga : succès")
    c, j, o = monde()
    if pc["etape_en_echec"] == "credit": c.panne.add("credit")
    else: j.panne = True
    st = o.executer("s", "awa", "paul", M)
    ok("saga_compensation_ok", st == "COMPENSEE" and c.soldes == {"awa": 10000, "paul": 5000} and not j.lignes,
       "6. Saga : échec à l'étape '%s', compensation complète" % pc["etape_en_echec"])
    bon = True
    for etape in ("debit", "credit"):
        c, j, o = monde()
        try: o.executer("s", "awa", "paul", M, crash_apres=etape); bon = False
        except Crash: pass
        r1 = o.reprendre("s"); r2 = o.reprendre("s")
        bon = bon and r1 == r2 == "TERMINEE" and c.soldes == {"awa": 10000 - M, "paul": 5000 + M} and len(j.lignes) == 1
    ok("saga_reprise_ok", bon, "7. Reprise après crash de l'orchestrateur, sans effet en double")
    c, j, o = monde(); c.panne.add("credit"); o.executer("s", "awa", "paul", M)
    for _ in range(3): o._annuler("s")
    ok("compensation_idempotente_ok", c.soldes == {"awa": 10000, "paul": 5000}, "8. Compensation rejouée plusieurs fois")

    # 9. 2PC
    ps = [Participant("a"), Participant("b")]; r = deux_pc(ps, crash_apres_votes=True)
    ok("deux_pc_bloque_ok", r != "VALIDE" and all(x.etat == "PREPARE" and x.verrou for x in ps),
       "9. 2PC : participants bloqués si le coordinateur tombe")

    # 10. chaos individuel
    gm = int(hashlib.sha256(a.membre.strip().lower().encode()).hexdigest(), 16) % 10**6
    rng = random.Random(gm); c, j = Comptes({"awa": 50000, "paul": 50000, "kim": 50000}), Journal(); o = Orchestrateur(c, j)
    total0 = sum(c.soldes.values()); bon = True; term = comp = 0
    for i in range(60):
        de, vers = rng.sample(["awa", "paul", "kim"], 2); mt = rng.randint(100, 4000); sid = "s%d" % i
        c.panne = set(rng.sample(["debit", "credit"], 1)) if rng.random() < 0.25 else set()
        j.panne = rng.random() < 0.1
        crash = rng.choice([None, None, "debit", "credit"])
        try: st = o.executer(sid, de, vers, mt, crash_apres=crash)
        except Crash:
            c.panne = set(); j.panne = False; st = o.reprendre(sid)
        c.panne = set(); j.panne = False
        bon = bon and st in ("TERMINEE", "COMPENSEE") and sum(c.soldes.values()) == total0
        term += st == "TERMINEE"; comp += st == "COMPENSEE"
        bon = bon and (st == "TERMINEE") == any(l[0] == sid for l in j.lignes)
    mes["chaos_terminees"], mes["chaos_compensees"] = term, comp
    ok("saga_chaos_ok", bon, "10. Épreuve de chaos : 60 sagas, argent conservé, aucun état intermédiaire (%d terminées, %d compensées)" % (term, comp))
    mes["duree_s"] = round(time.perf_counter() - t0, 2)

    donnees = {
        "version": 1, "chapitre": 5, "equipe": eq, "membre": a.membre.strip(),
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "parametres": parametres(eq), "parametres_chapitre": pc,
        "mesures": mes, "resultats": res, "git": info_git(),
        "environnement": {"python": platform.python_version(), "systeme": platform.system(),
                          "hote": hashlib.sha256(platform.node().encode()).hexdigest()[:10]},
    }
    donnees["empreinte"] = calcul_empreinte(donnees)
    nom = "preuve_ch5_%s_%s.json" % (eq, "".join(ch for ch in a.membre if ch.isalnum()))
    with open(nom, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=2)
    print("Fichier de preuve écrit :", nom, "| tests réussis : %d/%d" % (sum(res.values()), len(res)))


if __name__ == "__main__":
    main()
