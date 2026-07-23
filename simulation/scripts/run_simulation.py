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

# ── Weather speed multipliers ────────────────────────────────────────────────
WEATHER_SPEED_MULT = {
    "clear":      1.00,
    "overcast":   0.95,
    "foggy":      0.78,
    "light_rain": 0.85,
    "heavy_rain": 0.65,
}

VEHICLE_TYPES = ["car", "bus", "motorcycle", "tuk_tuk", "truck"]

SIM_DURATION  = 86400   # 24 hours in seconds
SAMPLE_EVERY  = 60      # sample every 60 steps (= 1 minute)
SIM_DATE      = datetime(2025, 7, 7)   # Monday — adjust as needed


def seconds_to_time(sec: int) -> str:
    return f"{(sec // 3600) % 24:02d}:{(sec % 3600) // 60:02d}"


def apply_weather_to_vehicle(vid: str, speed_mult: float):
    """Scale a vehicle's maximum speed by the weather multiplier."""
    try:
        base_max = traci.vehicletype.getMaxSpeed(traci.vehicle.getTypeID(vid))
        traci.vehicle.setMaxSpeed(vid, base_max * speed_mult)
    except traci.TraCIException:
        pass


def count_vehicles_by_type(edge_id: str) -> dict:
    counts = {vt: 0 for vt in VEHICLE_TYPES}
    for vid in traci.edge.getLastStepVehicleIDs(edge_id):
        vtype = traci.vehicle.getTypeID(vid)
        if vtype in counts:
            counts[vtype] += 1
    return counts


def build_header(arms: list) -> list:
    suffixes = ["cars", "buses", "motorcycles", "tuk_tuks", "trucks",
                "total", "queue", "speed_kmh", "wait_sec"]
    base = ["date", "day_of_week", "time_seconds", "time", "hour", "weather", "junction"]
    arm_cols = [f"{arm}_{suf}" for arm in sorted(arms) for suf in suffixes]
    return base + arm_cols + ["junction_total_vehicles"]


def main():
    parser = argparse.ArgumentParser(description="Run SUMO simulation for a corridor junction.")
    parser.add_argument("--junction", default="malabe",
                        choices=list(JUNCTION_CONFIG.keys()),
                        help="Which junction to simulate (default: malabe)")
    parser.add_argument("--weather", default="clear",
                        choices=list(WEATHER_SPEED_MULT.keys()),
                        help="Weather condition (affects vehicle speed, default: clear)")
    parser.add_argument("--gui", action="store_true",
                        help="Launch sumo-gui instead of headless sumo")
    args = parser.parse_args()

    jname   = args.junction
    weather = args.weather
    jconf   = JUNCTION_CONFIG[jname]
    speed_m = WEATHER_SPEED_MULT[weather]

    output_csv = os.path.join("data", "processed", f"{jname}_traffic_data.csv")
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)

    sumo_bin = "sumo-gui" if args.gui else "sumo"
    traci.start([sumo_bin, "-c", jconf["config"], "--no-warnings",
                 "--time-to-teleport", "-1"])

    arms   = jconf["edges"]        # {arm_name: edge_id}
    header = build_header(list(arms.keys()))
    records = []
    step    = 0

    day_name = SIM_DATE.strftime("%A")
    date_str = SIM_DATE.strftime("%Y-%m-%d")

    print(f"[{jname.upper()}] Simulation started | weather={weather} | speed_mult={speed_m}")
    print(f"  Config : {jconf['config']}")
    print(f"  Output : {output_csv}\n")

    while step < SIM_DURATION:
        traci.simulationStep()

        # Apply weather speed scaling to newly departed vehicles
        if speed_m != 1.0:
            for vid in traci.simulation.getDepartedIDList():
                apply_weather_to_vehicle(vid, speed_m)

        if step % SAMPLE_EVERY == 0:
            hour     = (step // 3600) % 24
            time_str = seconds_to_time(step)

            row = {
                "date":        date_str,
                "day_of_week": day_name,
                "time_seconds": step,
                "time":        time_str,
                "hour":        hour,
                "weather":     weather,
                "junction":    jname.capitalize(),
            }
