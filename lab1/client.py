import socket, time

t0 = time.time()
#id_paiement = str(uuid.uuid4())      # un seul identifiant pour tous les essais
for essai in range(2):
    try:
        c = socket.create_connection(("127.0.0.1", 5000), timeout=2)
        c.sendall(b"|payer 5000")
        print(c.recv(1024).decode()); break
    except OSError as e:
        print("Essai", essai + 1, "échoué :", e)
print("Durée : %.0f ms" % ((time.time() - t0) * 1000))