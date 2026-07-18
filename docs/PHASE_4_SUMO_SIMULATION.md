# Phase 4: Coordinated Multi-Agent Control

> [!NOTE]
> This file is a mirror of [PHASE_4_COORDINATOR.md](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/docs/PHASE_4_COORDINATOR.md) representing Phase 4 of the Smart Traffic Management Platform.

## Overview

Phase 4 implements the **Coordinator Agent** layer. While Phase 3 manages individual intersections independently, Phase 4 orchestrates multiple junctions along the corridor to achieve a **Green Wave** (minimizing stops for vehicles traveling through consecutive junctions) and manage congestion bottlenecks.

Phase 4 is split into:
* **Phase 4A (Basic Coordination):** Offsetting signal timers based on general junction congestion.
* **Phase 4B (Directional Awareness):** Factoring in flow directions (e.g., toward Colombo in the morning) to dynamically adjust priority.

---

## Architecture: Multi-Agent Network

```
                ┌───────────────────────────────────┐
                │        Coordinator Agent          │
                └─────────────────┬─────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
 ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
 │ Ranala Agent  │◄──────►│Kaduwela Agent │◄──────►│ Malabe Agent  │
 └───────────────┘        └───────────────┘        └───────────────┘
```

The Coordinator Agent queries state predictions from all individual `JunctionAgent` instances, determines priorities, and adjusts offsets and phase lengths.

---

## Phase 4A: Basic Coordinator

In the basic coordinator model, junctions are dynamically prioritized based on their predicted congestion level.

### Coordination Strategy:
1. **Gather Predictions:** Collect 15-minute look-ahead congestion levels (LOW, MEDIUM, HIGH) from all agents.
2. **Prioritization Sort:** Sort junctions from most congested to least congested.
3. **Signal Phase Offsetting:** Allocate green light windows sequentially, adding a 4-second safety buffer (yellow light clearance) between cycles to prevent collisions.
4. **Calculated Offset:** The start offset of each junction is calculated as the sum of green times and safety yellow buffers of all higher-priority junctions in the sequence.

---

## Phase 4B: Direction-Aware Coordinator

Phase 4B enhances the coordinator by introducing **Directional Traffic Breakdown** tracking. Traffic in the Colombo-Malabe-Kaduwela corridor exhibits heavy directional peaks:
* **Morning Peak:** ~70% of vehicles travel **inbound** (toward Colombo).
* **Evening Peak:** ~70% of vehicles travel **outbound** (from Colombo).

### The Algorithm:
The coordinator in [coordinator_agent_4b.py](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/agents/coordinator_agent_4b.py) tracks these demand splits:

1. **Calculate Demand Proportions:** Junction agents observe the percentage of vehicles headed toward the priority direction vs. cross-streets.
2. **Dynamic Green Splitting:** The total green light budget is split proportionally between the priority corridor and the minor roads.
3. **Fairness Minimum Constraint:** Enforces a minimum safety duration of **30 seconds** on cross-roads, guaranteeing that local streets are never entirely starved of green lights.
4. **Coordinated Signal Plan:** Produces an optimized corridor timing table outlining green times and start offsets customized per direction.

---

## Code Files & Verification

The Phase 4 logic is implemented and tested across the following files:
* **Basic Coordinator:** [coordinator_agent.py](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/agents/coordinator_agent.py)
* **Direction-Aware Coordinator:** [coordinator_agent_4b.py](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/agents/coordinator_agent_4b.py)
* **Verification Tests:**
  * [test_coordinator.py](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/agents/test_coordinator.py)
  * [test_coordinator_4b.py](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/agents/test_coordinator_4b.py)

### How to Run the Coordinated Signal Plan Test:
Execute the test script to output the coordinated signal offset tables:
```bash
python agents/test_coordinator_4b.py
```
This test outputs the structured plan showing:
* Active green wave directions.
* Prioritized green timings for the main corridor.
* Offsets and congestion details per direction.
