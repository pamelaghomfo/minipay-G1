#!/usr/bin/env python3
"""Consommateur de notifications. Il applique l'effet UNE SEULE FOIS par événement
grâce à une table des identifiants déjà traités (consommateur idempotent).

Usage : python3 consommateur.py [URL_courtier] [--plante-avant-ack] [--sans-idempotence]
  --plante-avant-ack : simule un crash après traitement, avant l'ack (provoque une redistribution)
  --sans-idempotence : désactive la déduplication (pour observer le doublon)
"""
import sqlite3, sys, time, requests

URL = next((a for a in sys.argv[1:] if a.startswith("http")), "http://127.0.0.1:7000")
PLANTE = "--plante-avant-ack" in sys.argv
DEDUP = "--sans-idempotence" not in sys.argv
db = sqlite3.connect("consommateur.db"); db.execute("CREATE TABLE IF NOT EXISTS vus(id TEXT PRIMARY KEY)")
db.execute("CREATE TABLE IF NOT EXISTS sms(id TEXT, texte TEXT)")

def traiter(ev):
    if DEDUP and db.execute("SELECT 1 FROM vus WHERE id=?", (ev["id"],)).fetchone():
        print("  doublon ignoré :", ev["id"]); return
    db.execute("INSERT OR IGNORE INTO vus VALUES(?)", (ev["id"],))
    db.execute("INSERT INTO sms VALUES(?,?)", (ev["id"], "Paiement de %s FCFA reçu" % ev["montant"]))
    db.commit(); print("  SMS envoyé pour", ev["id"])

vides = 0
while vides < 4:
    r = requests.get(URL + "/consommer/paiements", params={"visibilite": 2}, timeout=2)
    if r.status_code == 204:
        vides += 1; time.sleep(1); continue
    vides = 0; m = r.json(); print("reçu msg", m["msg_id"], "essai", m["essai"])
    traiter(m["corps"])
    if PLANTE and m["essai"] == 1:
        print("  *** crash simulé avant l'ack ***"); continue
    requests.post("%s/ack/paiements/%d" % (URL, m["msg_id"]), timeout=2)
n = db.execute("SELECT COUNT(*) FROM sms").fetchone()[0]
print("SMS enregistrés :", n)
