#!/usr/bin/env python3
"""Service compte : soldes persistants (SQLite) ; opérations idempotentes si une clé 'cle' est fournie.

  GET  /sante
  GET  /solde/<compte>
  POST /debiter  {"cle": "...", "compte": "c1", "montant": 100}   200 | 409 (fonds insuffisants)
  POST /crediter {"cle": "...", "compte": "c2", "montant": 100}
  POST /annuler  {"cle": "...", "compte": "c1", "montant": 100, "sens": "debit"|"credit"}
Une opération rejouée avec la même clé n'a aucun effet supplémentaire (réponse identique)."""
import os, sqlite3, threading
from flask import Flask, jsonify, request

DB = os.environ.get("DB", "compte.db")
app = Flask(__name__)
verrou = threading.Lock()
db = sqlite3.connect(DB, check_same_thread=False, isolation_level=None)
db.execute("PRAGMA journal_mode=WAL")
db.execute("CREATE TABLE IF NOT EXISTS comptes(nom TEXT PRIMARY KEY, solde INTEGER)")
db.execute("CREATE TABLE IF NOT EXISTS ops(cle TEXT PRIMARY KEY, genre TEXT, compte TEXT, montant INTEGER)")
for n in ("c1", "c2", "c3", "c4", "c5"):
    db.execute("INSERT OR IGNORE INTO comptes VALUES(?, 100000)", (n,))


@app.get("/sante")
def sante():
    return jsonify(ok=True, service="compte")


@app.get("/solde/<c>")
def solde(c):
    with verrou:
        r = db.execute("SELECT solde FROM comptes WHERE nom=?", (c,)).fetchone()
    return (jsonify(compte=c, solde=r[0]), 200) if r else (jsonify(erreur="compte inconnu"), 404)


def operation(genre, delta_signe):
    d = request.get_json(); cle, c, m = d.get("cle"), d["compte"], int(d["montant"])
    with verrou:
        if cle and db.execute("SELECT 1 FROM ops WHERE cle=?", (cle + "#" + genre,)).fetchone():
            return jsonify(ok=True, deja=True), 200
        r = db.execute("SELECT solde FROM comptes WHERE nom=?", (c,)).fetchone()
        if not r: return jsonify(erreur="compte inconnu"), 404
        if delta_signe < 0 and r[0] < m: return jsonify(erreur="fonds insuffisants"), 409
        db.execute("BEGIN")
        db.execute("UPDATE comptes SET solde=solde+? WHERE nom=?", (delta_signe * m, c))
        if cle: db.execute("INSERT OR IGNORE INTO ops VALUES(?,?,?,?)", (cle + "#" + genre, genre, c, m))
        db.execute("COMMIT")
    return jsonify(ok=True, deja=False), 200


@app.post("/debiter")
def debiter(): return operation("debit", -1)


@app.post("/crediter")
def crediter(): return operation("credit", +1)


@app.post("/annuler")
def annuler():
    d = request.get_json(); cle, c, m, sens = d["cle"], d["compte"], int(d["montant"]), d["sens"]
    origine = "debit" if sens == "debit" else "credit"
    with verrou:
        if not db.execute("SELECT 1 FROM ops WHERE cle=?", (cle + "#" + origine,)).fetchone():
            return jsonify(ok=True, rien_a_annuler=True), 200
        if db.execute("SELECT 1 FROM ops WHERE cle=?", (cle + "#annul_" + origine,)).fetchone():
            return jsonify(ok=True, deja=True), 200
        db.execute("BEGIN")
        db.execute("UPDATE comptes SET solde=solde+? WHERE nom=?", ((m if sens == "debit" else -m), c))
        db.execute("INSERT INTO ops VALUES(?,?,?,?)", (cle + "#annul_" + origine, "annul", c, m))
        db.execute("COMMIT")
    return jsonify(ok=True, deja=False), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), threaded=True)
