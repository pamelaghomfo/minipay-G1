#!/usr/bin/env python3
"""Banc d'essai du chaos pour MiniPay : envoie des virements, provoque une panne, puis AUDITE les comptes.

Usage :
  python3 chaos_runner.py --equipe E07 --membre "Nom Prenom" [--sel SEL_DU_JOUR]
         [--url http://localhost:8080] [--cible compte|paiement|notification]
         [--arret-cmd "./ctl.sh stop {service}"] [--demarrage-cmd "./ctl.sh start {service}"]
Par défaut (Docker Compose) : docker compose stop/start {service}.

Contrat testé : voir gateway.py. Le script ne regarde jamais votre code : il observe seulement l'API
et vérifie des invariants (conservation de l'argent, effet unique, convergence, réponses rapides).
"""
import argparse, hashlib, json, os, platform, random, subprocess, sys, threading, time, uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import urllib.request, urllib.error
from verifier import calcul_empreinte, parametres, parametres_chapitre, info_git

COMPTES = ["c1", "c2", "c3", "c4", "c5"]


def http(methode, url, corps=None, timeout=4):
    data = json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(url, data=data, method=methode, headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}"), time.perf_counter() - t
    except urllib.error.HTTPError as e:
        try: corps = json.loads(e.read().decode() or "{}")
        except Exception: corps = {}
        return e.code, corps, time.perf_counter() - t
    except Exception:
        return 0, {}, time.perf_counter() - t           # 0 : pas de réponse (refus, délai dépassé)


def definitif(code, j):
    return code in (200, 409) and j.get("statut") in ("TERMINEE", "REFUSEE", "COMPENSEE")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--equipe", required=True); ap.add_argument("--membre", required=True)
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--sel", default="repetition", help="sel du jour fourni par l'enseignant le jour officiel")
    ap.add_argument("--cible", default=None)
    ap.add_argument("--arret-cmd", default="docker compose stop {service}")
    ap.add_argument("--demarrage-cmd", default="docker compose start {service}")
    ap.add_argument("--duree-charge", type=float, default=14.0)
    a = ap.parse_args()
    eq = a.equipe.strip().upper(); pc = parametres_chapitre(eq, 6)
    cible = a.cible or pc["cible_panne"]; base = a.url.rstrip("/")
    rng = random.Random(hashlib.sha256((eq + a.sel).encode()).hexdigest()); res, mes, details = {}, {}, []
    def ok(nom, cond, txt):
        res[nom] = bool(cond); print("%-3s %s" % ("OK" if cond else "KO", txt))
    def cmd(modele): subprocess.run(modele.format(service=cible), shell=True, capture_output=True, timeout=120)

    # 0. santé et soldes initiaux
    code, j, _ = http("GET", base + "/sante", timeout=5)
    if code != 200: sys.exit("La plateforme ne répond pas sur %s/sante (code %s). Démarrez-la d'abord." % (base, code))
    init = {}
    for c in COMPTES:
        code, j, _ = http("GET", base + "/solde/" + c); init[c] = j.get("solde")
    if None in init.values(): sys.exit("Soldes illisibles : /solde/<compte> doit répondre {'solde': n}")
    total0 = sum(init.values()); print("Soldes initiaux :", init)

    attendu = dict(init); sorts = {}      # id -> statut définitif connu
    corps_par_id = {}
    def nouveau(montant_max=3000, de=None, vers=None):
        d, v = rng.sample(COMPTES, 2)
        vid = "v-%s-%s" % (eq, uuid.UUID(int=rng.getrandbits(128)).hex[:12])
        c = {"id": vid, "de": de or d, "vers": vers or v, "montant": rng.randint(100, montant_max)}
        corps_par_id[vid] = c; return c

    def tenter(c, essais=1, pause=0.3, timeout=4):
        last = (0, {}, 0)
        for k in range(essais):
            last = http("POST", base + "/virement", c, timeout=timeout)
            if definitif(last[0], last[1]): return last
            time.sleep(pause)
        return last

    # 1. charge nominale
    with ThreadPoolExecutor(4) as ex:
        rs = list(ex.map(lambda c: (c, tenter(c)), [nouveau() for _ in range(30)]))
    nominal = [r for r in rs if definitif(r[1][0], r[1][1])]
    for c, (code, j, d) in nominal: sorts[c["id"]] = j["statut"]
    ok("nominal_ok", len(nominal) == 30 and all(j["statut"] in ("TERMINEE", "REFUSEE") for _, (_, j, _) in nominal),
       "1. Charge nominale : 30 virements, réponses définitives (%d/30)" % len(nominal))
    mes["latence_nominale_ms_moy"] = round(1000 * sum(r[1][2] for r in rs) / len(rs), 1)

    # 2. doublons concurrents : un même id, 6 requêtes simultanées
    c = nouveau(); c["montant"] = 777
    avant = [http("GET", base + "/solde/" + x)[1].get("solde") for x in (c["de"], c["vers"])]
    with ThreadPoolExecutor(6) as ex: rr = list(ex.map(lambda _: http("POST", base + "/virement", c, timeout=6), range(6)))
    st = {j.get("statut") for code, j, _ in rr if definitif(code, j)}
    apres = [http("GET", base + "/solde/" + x)[1].get("solde") for x in (c["de"], c["vers"])]
    effet_unique = (st == {"TERMINEE"} and apres == [avant[0] - 777, avant[1] + 777]) or (st and "TERMINEE" not in st and apres == avant)
    ok("doublons_ok", len(st) == 1 and all(definitif(code, j) for code, j, _ in rr) and effet_unique,
       "2. Six requêtes simultanées avec le même id : une issue cohérente %s et un seul effet (soldes avant %s, après %s)" % (sorted(st), avant, apres))
    if st: sorts[c["id"]] = list(st)[0]

    # 3. compte inconnu : aucun effet
    c = nouveau(); c["vers"] = "inconnu"
    code, j, _ = tenter(c, essais=3)
    ok("compte_inconnu_ok", code == 409 and j.get("statut") in ("COMPENSEE", "REFUSEE"),
       "3. Virement vers un compte inconnu : refus ou compensation (code %s, statut %s)" % (code, j.get("statut")))
    sorts[c["id"]] = j.get("statut")

    # 4. panne de la cible pendant une charge continue
    print("4. Panne de '%s' pendant %.0f s de charge..." % (cible, a.duree_charge))
    journal, stop = [], threading.Event(); t_debut = time.time(); fenetre = {"arret": None, "reprise": None}
    def charge():
        with ThreadPoolExecutor(3) as ex:
            while not stop.is_set():
                c = nouveau(); instant = time.time() - t_debut
                ex.submit(lambda c=c, instant=instant: journal.append((instant, c, http("POST", base + "/virement", c, timeout=6))))
                time.sleep(0.15)
    th = threading.Thread(target=charge); th.start()
    time.sleep(3); fenetre["arret"] = time.time() - t_debut; cmd(a.arret_cmd)
    time.sleep(6); cmd(a.demarrage_cmd); fenetre["reprise"] = time.time() - t_debut; t_redemarre = time.time()
    time.sleep(max(1, a.duree_charge - 9)); stop.set(); th.join(); time.sleep(7)    # laisse finir les requêtes en vol
    pendant = [(c, r) for (t, c, r) in journal if fenetre["arret"] <= t < fenetre["reprise"]]
    rapides = [r for _, r in pendant if r[2] < 3.0 and r[0] != 0]
    definitifs_pendant = [r for _, r in pendant if definitif(r[0], r[1])]
    mes["requetes_pendant_panne"] = len(pendant)
    mes["reponses_rapides_pct"] = round(100 * len(rapides) / max(1, len(pendant)), 1)
    mes["reponses_definitives_pendant_panne_pct"] = round(100 * len(definitifs_pendant) / max(1, len(pendant)), 1)
    ok("reponses_rapides_ok", len(pendant) > 5 and len(rapides) >= 0.95 * len(pendant),
       "4a. Pendant la panne, réponses (même en erreur) en moins de 3 s : %.0f %% des %d requêtes" % (mes["reponses_rapides_pct"], len(pendant)))
    if cible == "notification":
        ok("disponibilite_degradee_ok", len(definitifs_pendant) >= 0.95 * len(pendant),
           "4b. Panne de la notification : virements toujours aboutis (%.0f %%)" % mes["reponses_definitives_pendant_panne_pct"])
    else:
        res["disponibilite_degradee_ok"] = True; print("--  4b. (non applicable : panne d'un service critique)")

    # 5. retour à la normale
    t0 = time.time(); revenu = None
    while time.time() - t0 < 30:
        code, j, _ = http("GET", base + "/sante", timeout=3)
        if code == 200: revenu = round(time.time() - t0, 1); break
        time.sleep(0.5)
    mes["retour_sante_s"] = revenu
    ok("reprise_ok", revenu is not None, "5. Retour à la normale de /sante : %s s" % revenu)

    # 6. convergence : tous les identifiants doivent obtenir une réponse définitive (rejeu avec le même id)
    tous = {c["id"]: c for (t, c, r) in journal}
    for (t, c, r) in journal:
        if definitif(r[0], r[1]): sorts[c["id"]] = r[1]["statut"]
    en_attente = [i for i in tous if i not in sorts]
    t0 = time.time()
    while en_attente and time.time() - t0 < 40:
        for i in list(en_attente):
            code, j, _ = http("POST", base + "/virement", tous[i], timeout=6)
            if definitif(code, j): sorts[i] = j["statut"]; en_attente.remove(i)
        time.sleep(0.5)
    mes["ids_non_convergents"] = len(en_attente)
    ok("convergence_ok", not en_attente, "6. Convergence : %d virement(s) sans issue définitive après rejeu" % len(en_attente))

    # 7. audit : l'état des comptes doit être exactement celui du modèle
    for i, st in sorts.items():
        c = corps_par_id.get(i)
        if st == "TERMINEE" and c:
            attendu[c["de"]] = attendu.get(c["de"], 0) - c["montant"]; attendu[c["vers"]] = attendu.get(c["vers"], 0) + c["montant"]
    reel = {}
    for cpt in COMPTES:
        code, j, _ = http("GET", base + "/solde/" + cpt); reel[cpt] = j.get("solde")
    ecarts = {c: (reel[c] or 0) - attendu[c] for c in COMPTES if reel[c] != attendu[c]}
    for c, v in attendu.items():
        if c not in COMPTES and v: ecarts[c] = -v         # argent envoyé vers un compte qui n'existe pas
    ok("conservation_ok", sum(v for v in reel.values() if v is not None) == total0, "7a. Conservation : somme des soldes %s (initial %d)" % (sum(v or 0 for v in reel.values()), total0))
    ok("exactitude_ok", not ecarts, "7b. Exactitude : chaque compte correspond au modèle (écarts : %s)" % (ecarts or "aucun"))
    mes["virements_termines"] = sum(1 for s in sorts.values() if s == "TERMINEE")
    mes["ecart_total_abs"] = sum(abs(v) for v in ecarts.values())

    pts = {"nominal_ok": 1, "doublons_ok": 1, "compte_inconnu_ok": 0.5, "reponses_rapides_ok": 1, "disponibilite_degradee_ok": 0.5,
           "reprise_ok": 0.5, "convergence_ok": 1, "conservation_ok": 1.5, "exactitude_ok": 1.0}
    note = sum(p for k, p in pts.items() if res.get(k)); print("\nNote automatique du chaos : %.1f / 8 (cible : %s)" % (note, cible))
    donnees = {"version": 1, "chapitre": 6, "equipe": eq, "membre": a.membre.strip(), "sel": a.sel,
               "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "parametres": parametres(eq), "parametres_chapitre": pc, "cible": cible,
               "mesures": mes, "resultats": res, "note_chaos": note, "git": info_git(),
               "environnement": {"python": platform.python_version(), "systeme": platform.system(),
                                 "hote": hashlib.sha256(platform.node().encode()).hexdigest()[:10]}}
    donnees["empreinte"] = calcul_empreinte(donnees)
    nom = "preuve_chaos_%s_%s_%s.json" % (eq, "".join(ch for ch in a.membre if ch.isalnum()), a.sel)
    with open(nom, "w", encoding="utf-8") as f: json.dump(donnees, f, ensure_ascii=False, indent=2)
    print("Fichier écrit :", nom)


if __name__ == "__main__":
    main()
