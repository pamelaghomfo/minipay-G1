#!/usr/bin/env python3
"""Dérive d'horloges physiques : à quelle fréquence resynchroniser ?
Usage : python3 derive.py [rho_ppm] [ecart_tolere_ms]
Deux horloges dérivent chacune d'au plus rho (en ppm) : l'écart peut croître de 2*rho par seconde."""
import sys
rho = float(sys.argv[1]) if len(sys.argv) > 1 else 50.0       # ppm, valeur typique d'un quartz courant
delta = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0     # ms d'écart toléré
croissance = 2 * rho * 1e-6                                   # s d'écart par seconde
intervalle = (delta / 1000) / croissance
print("dérive max %.0f ppm : l'écart croît de %.2f ms par seconde" % (rho, croissance * 1000))
print("pour rester sous %.0f ms, resynchroniser au moins toutes les %.0f s" % (delta, intervalle))
print("sans resynchronisation, écart après 24 h : %.1f s" % (croissance * 86400))
