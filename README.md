# Ressources_TP : Systèmes Distribués (M1 MSI, IFTIC-Sup)

Archive à télécharger sur la plateforme Moodle du cours, puis à décompresser.

## Contenu
| Dossier | TP |
|---|---|
| lab1 | Lab 1 : vous écrivez serveur.py et client.py ; verifier.py fourni |
| lab2a, lab2b | Chapitre 2 : répartiteur de charge ; MiniPay en microservices (Docker Compose) |
| lab3a, lab3b, lab3c | Chapitre 3 : sockets et sérialisation ; courtier et idempotence ; réessais et disjoncteur |
| lab4a, lab4b, lab4c | Chapitre 4 : horloges ; verrou à bail ; Raft simulé |
| lab5a, lab5b, lab5c | Chapitre 5 : quorums ; hachage cohérent ; saga et 2PC |
| projet_minipay | Projet final : point de départ à copier dans le dépôt d'équipe |

## Mise en route
1. Décompressez l'archive et copiez les dossiers dans le dépôt de votre équipe, sans changer l'arborescence (certaines commandes utilisent des chemins relatifs, par exemple ../lab2a/charge.py).
2. Lancez les commandes de chaque énoncé depuis le dossier du lab concerné.
3. Ne modifiez pas verifier.py ni chaos_runner.py. Les fichiers de preuve produits portent votre identifiant d'équipe et votre nom.
4. Fichier manquant ou abîmé : retéléchargez l'archive depuis Moodle.

## Installation locale de secours (sans Codespaces)
- Python 3.10 ou plus récent : `python3 --version`
- Dépendances : `pip install flask requests`
- Docker et Docker Compose pour le Lab 2B et le projet (sinon, le projet se lance sans Docker avec `./lancer_local.sh`, sous Linux, WSL2 ou macOS).
