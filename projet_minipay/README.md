# MiniPay : dépôt de départ du projet

Plateforme de paiement mobile résiliente. Quatre services : `gateway` (8080), `compte` (5001),
`paiement` (5002), `notification` (5003). Le contrat d'API public est décrit en tête de `gateway.py`.

## Démarrer
Avec Docker (Codespaces) : `docker compose up --build -d` puis `curl localhost:8080/sante`
Sans Docker : `./lancer_local.sh` (processus locaux, journaux dans `run/`)

## Votre mission
Le service `paiement.py` est volontairement naïf. Rendez-le résilient (idempotence, saga, réessais,
disjoncteur, notification facultative), puis éprouvez-le avec le banc d'essai du chaos :

    # avec Docker
    python3 chaos_runner.py --equipe E07 --membre "Nom Prenom"
    # sans Docker
    python3 chaos_runner.py --equipe E07 --membre "Nom Prenom" \
        --arret-cmd "./ctl.sh stop {service}" --demarrage-cmd "./ctl.sh start {service}"

Le script provoque une panne (le service dépend de votre équipe), envoie des virements, puis audite
les soldes. Il écrit `preuve_chaos_<équipe>_<membre>_<sel>.json`. Le jour officiel, l'enseignant fournit
un autre sel (`--sel`) : les montants, l'ordre et les comptes changent, pas le principe.

## Règles
- Ne pas modifier `chaos_runner.py` ni `verifier.py` (les empreintes détectent les modifications).
- Vous pouvez ajouter des services, des fichiers, des tests, du monitoring ; les quatre noms de service
  et le contrat de `gateway.py` doivent rester.
- Un journal `JOURNAL.md` de l'équipe (décisions de conception, expériences de chaos, échecs) est exigé.
