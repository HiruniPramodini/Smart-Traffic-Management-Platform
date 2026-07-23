"""
run_simulation.py
==================
Runs a SUMO simulation for any of the 5 Kaduwela Green Wave corridor junctions
via TraCI and extracts traffic data every 60 seconds into a CSV file.

Usage:
    python run_simulation.py [--junction <name>] [--weather <type>] [--gui]

    --junction : kaduwela | malabe | biyagama | kotikawatta | ranala  (default: malabe)
    --weather  : clear | light_rain | heavy_rain | foggy | overcast   (default: clear)
    --gui      : open sumo-gui instead of headless sumo

Output: data/processed/<junction>_traffic_data.csv

Design notes:
  - NO time_period column — ML model discovers peaks from raw hour + counts
  - Weather scales vehicle max speed via traci.vehicle.setMaxSpeed()
  - hour and date are derived from simulation step (assumes sim starts at 00:00)
"""

import os
import sys
import csv
import argparse
from datetime import datetime, timedelta

# ── SUMO setup ──────────────────────────────────────────────────────────────
SUMO_HOME = os.environ.get("SUMO_HOME", "C:/Program Files (x86)/Eclipse/Sumo")
sys.path.append(os.path.join(SUMO_HOME, "tools"))

try:
    import traci
except ImportError:
    print("[ERROR] traci not found. Ensure SUMO is installed and SUMO_HOME is set.")
    sys.exit(1)

# ── Junction definitions ─────────────────────────────────────────────────────
JUNCTION_CONFIG = {
    "kaduwela": {
        "config":  "simulation/kaduwela/kaduwela.sumocfg",
        "edges": {
            "malabe":      "malabe_in",
            "biyagama":    "biyagama_in",
            "kotikawatta": "kotikawatta_in",
            "ranala":      "ranala_in",
        },
    },
    "malabe": {
        "config":  "simulation/malabe/malabe.sumocfg",
        "edges": {
            "kaduwela":     "kaduwela_in",
            "athurugiriya": "athurugiriya_in",
            "battaramulla": "battaramulla_in",
        },
    },
    "biyagama": {
        "config":  "simulation/biyagama/biyagama.sumocfg",
        "edges": {
            "kaduwela":   "kaduwela_in",
            "industrial": "industrial_in",
            "kelaniya":   "kelaniya_in",
        },
    },
    "kotikawatta": {
        "config":  "simulation/kotikawatta/kotikawatta.sumocfg",
        "edges": {
            "kaduwela":   "kaduwela_in",
            "kolonnawa":  "kolonnawa_in",
            "mulleriyawa":"mulleriyawa_in",
        },
    },
    "ranala": {
        "config":  "simulation/ranala/ranala.sumocfg",
        "edges": {
            "kaduwela":    "kaduwela_in",
            "hanwella":    "hanwella_in",
            "avissawella": "avissawella_in",
        },
    },
}