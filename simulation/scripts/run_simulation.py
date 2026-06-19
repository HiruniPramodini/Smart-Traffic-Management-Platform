"""
run_simulation.py
Runs the Malabe junction SUMO simulation via TraCI and extracts
traffic data every 60 seconds into a CSV file.

Output: data/processed/malabe_traffic_data.csv
"""

import os
import sys
import csv
import traci
from datetime import datetime, timedelta

SUMO_HOME = os.environ.get("SUMO_HOME", "C:/Program Files (x86)/Eclipse/Sumo")
sys.path.append(os.path.join(SUMO_HOME, "tools"))

CONFIG_FILE  = "simulation/malabe/malabe.sumocfg"
OUTPUT_CSV   = "data/processed/malabe_traffic_data.csv"
SAMPLE_EVERY = 60
SIM_DURATION = 86400

INCOMING_EDGES = {
    "kaduwela":     "kaduwela_in",
    "athurugiriya": "athurugiriya_in",
    "battaramulla": "battaramulla_in",
}

VEHICLE_TYPES = ["car", "bus", "motorcycle", "tuk_tuk", "truck"]

def seconds_to_time(sec):
    base = datetime(2024, 1, 1, 0, 0, 0)
    t = base + timedelta(seconds=int(sec))
    return t.strftime("%H:%M")

def get_time_period(sec):
    hour = (sec // 3600) % 24
    if 6 <= hour < 8:
        return "morning_peak"
    elif 13 <= hour < 14.5:
        return "afternoon_peak"
    elif 17 <= hour < 19:
        return "evening_peak"
    elif 22 <= hour or hour < 5:
        return "night"
    else:
        return "off_peak"

def count_vehicles_by_type(edge_id):
    counts = {vt: 0 for vt in VEHICLE_TYPES}
    vehicle_ids = traci.edge.getLastStepVehicleIDs(edge_id)
    for vid in vehicle_ids:
        vtype = traci.vehicle.getTypeID(vid)
        if vtype in counts:
            counts[vtype] += 1
    return counts

def main():
    os.makedirs("data/processed", exist_ok=True)
    traci.start(["sumo", "-c", CONFIG_FILE, "--no-warnings"])

    records = []
    step = 0

    print("Simulation started. Collecting data every 60 seconds...")
    print(f"Total duration: 24 hours ({SIM_DURATION} steps)\n")

    while step < SIM_DURATION:
        traci.simulationStep()

        if step % SAMPLE_EVERY == 0:
            time_str    = seconds_to_time(step)
            time_period = get_time_period(step)

            row = {
                "time_seconds": step,
                "time":         time_str,
                "time_period":  time_period,
                "junction":     "Malabe",
            }

            total_all = 0

            for road_name, edge_id in INCOMING_EDGES.items():
                counts = count_vehicles_by_type(edge_id)
                total  = sum(counts.values())
                total_all += total

                all_vehicles = traci.edge.getLastStepVehicleIDs(edge_id)
                queue = sum(1 for v in all_vehicles if traci.vehicle.getSpeed(v) < 0.5)

                avg_speed_ms  = traci.edge.getLastStepMeanSpeed(edge_id)
                avg_speed_kmh = round(avg_speed_ms * 3.6, 1)

                waiting_times = [traci.vehicle.getAccumulatedWaitingTime(v) for v in all_vehicles]
                avg_wait = round(sum(waiting_times) / len(waiting_times), 1) if waiting_times else 0

                row[f"{road_name}_cars"]        = counts["car"]
                row[f"{road_name}_buses"]       = counts["bus"]
                row[f"{road_name}_motorcycles"] = counts["motorcycle"]
                row[f"{road_name}_tuk_tuks"]    = counts["tuk_tuk"]
                row[f"{road_name}_trucks"]      = counts["truck"]
                row[f"{road_name}_total"]       = total
                row[f"{road_name}_queue"]       = queue
                row[f"{road_name}_speed_kmh"]   = avg_speed_kmh
                row[f"{road_name}_wait_sec"]    = avg_wait

            row["junction_total_vehicles"] = total_all
            records.append(row)

            if step % 3600 == 0:
                hour = step // 3600
                print(f"  Hour {hour:02d}:00 — junction total: {total_all} vehicles | period: {time_period}")

        step += 1

    traci.close()
    print(f"\nSimulation complete. {len(records)} records collected.")

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    print(f"Data saved to: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()