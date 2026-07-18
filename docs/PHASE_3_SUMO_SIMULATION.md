# Phase 3: Junction Agent & Reinforcement Learning

> [!NOTE]
> This file is a mirror of [PHASE_3_JUNCTION_AGENT.md](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/docs/PHASE_3_JUNCTION_AGENT.md) representing Phase 3 of the Smart Traffic Management Platform.

## Overview

Phase 3 introduces the **Junction AI Agent** (implemented in the `JunctionAgent` class). Each junction operates an autonomous agent that monitors incoming traffic lanes, calls the ML model to predict future congestion, and determines signal timing. 

Phase 3 consists of two parts:
* **Phase 3A:** Rule-Based and time-aware signal timing decisions.
* **Phase 3B:** Reinforcement Learning (Q-learning) to dynamically optimize and adapt timings based on live feedback.

---

## Agent Observe-Think-Act Loop

The agent runs a cyclical control loop every signal phase cycle:

```
    [Observe] ────> Reads vehicle count, wait times, queue lengths, time, weather, and direction demand
        │
    [Think]   ────> Feeds state into the Phase 2 XGBoost model to predict 15-minute look-ahead congestion
        │
    [Act]     ────> Selects green timing (via Rule-Based or Q-Learning) and splits time between directions
```

---

## Phase 3A: Rule-Based Control

The rule-based decision logic maps the predicted congestion level to a base green timing, modified by engineering safety bounds:

| Predicted Congestion | Congestion Code | Base Green Time |
|----------------------|-----------------|-----------------|
| **LOW**              | 0               | 45 seconds      |
| **MEDIUM**           | 1               | 65 seconds      |
| **HIGH**             | 2               | 90 seconds      |

### Peak Period Adjustments:
To prevent extreme waiting times, the decisions are bounded by the following time-period constraints:
* **Night hours (10 PM - 5 AM):** Reduced timings to prevent empty roads waiting on red lights (caps timing to max 75 seconds).
* **Off-Peak hours:** Standard timings (caps timing to max 80 seconds).
* **Peak hours:** Timings extended to manage high volumes (caps timing to max 120 seconds).

---

## Phase 3B: Q-Learning RL Enhancement

To overcome the limitations of static rules, we implement a **tabular Q-learning** agent. Over repeated cycles, the agent learns which green timings yield the lowest waiting times.

### RL Design Elements:
1. **States ($S$):** Congestion level predicted by the XGBoost model (LOW: 0, MEDIUM: 1, HIGH: 2).
2. **Actions ($A$):** Candidate green light durations: `[45, 60, 75, 90, 105, 120]` seconds.
3. **Reward ($R$):** The negative of the average vehicle wait time:
   $$R = -\text{actual\_wait\_time}$$
   *Minimizing waiting time directly maximizes the agent's reward.*
4. **Exploration Strategy:** Epsilon-greedy action selection ($\epsilon = 0.15$):
   * 85% of the time, the agent chooses the action with the highest reward in the Q-table.
   * 15% of the time, the agent explores a random candidate timing.

### Learning Update:
The Q-table maps `(congestion_level) -> {green_time: reward}` and updates when the simulation steps forward:
```python
def learn(self, actual_wait_time):
    green_time = self.decide_green_time()
    reward = -actual_wait_time
    table = self.q_table[self.congestion_level]
    if green_time not in table or reward > table[green_time]:
        table[green_time] = reward
```

---

## Directional Splits

After determining the optimal overall green time for the junction, the agent splits the time between the **main corridor** and **cross-roads** based on real-time direction demand percentages:
* Main road demand is calculated as the proportion of vehicles headed toward Colombo or coming from Colombo.
* A **Fairness Minimum Green Time** of **30 seconds** is enforced on all arms to ensure low-priority directions are never starved.

---

## Execution & Testing

The agent and testing wrappers are located in:
* **Core Agent:** [junction_agent.py](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/backend/junction_agent.py)
* **RL Test Script:** [test_agent_rl.py](file:///c:/Users/hirun/Desktop/Smart-Traffic-Management-Platform%201/Smart-Traffic-Management-Platform/agents/test_agent_rl.py)

To test the RL training loop and view the agent's learning progression over successive steps:
```bash
python agents/test_agent_rl.py
```
