"""Service compte : soldes. Sa propre base (database per service)."""
import os, sqlite3
from flask import Flask, jsonify, request

DB = os.environ.get("DB", "compte.db")
app = Flask(__name__)


def sql(requete, args=(), ecriture=False):
    c = sqlite3.connect(DB)
    try:
        c.execute("CREATE TABLE IF NOT EXISTS comptes(id TEXT PRIMARY KEY, solde INTEGER)")
        c.execute("INSERT OR IGNORE INTO comptes VALUES('awa', 1000000)")
        cur = c.execute(requete, args)
        res, n = cur.fetchall(), cur.rowcount
        if ecriture:
            c.commit()
        return res, n
    finally:
        c.close()


@app.get("/sante")
def sante():
    return jsonify(ok=True)


@app.get("/solde/<compte>")
def solde(compte):
    res, _ = sql("SELECT solde FROM comptes WHERE id=?", (compte,))
    if not res:
        return jsonify(erreur="compte inconnu"), 404
    return jsonify(compte=compte, solde=res[0][0])


@app.post("/debiter")
def debiter():
    d = request.get_json()
    _, n = sql("UPDATE comptes SET solde = solde - ? WHERE id=? AND solde >= ?",
               (d["montant"], d["compte"], d["montant"]), ecriture=True)
    if n == 0:
        return jsonify(erreur="solde insuffisant ou compte inconnu"), 409
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), threaded=True)
