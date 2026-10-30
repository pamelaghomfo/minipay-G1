import socket, time

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", 5000))
s.listen()
print("Serveur en attente sur le port 5000")
compteur = 0
while True:
    conn, addr = s.accept()
    data = conn.recv(1024).decode()
    compteur += 1                  # le paiement est exécuté
    print("paiements exécutés :", compteur)
    time.sleep(3)                  # plus long que le timeout du client (2 s)
    conn.sendall(("OK " + data).encode())
    conn.close()