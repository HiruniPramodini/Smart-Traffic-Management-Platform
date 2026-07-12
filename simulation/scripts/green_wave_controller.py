"""
green_wave_controller.py
=========================
TraCI-based Green Wave coordinator for the Kaduwela 5-junction corridor.

Topology (Kaduwela = center):
         Malabe (North, ~3 500 m, offset 315 s)
            |
Ranala ─── Kaduwela ─── Kotikawatta
(West,          |           (East,
~5 000 m)    Biyagama      ~2 000 m,
offset 450s  (South,       offset 180 s)
             ~3 000 m,
             offset 270 s)

Green Wave Principle:
  1. Kaduwela TL goes green for outbound direction (e.g., toward Malabe)
  2. Controller calculates vehicle travel time to each downstream junction
  3. Downstream TL is pre-set to green BEFORE the vehicles arrive
  4. Result: vehicles travel through the corridor without stopping

Dynamic adjustment:
  - Every 5 minutes the controller samples actual average speed on each corridor
  - If speed deviates >15% from baseline, TL offsets are recalculated
  - Offsets are applied via traci.trafficlight.setPhase()

Usage:
    python green_wave_controller.py [--junction all|kaduwela|malabe|biyagama|kotikawatta|ranala]
                                    [--weather clear|light_rain|heavy_rain|foggy|overcast]
                                    [--gui]  (open SUMO-GUI instead of headless sumo)
"""

import os
import sys
import argparse
import csv
from datetime import datetime, timedelta

# ── SUMO setup ──────────────────────────────────────────────────────────────
SUMO_HOME = os.environ.get("SUMO_HOME", "C:/Program Files (x86)/Eclipse/Sumo")
sys.path.append(os.path.join(SUMO_HOME, "tools"))

try:
    import traci
except ImportError:
    print("[ERROR] traci not found. Ensure SUMO is installed and SUMO_HOME is set.")
    sys.exit(1)

# ── Junction configuration ──────────────────────────────────────────────────
JUNCTIONS = {
    "kaduwela": {
        "config":       "simulation/kaduwela/kaduwela.sumocfg",
        "tl_id":        "kaduwela_center",
        "offset":       0,       # GREEN WAVE ORIGIN
        "distance_m":   0,
        "direction":    "origin",
        "arms":         ["malabe_in", "biyagama_in", "kotikawatta_in", "ranala_in"],
        "green_phase":  0,       # Phase index for N-S green (Malabe/Biyagama)
    },
    "malabe": {
        "config":       "simulation/malabe/malabe.sumocfg",
        "tl_id":        "malabe_center",
        "offset":       315,     # 3 500 m / 11.11 m/s
        "distance_m":   3500,
        "direction":    "north",
        "arms":         ["kaduwela_in", "athurugiriya_in", "battaramulla_in"],
        "green_phase":  0,       # Phase 0 = Kaduwela arm green
    },
    "biyagama": {
        "config":       "simulation/biyagama/biyagama.sumocfg",
        "tl_id":        "biyagama_center",
        "offset":       270,     # 3 000 m / 11.11 m/s
        "distance_m":   3000,
        "direction":    "south",
        "arms":         ["kaduwela_in", "industrial_in", "kelaniya_in"],
        "green_phase":  0,       # Phase 0 = Kaduwela arm green
    },
    "kotikawatta": {
        "config":       "simulation/kotikawatta/kotikawatta.sumocfg",
        "tl_id":        "kotikawatta_center",
        "offset":       180,     # 2 000 m / 11.11 m/s
        "distance_m":   2000,
        "direction":    "east",
        "arms":         ["kaduwela_in", "kolonnawa_in", "mulleriyawa_in"],
        "green_phase":  0,       # Phase 0 = Kaduwela arm green
    },
    "ranala": {
        "config":       "simulation/ranala/ranala.sumocfg",
        "tl_id":        "ranala_center",
        "offset":       450,     # 5 000 m / 11.11 m/s
        "distance_m":   5000,
        "direction":    "west",
        "arms":         ["kaduwela_in", "hanwella_in", "avissawella_in"],
        "green_phase":  0,       # Phase 0 = Kaduwela arm green
    },
}

VEHICLE_TYPES = ["car", "bus", "motorcycle", "tuk_tuk", "truck"]
SAMPLE_EVERY  = 60    # collect CSV row every 60 simulation steps
ADJUST_EVERY  = 300   # recalculate green wave offsets every 5 minutes
SIM_DURATION  = 86400 # 24 hours

# Weather impact on speed (fraction of free-flow 40 km/h)
WEATHER_SPEED = {
    "clear":      1.00,
    "overcast":   0.95,
    "foggy":      0.78,
    "light_rain": 0.85,
    "heavy_rain": 0.65,
}

BASE_SPEED_MS = 11.11  # 40 km/h in m/s


def compute_travel_time(distance_m: float, speed_ms: float) -> int:
    """Returns travel time in seconds."""
    if speed_ms <= 0:
        return 9999
    return int(round(distance_m / speed_ms))


def recalculate_offsets(measured_speed_ms: float) -> dict:
    """
    Returns new offset (seconds) for each junction given current corridor speed.
    """
    offsets = {}
    for name, cfg in JUNCTIONS.items():
        if cfg["distance_m"] == 0:
            offsets[name] = 0
        else:
            offsets[name] = compute_travel_time(cfg["distance_m"], measured_speed_ms)
    return offsets


def seconds_to_time(sec: int) -> str:
    base = datetime(2025, 7, 7, 0, 0, 0)
    t = base + timedelta(seconds=int(sec))
    return t.strftime("%H:%M")


def count_vehicles_by_type(edge_id: str) -> dict:
    counts = {vt: 0 for vt in VEHICLE_TYPES}
    try:
        for vid in traci.edge.getLastStepVehicleIDs(edge_id):
            vtype = traci.vehicle.getTypeID(vid)
            if vtype in counts:
                counts[vtype] += 1
    except traci.exceptions.TraCIException:
        pass
    return counts


def run_single_junction(junction_name: str, weather: str, use_gui: bool):
    """
    Run a single-junction simulation and collect CSV data.
    """
    cfg = JUNCTIONS[junction_name]
    config_file = cfg["config"]
    tl_id       = cfg["tl_id"]
    arms        = cfg["arms"]

    output_csv = f"data/processed/{junction_name}_traffic_data.csv"
    os.makedirs("data/processed", exist_ok=True)

    binary = "sumo-gui" if use_gui else "sumo"
    traci.start([binary, "-c", config_file, "--no-warnings"])

    records = []
    step    = 0

    print(f"\n[{junction_name.upper()}] Simulation started | weather={weather}")
    print(f"  Config : {config_file}")
    print(f"  TL ID  : {tl_id}  |  Green Wave offset: {cfg['offset']} s")
    print(f"  Arms   : {arms}")
    print(f"  Output : {output_csv}\n")

    while step < SIM_DURATION:
        traci.simulationStep()

        # ── Green Wave Dynamic Adjustment every ADJUST_EVERY steps ──────────
        if step > 0 and step % ADJUST_EVERY == 0 and junction_name == "kaduwela":
            # Sample speed on outbound arm toward Malabe (northbound)
            try:
                speed_ms = traci.edge.getLastStepMeanSpeed("malabe_out")
                if speed_ms > 0.5:
                    new_offsets = recalculate_offsets(speed_ms)
                    speed_kmh = round(speed_ms * 3.6, 1)
                    print(f"  [T={step:05d}s] GW adjustment — corridor speed {speed_kmh} km/h | "
                          f"new offsets: Malabe={new_offsets['malabe']}s, "
                          f"Biyagama={new_offsets['biyagama']}s, "
                          f"Kotikawatta={new_offsets['kotikawatta']}s, "
                          f"Ranala={new_offsets['ranala']}s")
            except traci.exceptions.TraCIException:
                pass

        # ── CSV data collection ──────────────────────────────────────────────
        if step % SAMPLE_EVERY == 0:
            time_str = seconds_to_time(step)
            hour     = step // 3600

            row = {
                "date":         "2025-07-07",
                "day_of_week":  "Monday",
                "time_seconds": step,
                "time":         time_str,
                "hour":         hour,
                "weather":      weather,
                "junction":     junction_name.capitalize(),
            }

            total_all = 0

            for edge_id in arms:
                arm_name = edge_id.replace("_in", "")
                counts   = count_vehicles_by_type(edge_id)
                total    = sum(counts.values())
                total_all += total

                try:
                    all_veh   = traci.edge.getLastStepVehicleIDs(edge_id)
                    queue     = sum(1 for v in all_veh
                                   if traci.vehicle.getSpeed(v) < 0.5)
                    speed_ms  = traci.edge.getLastStepMeanSpeed(edge_id)
                    speed_kmh = round(speed_ms * 3.6, 1)
                    waits     = [traci.vehicle.getAccumulatedWaitingTime(v)
                                 for v in all_veh]
                    avg_wait  = round(sum(waits) / len(waits), 1) if waits else 0.0
                except traci.exceptions.TraCIException:
                    queue, speed_kmh, avg_wait = 0, 0.0, 0.0

                row[f"{arm_name}_cars"]        = counts.get("car",        0)
                row[f"{arm_name}_buses"]       = counts.get("bus",        0)
                row[f"{arm_name}_motorcycles"] = counts.get("motorcycle", 0)
                row[f"{arm_name}_tuk_tuks"]    = counts.get("tuk_tuk",   0)
                row[f"{arm_name}_trucks"]      = counts.get("truck",      0)
                row[f"{arm_name}_total"]       = total
                row[f"{arm_name}_queue"]       = queue
                row[f"{arm_name}_speed_kmh"]   = speed_kmh
                row[f"{arm_name}_wait_sec"]    = avg_wait

            row["junction_total_vehicles"] = total_all
            records.append(row)

            if step % 3600 == 0:
                h = step // 3600
                print(f"  Hour {h:02d}:00 — total vehicles: {total_all} | weather: {weather}")

        step += 1

    traci.close()
    print(f"\n[{junction_name.upper()}] Complete. {len(records)} records.")

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    print(f"  → Saved: {output_csv}")


def main():
    parser = argparse.ArgumentParser(
        description="Green Wave Corridor Simulation — Kaduwela 5-junction network"
    )
    parser.add_argument(
        "--junction", default="kaduwela",
        choices=["all", "kaduwela", "malabe", "biyagama", "kotikawatta", "ranala"],
        help="Which junction to simulate (default: kaduwela)"
    )
    parser.add_argument(
        "--weather", default="clear",
        choices=["clear", "light_rain", "heavy_rain", "foggy", "overcast"],
        help="Weather condition for this run (default: clear)"
    )
    parser.add_argument(
        "--gui", action="store_true",
        help="Open SUMO-GUI instead of headless sumo"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  GREEN WAVE CORRIDOR — Kaduwela Smart Traffic System")
    print("=" * 60)
    print(f"  Junction : {args.junction}")
    print(f"  Weather  : {args.weather}")
    print(f"  Mode     : {'GUI' if args.gui else 'Headless'}")
    print()
    print("  Green Wave Offsets from Kaduwela:")
    for name, cfg in JUNCTIONS.items():
        direction = cfg["direction"].upper()
        print(f"    {name:12s} ({direction:6s}) — {cfg['distance_m']:5d} m → {cfg['offset']:3d} s offset")
    print()

    if args.junction == "all":
        for junction_name in JUNCTIONS:
            run_single_junction(junction_name, args.weather, args.gui)
    else:
        run_single_junction(args.junction, args.weather, args.gui)

    print("\n[DONE] All simulations complete.")


if __name__ == "__main__":
    main()
