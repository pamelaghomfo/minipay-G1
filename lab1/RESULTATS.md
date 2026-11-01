# Tous les résultats du Lab1
1. Fonctionnement normal : le client reçoit « OK payer 5000 » en 761 ms.
2. Arrêt du serveur (kill %1) : la première panne (serveur arrêté) : erreur « Connection refused » en 6 ms. Le client sait que la demande n'est pas partie, l'échec est sûr. Puis le remplacement de l'adresse 127.0.0.1 par l'adresse 10.255.255.1 nous avons la deuxième panne (adresse injoignable) : erreur « timed out » après 2007 ms. Le client ne sait pas si la demande est arrivée : c'est une panne partielle.
4. Reproduction du double débit : le serveur met 3 s à répondre alors que le client abandonne après 2 s et réessaie. Résultat : 2 paiements exécutés pour un seul ordre, soit 16 000 FCFA débités, sans aucune confirmation reçue.
