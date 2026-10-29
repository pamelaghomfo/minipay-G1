#!/usr/bin/env python3
"""UDP : pas de connexion, pas de garantie. On simule une perte de p % côté récepteur.
Usage : python3 udp_demo.py [N] [perte_en_pourcent]"""
import random, socket, sys, threading, time

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
PERTE = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
recus = set()

def recepteur(sock):
    sock.settimeout(0.5)
    while True:
        try:
            data, _ = sock.recvfrom(64)
        except socket.timeout:
            return
        if random.random() * 100 >= PERTE:       # perte simulée
            recus.add(int(data.decode()))

r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); r.bind(("127.0.0.1", 0))
port = r.getsockname()[1]
t = threading.Thread(target=recepteur, args=(r,)); t.start()
e = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
for i in range(N):
    e.sendto(str(i).encode(), ("127.0.0.1", port))
    if i % 50 == 0: time.sleep(0.001)
t.join()
print("envoyés : %d, reçus : %d, perdus : %d (%.1f %%)" % (N, len(recus), N - len(recus), 100 * (N - len(recus)) / N))
print("UDP ne réémet rien : si la perte compte, c'est à l'application d'ajouter numéros de séquence et accusés.")
