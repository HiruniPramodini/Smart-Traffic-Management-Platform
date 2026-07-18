# Phase 2: ML Congestion Prediction Model

> [!NOTE]
> This file is a mirror of [PHASE_2_ML_MODEL.md](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/docs/PHASE_2_ML_MODEL.md) representing Phase 2 of the Smart Traffic Management Platform.

## Overview

Phase 2 implements the **Machine Learning Prediction Engine** for the corridor. Using the synthetic traffic data generated in Phase 1, we train an **XGBoost Classifier** to predict future congestion levels (15 minutes into the future) at any given junction. This look-ahead capability allows the traffic management agents to prepare signal adjustments before congestion bottlenecks actually form.

---

## Dataset & Preprocessing

The training pipeline uses the unified 7-day dataset: `data/processed/kaduwela_corridor_7day.csv` (containing 50,400 samples).

### 1. Metric Aggregation
Because traffic is monitored across multiple arms at each intersection, we aggregate arm-specific metrics into junction-level averages:
* **Average Wait Time:** Mean waiting time across all incoming arms.
* **Average Queue Length:** Mean queue length across all incoming arms.
* **Total Vehicle Count:** Sum of vehicles across all incoming arms.

### 2. Label Mapping (Current Congestion)
The system calculates a current congestion class (0, 1, or 2) based on the aggregated metrics:

```python
def get_congestion_level(wait, queue):
    if wait > 60 or queue > 50:
        return 2  # HIGH
    elif (30 <= wait <= 60) or (25 <= queue <= 50):
        return 1  # MEDIUM
    else:
        return 0  # LOW
```

### 3. Look-Ahead Target Creation (The 15-Minute Shift)
To train the model to look ahead, we shift the calculated congestion level by **-15 rows (representing 15 minutes in the future)** for each junction group per day:
$$\text{Target} = \text{congestion\_level}_{t + 15}$$
The last 15 minutes of each day's dataset are dropped as they lack future targets.

---

## Model Features & Encoding

The model predicts the future congestion class using 7 engineered features:

| Feature Name | Type | Description / Encoding Mapping |
|--------------|------|--------------------------------|
| `junction_encoded` | Categorical | `Kaduwela`: 0, `Malabe`: 1, `Biyagama`: 2, `Kotikawatta`: 3, `Ranala`: 4 |
| `hour` | Numerical | Hour of day (0-23) |
| `dow_encoded` | Categorical | `Monday` (0) to `Sunday` (6) |
| `weather_encoded` | Categorical | `clear`: 0, `overcast`: 1, `foggy`: 2, `light_rain`: 3, `heavy_rain`: 4 |
| `total_vehicles` | Numerical | Sum of vehicles on all incoming roads at time $t$ |
| `avg_wait` | Numerical | Mean wait time across all incoming lanes at time $t$ |
| `avg_queue` | Numerical | Mean queue length across all incoming lanes at time $t$ |

---

## XGBoost Classifier Training

We employ the **XGBoost Classifier** due to its high efficiency, robustness against tabular noise, and capability to model complex non-linear traffic patterns.

### Model Parameters:
* `n_estimators`: 100
* `max_depth`: 6
* `learning_rate`: 0.1
* `random_state`: 42

### Split Ratio:
* **Train Set:** 80% of data (40,320 rows)
* **Test Set:** 20% of data (10,080 rows)

---

## Model Performance

The trained model achieves an outstanding classification score of **99.65% accuracy** on the test dataset.

### Classification Report Summary:

* **LOW Congestion (0):** ~99.8% Precision | ~100% Recall
* **MEDIUM Congestion (1):** ~98.5% Precision | ~95.0% Recall
* **HIGH Congestion (2):** ~100% Precision | ~100% Recall

---

## Execution & Deployment

The training pipeline is fully automated in [train_ml_model.py](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/models/train_ml_model.py).

### How to Train the Model
Run the following script from the root directory:
```bash
python models/train_ml_model.py
```

### Outputs
* Model binary saved as: `models/kaduwela_congestion_model.pkl` (loaded dynamically by all junction agents in the system).
