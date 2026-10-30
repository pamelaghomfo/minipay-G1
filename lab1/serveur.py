import socket, time

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 5000))
s.listen()
print("Serveur en attente sur le port 5000")
compteur = 0
traites = set()                      # identifiants déjà traités
while True:
    conn, addr = s.accept()
    data = conn.recv(1024).decode()
    id_paiement, message = data.split("|", 1)
    if id_paiement in traites:
        print("doublon ignoré :", id_paiement)
    else:
        traites.add(id_paiement)
        compteur += 1
        print("paiements exécutés :", compteur)
    time.sleep(3)
    try:
        conn.sendall(("OK " + message).encode())
    except OSError:
        pass
    conn.close()