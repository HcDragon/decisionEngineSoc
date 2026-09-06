#!/usr/bin/env python3
"""
dos_simulation.py
-----------------
Convenience root launcher for the Integrated DoS Simulation & Decision Pipeline.
Delegates directly to scripts/dos_simulation.py.
"""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import scripts.dos_simulation as sim

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = " ".join(sys.argv[1:])
        if arg in sim.ATTACK_CONFIG:
            sim.run_simulation(arg)
        elif arg.upper() == "ALL":
            for v in sim.ATTACK_VARIANTS:
                sim.run_simulation(v)
                sim.time.sleep(1.5)
        else:
            print("  [!] Unknown attack: " + arg)
            print("      Valid: " + ", ".join(sim.ATTACK_VARIANTS) + ", ALL")
    else:
        choice = sim.select_attack()
        if choice == "ALL":
            for v in sim.ATTACK_VARIANTS:
                sim.run_simulation(v)
                sim.time.sleep(1.5)
        else:
            sim.run_simulation(choice)
