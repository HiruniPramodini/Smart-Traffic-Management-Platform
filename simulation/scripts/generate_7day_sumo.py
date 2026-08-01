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
