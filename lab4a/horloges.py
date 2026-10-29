"""Horloges logiques : Lamport et vectorielles, sur une trace d'événements.

Une trace est une liste d'événements :
    ("local", p)                 événement interne du processus p
    ("envoi", p, m)              p envoie le message m (étiquette quelconque)
    ("reception", q, m)          q reçoit le message m
Les processus sont numérotés 0..n-1.
"""


def lamport(trace, n):
    """Retourne la liste des estampilles de Lamport, une par événement."""
    h = [0] * n
    msgs, res = {}, []
    for ev in trace:
        p = ev[1]
        if ev[0] == "reception":
            h[p] = max(h[p], msgs[ev[2]]) + 1      # règle de réception
        else:
            h[p] += 1                              # règle locale / d'envoi
            if ev[0] == "envoi":
                msgs[ev[2]] = h[p]
        res.append(h[p])
    return res


def vecteurs(trace, n):
    """Retourne la liste des horloges vectorielles (tuples), une par événement."""
    v = [[0] * n for _ in range(n)]
    msgs, res = {}, []
    for ev in trace:
        p = ev[1]
        if ev[0] == "reception":
            v[p] = [max(a, b) for a, b in zip(v[p], msgs[ev[2]])]
        v[p][p] += 1
        if ev[0] == "envoi":
            msgs[ev[2]] = list(v[p])
        res.append(tuple(v[p]))
    return res


def comparer(a, b):
    """'avant' si a -> b, 'apres' si b -> a, 'egal', sinon 'concurrent'."""
    if a == b: return "egal"
    if all(x <= y for x, y in zip(a, b)): return "avant"
    if all(x >= y for x, y in zip(a, b)): return "apres"
    return "concurrent"
