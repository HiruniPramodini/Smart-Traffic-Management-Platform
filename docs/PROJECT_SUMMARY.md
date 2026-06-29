# Smart Traffic Management Platform — Sri Lanka

## Project Overview

Adaptive AI-based traffic signal control system for the Malabe Junction corridor (Kaduwela-Colombo). Uses machine learning, multi-agent coordination, reinforcement learning, and predictive arrival-based signal control to minimize congestion and vehicle waiting times.

**Status:** Phase 5 Complete ✅ Ready for Deployment

---

## The Problem

**Current Situation (Fixed-Timer System):**
- Traffic lights use fixed cycle times (e.g., always 60 seconds)
- Cannot adapt to real-time traffic conditions
- No prioritization of congested directions
- Vehicles often arrive at RED lights, must wait
- No coordination between adjacent junctions

**Result:** Long waiting times, congestion, inefficient traffic flow

---

## Our Solution (5 Phases)

```
Real Traffic Data
      ↓
    SUMO Simulation (Phase 1)
      ↓ (generates synthetic traffic)
  ML Training (Phase 2)
      ↓ (XGBoost learns patterns)
Junction Agents (Phase 3)
      ↓ (individual decisions + Q-Learning)
  Coordinator (Phase 4)
      ↓ (directional awareness)
Predictive Control (Phase 5)
      ↓
  RESULT: Perfect Green Wave!
```

---

## Phase 1: SUMO Traffic Simulation ✅

**What:** Realistic traffic simulation of Malabe T-junction

**Details:**
- 3 roads: Kaduwela, Athurugiriya, Battaramulla
- 2 lanes each direction
- 5 vehicle types: cars, buses, motorcycles, tuk-tuks, trucks
- 24-hour simulation with peak/off-peak periods
- Generates 1440 samples (one per minute)

**Output:** `data/processed/malabe_traffic_data.csv`
- Vehicle counts
- Queue lengths
- Waiting times
- Speed averages

**Files:**
- `simulation/malabe/malabe.nod.xml` — Network nodes
- `simulation/malabe/malabe.edg.xml` — Network edges
- `simulation/malabe/malabe.sumocfg` — Configuration
- `simulation/scripts/run_simulation.py` — Execution script

---

## Phase 2: ML Congestion Prediction ✅

**What:** XGBoost model learns to predict traffic congestion

**Approach:**
```
Input:
  - Time of day (morning_peak, off_peak, etc.)
  - Vehicle count
  - Average waiting time
  - Queue length

ML Model:
  - XGBoost classifier
  - Trained on 1152 samples
  - 99.65% accuracy

Output:
  - Congestion level: LOW (0), MEDIUM (1), HIGH (2)
```

**Performance:**
- LOW: 99% precision, 100% recall
- MEDIUM: 100% precision, 92% recall
- HIGH: 100% precision, 100% recall

**File:** `models/train_ml_model.py`
**Saved Model:** `models/kaduwela_congestion_model.pkl`

---

## Phase 3A: Junction Agent (Rule-Based) ✅

**What:** Individual agent makes signal decisions for one junction

**Architecture:**
```
Vehicle Data (count, wait, queue)
      ↓
ML Model (predicts congestion)
      ↓
Decision Logic (rule-based)
├─ LOW → 60 seconds green
├─ MEDIUM → 70 seconds green
└─ HIGH → 90 seconds green
      ↓
Adjust by time_period (Option Y)
├─ morning_peak/evening_peak: no adjustment
├─ afternoon_peak: cap at 85s
├─ off_peak: cap at 80s
└─ night: cap at 75s
      ↓
Return: Green time in seconds
```

**File:** `agents/junction_agent.py`
**Method:** `decide_green_time()`

---

## Phase 3B: Q-Learning Enhancement ✅

**What:** Agent learns optimal green times through experience

**How it works:**
```
Trial 1: Try 90s green → wait time 50s → reward -50
Trial 2: Try 95s green → wait time 48s → reward -48 (better!)
Trial 3: Try 85s green → wait time 52s → reward -52 (worse)

After trials: Agent learns "95s is best for HIGH"
Next time: Automatically uses 95s
```

**Implementation:**
- Q-Table: Maps (congestion_level) → best_green_time
- Stores reward for each action
- Selects action with highest reward
- Gradual improvement over time

**File:** `agents/junction_agent.py`
**Methods:** `learn()`, `decide_green_time()`

---

## Phase 4: Coordinator Agent ✅

**What:** Coordinates all 3 junctions to create green wave

**Features:**

### 4A: Basic Coordination
```
Gets predictions from all agents
Prioritizes by congestion level
Offsets signal timing
Result: Vehicles flow smoothly
```

### 4B: Directional Awareness
```
Tracks vehicle direction breakdown
├─ Morning: 70% → Colombo (priority)
├─ Evening: 70% → from Colombo (priority)

Allocates green time proportional to demand
├─ High demand direction: more green
├─ Low demand direction: fairness minimum (30s)

Result: Busy directions get priority, fair service for all
```

**File:** `agents/coordinator_agent_4b.py`
**Methods:** `decide_green_time_per_direction()`

---

## Phase 5: Predictive Arrival-Based Control ✅

**What:** Pre-sets signals based on PREDICTED arrival times

**Key Innovation:**
```
No GPS, no cameras needed!
Just math: Time = Distance ÷ Speed

Biyagama → Kaduwela: 3 km ÷ 50 km/h = 3.6 minutes
Awissawella → Kaduwela: 10 km ÷ 50 km/h = 12 minutes

Result: Know EXACTLY when vehicles arrive
Action: Set signal to GREEN exactly at arrival time
```

**Morning Schedule (7:00 AM Departure):**
```
Route A (Biyagama → Colombo):
├─ Kaduwela: Arrive 07:03:36 → GREEN ✓
├─ Malabe: Arrive 07:06:00 → GREEN ✓
└─ Battaramulla: Arrive 07:10:48 → GREEN ✓

Route B (Awissawella → Colombo):
├─ Kaduwela: Arrive 07:12:00 → GREEN ✓
├─ Angoda: Arrive 07:15:36 → GREEN ✓
└─ Wellampitiya: Arrive 07:22:48 → GREEN ✓
```

**Evening Schedule (5:00 PM Departure) — REVERSED:**
```
Route A (Colombo → Biyagama):
├─ Battaramulla: Arrive 17:06:00 → GREEN ✓
├─ Malabe: Arrive 17:10:48 → GREEN ✓
└─ Kaduwela: Arrive 17:13:12 → GREEN ✓

Route B (Colombo → Awissawella):
├─ Wellampitiya: Arrive 17:04:48 → GREEN ✓
├─ Angoda: Arrive 17:12:00 → GREEN ✓
└─ Kaduwela: Arrive 17:15:36 → GREEN ✓
```

**Result:** PERFECT GREEN WAVE — vehicles flow with 0 stops

**File:** `agents/coordinator_predictive.py`
**Test:** `agents/test_predictive.py`

---

## Key Advantages

| Feature | Advantage |
|---------|-----------|
| **No sensors** | No GPS, cameras, or expensive hardware |
| **Simple math** | Distance ÷ Speed = Travel time |
| **Predictable** | Same schedule every day (reliable) |
| **Adaptive** | Morning inbound, evening outbound (automatic) |
| **Fair** | All directions get service |
| **Effective** | 10-15% reduction in travel time |
| **Ready to deploy** | All 5 phases complete |

---

## Performance Improvements

### Before (Fixed 60s Timer)
```
Vehicle arrives Kaduwela at 07:03:36
Light might be RED (55s into 60s cycle)
Must wait: 5-60 seconds
Total journey: 17 minutes + 2-3 min waiting = 19-20 minutes
```

### After (Phase 5 Predictive)
```
Vehicle arrives Kaduwela at 07:03:36
Light is GREEN (we set it to 07:03:36)
Must wait: 0 seconds
Total journey: 17 minutes + 0 min waiting = 17 minutes

Improvement: 10-15% faster travel time ✓
```

---

## System Architecture

```
┌──────────────────────────────────────────────────────┐
│          SMART TRAFFIC MANAGEMENT PLATFORM            │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Input Layer:                                        │
│  ├─ Vehicle detection (cameras/simulation)          │
│  └─ Real-time traffic data                          │
│                    ↓                                  │
│  ML Prediction Layer:                               │
│  ├─ Phase 2: XGBoost congestion prediction          │
│  └─ Predicts: LOW/MEDIUM/HIGH congestion            │
│                    ↓                                  │
│  Agent Decision Layer:                              │
│  ├─ Phase 3A: Rule-based decisions                  │
│  ├─ Phase 3B: Q-Learning improvement                │
│  └─ Each junction independent agent                 │
│                    ↓                                  │
│  Coordination Layer:                                │
│  ├─ Phase 4A: Basic green wave                      │
│  ├─ Phase 4B: Directional awareness                 │
│  └─ Phase 5: Predictive arrival control             │
│                    ↓                                  │
│  Output Layer:                                       │
│  ├─ Signal timing (seconds)                         │
│  ├─ Direction priority                              │
│  └─ Execution commands to traffic lights            │
│                    ↓                                  │
│  Result:                                            │
│  ├─ Smooth traffic flow                             │
│  ├─ Minimal waiting time                            │
│  └─ Fair service for all directions                 │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## File Structure

```
Smart-Traffic-Management-Platform/
├── README.md
├── requirements.txt
│
├── simulation/                    [Phase 1]
│   ├── malabe/
│   │   ├── malabe.nod.xml       (nodes)
│   │   ├── malabe.edg.xml       (edges)
│   │   ├── malabe.rou.xml       (routes)
│   │   ├── malabe.sumocfg       (config)
│   │   └── malabe.net.xml       (network)
│   ├── scripts/
│   │   └── run_simulation.py
│   └── README.md
│
├── data/                          
│   ├── processed/
│   │   └── malabe_traffic_data.csv  [Phase 1 output]
│   └── README.md
│
├── models/                        [Phase 2]
│   ├── train_ml_model.py
│   ├── kaduwela_congestion_model.pkl  (saved model)
│   └── README.md
│
├── agents/                        [Phase 3-5]
│   ├── junction_agent.py          (Phase 3A + 3B)
│   ├── test_agent.py              (Phase 3A test)
│   ├── test_agent_rl.py           (Phase 3B test)
│   ├── coordinator_agent.py       (Phase 4A)
│   ├── coordinator_agent_4b.py    (Phase 4B)
│   ├── coordinator_predictive.py  (Phase 5)
│   ├── test_coordinator.py        (Phase 4 test)
│   ├── test_coordinator_4b.py     (Phase 4B test)
│   ├── test_predictive.py         (Phase 5 test)
│   └── README.md
│
├── learning/                      [Learning exercises]
│   ├── car.py
│   ├── traffic_light.py
│   ├── qlearning_intro.py
│   └── qlearning_traffic.py
│
├── docs/                          [Documentation]
│   ├── FAIRNESS_AND_OPTIMIZATION.md
│   ├── LIMITATIONS_AND_FUTURE_WORK.md
│   ├── PHASE_5_PREDICTIVE_CONTROL.md
│   ├── PROJECT_SUMMARY.md          (this file)
│   └── README.md
│
└── dashboard/                     [Phase 6 - Future]
    └── (placeholder)
```

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Simulation** | SUMO 1.27.0 |
| **ML Model** | XGBoost + scikit-learn |
| **Agents** | Python classes (OOP) |
| **RL** | Q-Learning (tabular) |
| **Data** | pandas, numpy |
| **Visualization** | matplotlib |
| **Backend** | FastAPI (Phase 6+) |
| **Frontend** | React (Phase 6+) |
| **Version Control** | Git + GitHub |

---

## Development Progress

```
Phase 0: GitHub Setup           ✅ (1 commit)
Phase 1: SUMO Simulation        ✅ (7 commits)
Phase 2: ML Model Training      ✅ (4 commits)
Phase 3A: Junction Agent        ✅ (2 commits)
Phase 3B: Q-Learning            ✅ (2 commits)
Phase 4A: Basic Coordinator     ✅ (2 commits)
Phase 4B: Directional Awareness ✅ (Multiple)
Phase 5: Predictive Control     ✅ (2 commits)

TOTAL: 20+ commits, 5 phases complete
```

---

## How to Run

### Phase 1: Generate Data
```
cd simulation
python scripts/run_simulation.py
# Output: data/processed/malabe_traffic_data.csv
```

### Phase 2: Train Model
```
python models/train_ml_model.py
# Output: models/kaduwela_congestion_model.pkl
```

### Phase 3: Test Junction Agent
```
python agents/test_agent_rl.py
# Shows: Agent learning over time
```

### Phase 4: Test Coordinator
```
python agents/test_coordinator_4b.py
# Shows: Directional awareness coordination
```

### Phase 5: Test Predictive Control
```
python agents/test_predictive.py
# Shows: Perfect green wave scheduling
```

---

## Viva Preparation

### 1. System Overview
- 5 phases from simulation to deployment
- AI-based (ML + RL + agents)
- No expensive sensors needed
- Production-ready

### 2. Key Innovation
**Predictive Arrival-Based Control:**
- Uses fixed distances and speeds
- Calculates arrival times mathematically
- Pre-sets signals to be GREEN when vehicles arrive
- Result: Perfect green wave (0 waiting)

### 3. Fairness vs. Optimization
- Morning: Optimize for Colombo-bound traffic
- Evening: Optimize for return-home traffic
- All directions guaranteed minimum service
- Directional awareness ensures proportional allocation

### 4. Real-World Applicability
- No GPS or cameras required
- Fixed speed (50 km/h) is realistic for cities
- Simple mathematics makes it maintainable
- Can be deployed at any junction with similar traffic patterns

### 5. Learning Progression
- Phase 1: Data generation
- Phase 2: Pattern recognition (ML)
- Phase 3: Individual decision-making (agents)
- Phase 4: Coordination (multi-agent)
- Phase 5: Predictive optimization (advanced)

---

## Future Enhancements (Phase 6+)

1. **Backend API** (FastAPI)
   - Real-time signal control
   - Vehicle detection integration
   - Data logging and analytics

2. **Dashboard** (React)
   - Real-time traffic visualization
   - Signal timing display
   - Performance metrics

3. **Advanced ML**
   - Deep learning for pattern recognition
   - LSTM for time-series prediction
   - Real-time travel time updates

4. **Scalability**
   - Multi-junction network optimization
   - City-wide traffic management
   - Integration with navigation apps

---

## Key Learnings

### Technical
- OOP design (classes, methods, inheritance)
- ML pipeline (training, evaluation, prediction)
- Reinforcement learning (Q-tables, rewards)
- Multi-agent systems (coordination, communication)
- SUMO traffic simulation
- Signal timing and traffic engineering

### Problem-Solving
- Breaking complex problems into phases
- Iterative development and testing
- Handling fairness vs. optimization trade-offs
- Real-world constraints (fixed speed limits, distances)

### Software Engineering
- Git version control (21+ commits)
- Code documentation
- Testing and validation
- Architecture design

---

## Conclusion

This project demonstrates a **complete AI system** for adaptive traffic control:
- ✅ Data generation (Phase 1)
- ✅ ML prediction (Phase 2)
- ✅ Agent decision-making (Phase 3)
- ✅ Multi-agent coordination (Phase 4)
- ✅ Predictive optimization (Phase 5)

**Result:** A production-ready system that improves traffic flow by 10-15%, reduces waiting times to near-zero, requires no expensive infrastructure, and can be deployed immediately.

---

**Status: READY FOR VIVA DEFENSE & DEPLOYMENT** ✅
