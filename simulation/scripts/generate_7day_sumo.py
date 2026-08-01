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

# speedFactor multiplies each vehicle's desired speed; sigma = driver
# imperfection (0=perfect,1=very imperfect); minGap in metres.
WEATHER_VTYPE_IMPACT = {
    "clear":      {"speedFactor": 1.00, "sigma_add": 0.00, "minGap_mult": 1.00},
    "overcast":   {"speedFactor": 0.95, "sigma_add": 0.03, "minGap_mult": 1.05},
    "foggy":      {"speedFactor": 0.78, "sigma_add": 0.15, "minGap_mult": 1.40},
    "light_rain": {"speedFactor": 0.85, "sigma_add": 0.10, "minGap_mult": 1.25},
    "heavy_rain": {"speedFactor": 0.65, "sigma_add": 0.20, "minGap_mult": 1.60},
}

BASE_SIGMA = {"car": 0.5, "bus": 0.4, "motorcycle": 0.6, "tuk_tuk": 0.7, "truck": 0.3}
BASE_MINGAP = {"car": 2.5, "bus": 3.0, "motorcycle": 1.5, "tuk_tuk": 1.8, "truck": 3.5}
VTYPES = ["car", "bus", "motorcycle", "tuk_tuk", "truck"]

# Fallback arm map, matching generate_7day_csv.py's JUNCTIONS dict and the
# "<arm>_in" / "<arm>_out" edge naming convention confirmed in
# kaduwela.edg.xml. If your other junctions use different edge id
# conventions, adjust the arm lists below to match.
ARM_MAP = {
    "kaduwela":    ["malabe", "biyagama", "kotikawatta", "ranala"],
    "malabe":      ["kaduwela", "athurugiriya", "battaramulla"],
    "biyagama":    ["kaduwela", "industrial", "kelaniya"],
    "kotikawatta": ["kaduwela", "kolonnawa", "mulleriyawa"],
    "ranala":      ["kaduwela", "hanwella", "avissawella"],
}
ALL_ARMS = sorted({a for arms in ARM_MAP.values() for a in arms})
ARM_SUFFIXES = ["cars", "buses", "motorcycles", "tuk_tuks", "trucks",
                 "total", "queue", "speed_kmh", "wait_sec"]


def get_weather(dow, hour):
    for (wtype, h0, h1) in WEEKLY_WEATHER.get(dow, []):
        if h0 <= hour < h1:
            return wtype
    return "clear"


def hhmm(sec):
    return f"{(sec // 3600) % 24:02d}:{(sec % 3600) // 60:02d}"


def apply_weather(traci, weather):
    impact = WEATHER_VTYPE_IMPACT[weather]
    for vt in VTYPES:
        if vt not in traci.vehicletype.getIDList():
            continue
        traci.vehicletype.setSpeedFactor(vt, impact["speedFactor"])
        traci.vehicletype.setImperfection(vt, min(0.95, BASE_SIGMA[vt] + impact["sigma_add"]))
        traci.vehicletype.setMinGap(vt, BASE_MINGAP[vt] * impact["minGap_mult"])


def run_junction_day(traci, sumo_binary, sumocfg, junction, dow, dstr, seed, writer):
    tls_ids = None
    cmd = [sumo_binary, "-c", sumocfg, "--seed", str(seed), "--no-warnings", "true",
           "--no-step-log", "true", "--duration-log.disable", "true"]
    traci.start(cmd)

    try:
        tls_ids = traci.trafficlight.getIDList()
        if tls_ids:
            programs = traci.trafficlight.getAllProgramLogics(tls_ids[0])
            custom = [p for p in programs if p.programID != "0"]
            if custom:
                traci.trafficlight.setProgram(tls_ids[0], custom[0].programID)

        in_edges = {arm: f"{arm}_in" for arm in ARM_MAP[junction]}
        known_edges = set(traci.edge.getIDList())
        in_edges = {arm: eid for arm, eid in in_edges.items() if eid in known_edges}
        missing = set(ARM_MAP[junction]) - set(in_edges)
        if missing:
            print(f"  [warn] {junction}: no edge found for arms {missing} "
                  f"(expected '<arm>_in' — check edge ids)")

        last_hour = -1
        for step in range(86400):
            traci.simulationStep()

            hour = step // 3600
            if hour != last_hour:
                weather = get_weather(dow, hour)
                apply_weather(traci, weather)
                last_hour = hour
                n_veh = traci.vehicle.getIDCount()
                print(f"    hour {hour:>2}/24  weather={weather:<10}  vehicles_running={n_veh}", flush=True)

            if step % 60 != 0:
                continue

            weather = get_weather(dow, hour)
            row = {"date": dstr, "day_of_week": DAY_NAMES[dow], "time_seconds": step,
                   "time": hhmm(step), "hour": hour, "weather": weather, "junction": junction.capitalize()}
            for arm in ALL_ARMS:
                for suf in ARM_SUFFIXES:
                    row[f"{arm}_{suf}"] = 0

            total_j = 0
            for arm, eid in in_edges.items():
                veh_ids = traci.edge.getLastStepVehicleIDs(eid)
                counts = {vt: 0 for vt in VTYPES}
                for vid in veh_ids:
                    vt = traci.vehicle.getTypeID(vid)
                    if vt in counts:
                        counts[vt] += 1
                total = len(veh_ids)
                speed_ms = traci.edge.getLastStepMeanSpeed(eid)
                speed_kmh = round(speed_ms * 3.6, 1)
                queue = traci.edge.getLastStepHaltingNumber(eid)
                wait = round(traci.edge.getWaitingTime(eid), 1)

                row[f"{arm}_cars"] = counts["car"]
                row[f"{arm}_buses"] = counts["bus"]
                row[f"{arm}_motorcycles"] = counts["motorcycle"]
                row[f"{arm}_tuk_tuks"] = counts["tuk_tuk"]
                row[f"{arm}_trucks"] = counts["truck"]
                row[f"{arm}_total"] = total
                row[f"{arm}_queue"] = queue
                row[f"{arm}_speed_kmh"] = speed_kmh
                row[f"{arm}_wait_sec"] = wait
                total_j += total

            row["junction_total_vehicles"] = total_j
            writer.writerow(row)
    finally:
        traci.close()

