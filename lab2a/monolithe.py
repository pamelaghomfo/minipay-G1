"""Lab 2A : MiniPay en monolithe (un seul processus, une seule base).

Usage : python3 monolithe.py 5001
Chaque instance a sa propre base : monolithe_<port>.db
"""
import sqlite3, sys
from flask import Flask, jsonify, request

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
DB = "monolithe_%d.db" % PORT
app = Flask(__name__)


def sql(requete, args=(), ecriture=False):
    c = sqlite3.connect(DB)
    try:
        c.execute("CREATE TABLE IF NOT EXISTS comptes(id TEXT PRIMARY KEY, solde INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS paiements(id TEXT PRIMARY KEY, compte TEXT, montant INTEGER)")
        c.execute("INSERT OR IGNORE INTO comptes VALUES('awa', 1000000)")
        cur = c.execute(requete, args)
        res = cur.fetchall()
        n = cur.rowcount
        if ecriture:
            c.commit()
        return res, n
    finally:
        c.close()


@app.get("/sante")
def sante():
    return jsonify(ok=True, instance=PORT)


@app.get("/solde/<compte>")
def solde(compte):
    res, _ = sql("SELECT solde FROM comptes WHERE id=?", (compte,))
    if not res:
        return jsonify(erreur="compte inconnu"), 404
    return jsonify(compte=compte, solde=res[0][0], instance=PORT)


@app.post("/payer")
def payer():
    d = request.get_json()
    deja, _ = sql("SELECT id FROM paiements WHERE id=?", (d["id"],))
    if deja:
        return jsonify(ok=True, deja_traite=True, instance=PORT)
    _, n = sql("UPDATE comptes SET solde = solde - ? WHERE id=? AND solde >= ?",
               (d["montant"], d["compte"], d["montant"]), ecriture=True)
    if n == 0:
        return jsonify(erreur="solde insuffisant ou compte inconnu"), 409
    sql("INSERT INTO paiements VALUES(?,?,?)", (d["id"], d["compte"], d["montant"]), ecriture=True)
    return jsonify(ok=True, instance=PORT)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, threaded=True)
