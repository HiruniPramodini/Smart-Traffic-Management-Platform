"""
generate_7day_csv.py
====================
Generates a 7-day realistic traffic dataset for the Kaduwela Green Wave corridor.

Junction layout:
                    Malabe (North)
                        |
  Ranala (West) ─── Kaduwela (Center) ─── Kotikawatta (East)
                        |
                   Biyagama (South)

Junctions and their arms:
  Kaduwela     (center) : malabe(N), biyagama(S), kotikawatta(E), ranala(W)
  Malabe       (north)  : kaduwela(S), athurugiriya(E), battaramulla(W)
  Biyagama     (south)  : kaduwela(N), industrial(E), kelaniya(W)
  Kotikawatta  (east)   : kaduwela(W), kolonnawa(E), mulleriyawa(S)
  Ranala       (west)   : kaduwela(E), hanwella(W), avissawella(S)

Output: data/processed/kaduwela_corridor_7day.csv
Rows  : 5 junctions × 7 days × 1440 minutes = 50,400 rows

Design:
  - NO time_period column — ML model discovers peaks from hour, day_of_week, counts
  - weather: clear, light_rain, heavy_rain, foggy, overcast (realistic July Sri Lanka)
  - hour: 0–23 raw numeric feature
  - Realistic commute shape: morning peak 06–09, lunch 12–13:30, evening peak 17–20
"""

import csv
import random
import os
from datetime import date, timedelta

random.seed(42)

# ---------------------------------------------------------------------------
# Junction definitions: arm name → peak vehicle/minute base rate
# ---------------------------------------------------------------------------
JUNCTIONS = {
    "Kaduwela": {
        "arms": ["malabe", "biyagama", "kotikawatta", "ranala"],
        "peak_base": {
            "malabe":      18,   # North — main corridor, heaviest
            "biyagama":    14,   # South
            "kotikawatta": 10,   # East — residential
            "ranala":      16,   # West — Hanwella/Avissawella corridor
        },
    },
    "Malabe": {
        "arms": ["kaduwela", "athurugiriya", "battaramulla"],
        "peak_base": {
            "kaduwela":     16,
            "athurugiriya": 10,
            "battaramulla": 13,
        },
    },
    "Biyagama": {
        "arms": ["kaduwela", "industrial", "kelaniya"],
        "peak_base": {
            "kaduwela":   13,
            "industrial":  9,   # industrial zone — heavy trucks too
            "kelaniya":   12,
        },
    },
    "Kotikawatta": {
        "arms": ["kaduwela", "kolonnawa", "mulleriyawa"],
        "peak_base": {
            "kaduwela":    11,
            "kolonnawa":    9,
            "mulleriyawa":  7,
        },
    },
    "Ranala": {
        "arms": ["kaduwela", "hanwella", "avissawella"],
        "peak_base": {
            "kaduwela":    14,
            "hanwella":    11,
            "avissawella":  8,
        },
    },
}

# Vehicle type mix
VEHICLE_MIX = {
    "car":        0.52,
    "bus":        0.08,
    "motorcycle": 0.25,
    "tuk_tuk":    0.12,
    "truck":      0.03,
}

# 24-hour traffic shape (peak = 1.0)
# Morning peak 06-09, lunch 12-13, evening peak 17-20
HOUR_SHAPE = [
    0.05, 0.03, 0.02, 0.02, 0.04, 0.08,   # 00-05
    0.22, 0.88, 1.00, 0.75, 0.56, 0.53,   # 06-11
    0.70, 0.68, 0.60, 0.58, 0.74, 0.97,   # 12-17
    1.00, 0.89, 0.65, 0.42, 0.22, 0.10,   # 18-23
]

# Day-of-week multiplier (0=Monday)
DOW_MULT = {
    0: 1.00,  # Monday
    1: 0.98,  # Tuesday
    2: 0.97,  # Wednesday
    3: 0.99,  # Thursday
    4: 1.05,  # Friday (highest)
    5: 0.70,  # Saturday
    6: 0.52,  # Sunday (lowest)
}
DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# Weekly weather schedule (realistic July Sri Lanka: intermittent monsoon)
# Format: (weather_type, start_hour_inclusive, end_hour_exclusive)
WEEKLY_WEATHER = {
    0: [("clear", 0, 12), ("light_rain", 14, 18), ("overcast", 18, 24)],
    1: [("overcast", 0, 7), ("clear", 7, 13), ("heavy_rain", 15, 17), ("overcast", 17, 24)],
    2: [("clear", 0, 24)],
    3: [("foggy", 5, 8), ("clear", 8, 14), ("light_rain", 14, 20), ("overcast", 20, 24)],
    4: [("clear", 0, 11), ("overcast", 11, 14), ("heavy_rain", 16, 19), ("clear", 19, 24)],
    5: [("light_rain", 6, 10), ("clear", 10, 17), ("overcast", 17, 24)],
    6: [("overcast", 0, 8), ("clear", 8, 24)],
}

WEATHER_IMPACT = {
    "clear":      {"speed": 1.00, "flow": 1.00, "wait": 1.00},
    "overcast":   {"speed": 0.95, "flow": 0.97, "wait": 1.05},
    "foggy":      {"speed": 0.78, "flow": 0.88, "wait": 1.30},
    "light_rain": {"speed": 0.85, "flow": 0.90, "wait": 1.25},
    "heavy_rain": {"speed": 0.65, "flow": 0.70, "wait": 1.80},
}

FREE_FLOW_KMH = 50.0
TL_CYCLE_S    = 128   # traffic light cycle in seconds


def get_weather(dow: int, hour: int) -> str:
    for (wtype, h0, h1) in WEEKLY_WEATHER.get(dow, []):
        if h0 <= hour < h1:
            return wtype
    return "clear"


def arm_metrics(base_peak: int, hour_mult: float, dow_mult: float,
                weather: str, noise: float) -> dict:
    wi = WEATHER_IMPACT[weather]
    raw = max(0.0, base_peak * hour_mult * dow_mult * wi["flow"] * noise)
    total = int(round(raw))

    counts, rem = {}, total
    for vt, frac in list(VEHICLE_MIX.items())[:-1]:
        n = int(round(total * frac))
        counts[vt] = n
        rem -= n
    counts["truck"] = max(0, rem)

    cong_pen  = min(0.60, raw / (base_peak * 1.5 + 1e-6)) * 0.40
    speed_kmh = max(5.0, round(
        FREE_FLOW_KMH * wi["speed"] * (1.0 - cong_pen) + random.uniform(-1.5, 1.5), 1
    ))
    queue_frac = min(0.95, cong_pen * 2.5 * wi["wait"])
    queue      = int(round(total * queue_frac))
    wait_sec   = max(0.0, round(
        TL_CYCLE_S * queue_frac * wi["wait"] * random.uniform(0.85, 1.15), 1
    ))

    return {
        "cars": counts.get("car", 0), "buses": counts.get("bus", 0),
        "motorcycles": counts.get("motorcycle", 0), "tuk_tuks": counts.get("tuk_tuk", 0),
        "trucks": counts.get("truck", 0), "total": total,
        "queue": queue, "speed_kmh": speed_kmh, "wait_sec": wait_sec,
    }


def hhmm(sec: int) -> str:
    return f"{(sec // 3600) % 24:02d}:{(sec % 3600) // 60:02d}"


def generate(output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Build unified sorted arm list for header
    all_arms = sorted({arm for jdata in JUNCTIONS.values() for arm in jdata["arms"]})
    arm_suffixes = ["cars", "buses", "motorcycles", "tuk_tuks", "trucks",
                    "total", "queue", "speed_kmh", "wait_sec"]
    arm_cols = [f"{arm}_{suf}" for arm in all_arms for suf in arm_suffixes]

    header = (["date", "day_of_week", "time_seconds", "time", "hour",
                "weather", "junction"] + arm_cols + ["junction_total_vehicles"])

    rows = []
    start = date(2025, 7, 7)   # Monday

    for day_off in range(7):
        d    = start + timedelta(days=day_off)
        dow  = day_off
        dm   = DOW_MULT[dow]
        dstr = d.isoformat()
        dname = DAY_NAMES[dow]

        for jname, jdata in JUNCTIONS.items():
            arms      = jdata["arms"]
            peak_base = jdata["peak_base"]

            for step in range(1440):
                sec  = step * 60
                hour = step // 60
                minute = step % 60
                weather  = get_weather(dow, hour)
                hour_mult = HOUR_SHAPE[hour]
                # smooth sub-hourly ramp
                next_mult = HOUR_SHAPE[(hour + 1) % 24]
                hour_mult = hour_mult + (next_mult - hour_mult) * (minute / 60.0)
                noise = random.uniform(0.88, 1.12)

                row = {
                    "date": dstr, "day_of_week": dname,
                    "time_seconds": sec, "time": hhmm(sec),
                    "hour": hour, "weather": weather, "junction": jname,
                }
                for col in arm_cols:
                    row[col] = 0

                total_j = 0
                for arm in arms:
                    m = arm_metrics(peak_base[arm], hour_mult, dm, weather, noise)
                    row[f"{arm}_cars"]        = m["cars"]
                    row[f"{arm}_buses"]       = m["buses"]
                    row[f"{arm}_motorcycles"] = m["motorcycles"]
                    row[f"{arm}_tuk_tuks"]    = m["tuk_tuks"]
                    row[f"{arm}_trucks"]      = m["trucks"]
                    row[f"{arm}_total"]       = m["total"]
                    row[f"{arm}_queue"]       = m["queue"]
                    row[f"{arm}_speed_kmh"]   = m["speed_kmh"]
                    row[f"{arm}_wait_sec"]    = m["wait_sec"]
                    total_j += m["total"]

                row["junction_total_vehicles"] = total_j
                rows.append(row)

    print(f"Generated {len(rows):,} rows  (expected 50,400)")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved → {output_path}")

    # Stats
    from collections import Counter
    wc = Counter(r["weather"] for r in rows)
    print("\nWeather distribution:")
    for w, n in sorted(wc.items()):
        print(f"  {w:12s}: {n:6,} rows ({n/len(rows)*100:.1f}%)")
    jc = Counter(r["junction"] for r in rows)
    print("\nJunction distribution:")
    for j, n in sorted(jc.items()):
        print(f"  {j:14s}: {n:6,} rows")
    dc = Counter(r["day_of_week"] for r in rows)
    print("\nDay distribution:")
    for day in DAY_NAMES:
        print(f"  {day:10s}: {dc[day]:6,} rows")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(script_dir, "kaduwela_corridor_7day.csv")
    generate(out)
