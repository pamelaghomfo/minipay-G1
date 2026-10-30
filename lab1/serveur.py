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
    time.sleep(0.2)
    conn.sendall(("OK "+data).encode())
    conn.close()