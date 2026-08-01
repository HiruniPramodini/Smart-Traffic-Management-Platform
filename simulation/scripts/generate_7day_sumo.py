"""
generate_7day_sumo.py
======================
Replaces generate_7day_csv.py with REAL SUMO/TraCI runs.

For each of the 5 junction .sumocfg files, this steps through a full
86,400s (24h) simulation once per simulated "day", 7 days total, and
on each simulated minute:
  - determines the weather for that hour (same weekly schedule as the
    synthetic generator, so the two datasets are comparable)
  - applies weather-adjusted vType parameters (speed factor, following
    imperfection, min gap) to all 5 vehicle types via TraCI
  - reads live edge detectors for every "<arm>_in" edge and writes one
    CSV row per junction per minute, in the SAME column schema as
    kaduwela_corridor_7day.csv so it's a drop-in replacement.

PREREQUISITE: run build_networks.sh first so every junction has a
compiled .net.xml. This script will refuse to run a junction that's
missing one.

Requires: SUMO installed, SUMO_HOME set, `pip install traci sumolib`
(or use the sumo-provided tools/ path).

Usage:
    python generate_7day_sumo.py --sumo-home /path/to/sumo \
        --sim-dir ../  --out ../../data/processed/kaduwela_corridor_7day_sumo.csv
"""

import argparse
import csv
import os
import sys
import random
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Same weather / day tables as generate_7day_csv.py, kept identical so the
# real-simulation dataset lines up with the synthetic one for comparison.
# ---------------------------------------------------------------------------
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

WEEKLY_WEATHER = {
    0: [("clear", 0, 12), ("light_rain", 14, 18), ("overcast", 18, 24)],
    1: [("overcast", 0, 7), ("clear", 7, 13), ("heavy_rain", 15, 17), ("overcast", 17, 24)],
    2: [("clear", 0, 24)],
    3: [("foggy", 5, 8), ("clear", 8, 14), ("light_rain", 14, 20), ("overcast", 20, 24)],
    4: [("clear", 0, 11), ("overcast", 11, 14), ("heavy_rain", 16, 19), ("clear", 19, 24)],
    5: [("light_rain", 6, 10), ("clear", 10, 17), ("overcast", 17, 24)],
    6: [("overcast", 0, 8), ("clear", 8, 24)],
}

