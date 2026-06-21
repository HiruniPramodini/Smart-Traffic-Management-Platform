## Smart-Traffic-Management-Platform ##

# Collecting Data 

 ** YouTube footages **
pip install yt-dlp
yt-dlp "https://youtu.be/ANhIuoJcSm4" -o "srilanka_traffic.mp4"


 ** Run YOLO on it **
from ultralytics import YOLO
import cv2
import csv

model = YOLO("yolov8n.pt")  # downloads automatically first time

cap = cv2.VideoCapture("srilanka_traffic.mp4")
fps = cap.get(cv2.CAP_PROP_FPS)
frame_interval = int(fps * 2)  # one reading every 2 seconds

records = []
frame_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    if frame_count % frame_interval == 0:
        results = model(frame, classes=[2, 3, 5, 7])
        # 2=car, 3=motorcycle, 5=bus, 7=truck

        counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
        for box in results[0].boxes:
            label = model.names[int(box.cls)]
            if label in counts:
                counts[label] += 1

        records.append({
            "frame": frame_count,
            "time_sec": round(frame_count / fps, 1),
            **counts,
            "total": sum(counts.values())
        })

    frame_count += 1

cap.release()

with open("srilanka_traffic_data.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)

print(f"Done — {len(records)} records saved")

# Agents — Junction AI System (Phase 3)

## Overview

The Agents module implements **intelligent traffic signal control** using AI agents. Each agent independently monitors a junction and makes decisions about traffic light timing based on real-time vehicle data and ML-powered congestion predictions.

---

## Architecture

### Single Junction Agent

```
Vehicle Data (count, wait time, queue)
        ↓
ML Congestion Predictor (Phase 2 model)
        ↓
Decision Logic (Option B: proportional + time-aware)
        ↓
Green Time Signal (60-90 seconds)
```

### Multi-Junction System (Future)

```
Kaduwela Agent ──┐
Koswatta Agent ──┼─→ Coordinator Agent → Optimized timings
Battaramulla Agent─┘
```

---

## Junction Agent Class

### What It Does

Each `JunctionAgent`:
1. **Observes** — reads current traffic state
   - Vehicle count
   - Waiting time
   - Queue length
   - Time of day

2. **Thinks** — uses ML model to predict congestion
   - Loads trained XGBoost model
   - Predicts: LOW / MEDIUM / HIGH

3. **Decides** — converts prediction to green time
   - Proportional logic (more vehicles = more green)
   - Time-of-day adjustment (peak hours get priority)

4. **Acts** — outputs signal timing decision

---

## Decision Logic (Phase 3A)

### Vehicle Count Thresholds

| Vehicle Count | Base Green Time |
|---|---|
| > 90 | 90 seconds |
| > 70 | 75 seconds |
| > 50 | 70 seconds |
| > 30 | 55 seconds |
| ≤ 30 | 45 seconds |

### Time-of-Day Adjustment

**Peak Hours** (6-8 AM, 1-2:30 PM, 5-7 PM):
- Add 15 seconds to all timings
- Higher priority for busy routes

**Off-Peak Hours** (all other times):
- Use base timings as-is
- Lower demand, standard timing

**Night** (10 PM - 5 AM):
- Reduce by 10 seconds
- Minimal traffic, shorter cycles

### Example Decision

```
Input:
  - Vehicle count: 85
  - Time period: morning_peak
  - Wait time: 55 sec
  - Queue: 40 vehicles

ML Model Prediction: HIGH

Decision Logic:
  1. Vehicle count 85 → base green = 90 sec
  2. Time period is morning_peak → add 15 sec
  3. Final decision: 90 + 15 = 105 sec
  
Output: GREEN for 105 seconds
```

---

## Phase 3A — Option B (Proportional Logic)

**File:** `junction_agent.py`

**Class:** `JunctionAgent`

**Methods:**
- `__init__(road_name, model_path)` — initialize agent
- `observe(vehicle_count, wait_time, queue_length, time_period)` — read state
- `predict_congestion()` — use ML model
- `decide_green_time()` — convert to signal timing
- `execute()` — return decision

**Usage:**
```python
# Create agent for Kaduwela road
agent = JunctionAgent("kaduwela", "models/kaduwela_congestion_model.pkl")

# Observe current state
agent.observe(vehicle_count=85, wait_time=55, queue_length=40, time_period="morning_peak")

# Get prediction
congestion = agent.predict_congestion()  # Returns: HIGH

# Decide green time
green_time = agent.decide_green_time()  # Returns: 105 seconds

# Execute (in real system, would send to traffic controller)
signal = agent.execute()  # Outputs signal timing
```

---

## Phase 3B — Reinforcement Learning Enhancement (Future)

**What will be added:**

A **Q-Learning layer** that learns optimal green times over multiple trials.

**Structure:**
```python
class JunctionAgent:
    def __init__(self, road_name, model_path):
        self.q_table = {}  # Learn mapping: state → best_green_time
        # ... rest of Phase 3A code ...
        
    def learn(self, vehicle_count, actual_wait_time):
        """Update Q-table based on how well decision worked"""
        # If wait_time improved → higher reward
        # Update Q-table: "For this vehicle count, this green time was good"
```

**In Action:**
```
Trial 1:  85 vehicles → try 90 sec → wait time = 52 sec → reward +10
Trial 2:  85 vehicles → try 95 sec → wait time = 48 sec → reward +15 ← better!
Trial 3:  85 vehicles → try 100 sec → wait time = 50 sec → reward +12

After 50 trials: Agent learns "For 85 vehicles, 95 seconds is optimal"
From then on: Automatically gives 95 seconds
```

---

## Input Data Requirements

Each agent needs:
- **vehicle_count** (int) — total vehicles on road
- **wait_time** (float) — average waiting time in seconds
- **queue_length** (int) — vehicles in queue
- **time_period** (str) — one of: morning_peak, afternoon_peak, evening_peak, off_peak, night

All this data comes from:
- **Live source:** Traffic cameras + YOLO detection (Phase 1 pipeline)
- **Simulation source:** SUMO traffic simulator (current Phase 3 testing)
- **Test data:** Phase 2 CSV dataset

---

## Integration with Phase 2 ML Model

Each agent loads the trained XGBoost model:

```python
import pickle

# Load Phase 2 model
with open('models/kaduwela_congestion_model.pkl', 'rb') as f:
    ml_model = pickle.load(f)

# Agent uses it to predict
prediction = ml_model.predict([[time_period_encoded, vehicle_count, wait_time, queue_length]])
# Returns: 0 (LOW), 1 (MEDIUM), or 2 (HIGH)
```

---
