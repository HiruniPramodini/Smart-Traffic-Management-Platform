"""
JunctionAgent — Phase 3A (rule-based) + Phase 3B (Q-learning)

NOTE FOR THE PROJECT OWNER:
This file was MISSING from the uploaded zip. Only compiled bytecode
(backend/__pycache__/junction_agent.cpython-*.pyc) existed, which is why
`agents/coordinator_agent.py` and `agents/coordinator_agent_4b.py` could
never actually run (they do `from backend.junction_agent import JunctionAgent`).
This is a reconstruction built strictly from the algorithm described in
docs/PROJECT_SUMMARY.md (Phase 3A / Phase 3B sections), so it matches your
documented design:

  congestion -> base green time
    LOW    -> 60s
    MEDIUM -> 70s
    HIGH   -> 90s

  then capped by time_period:
    morning_peak / evening_peak -> no cap
    afternoon_peak              -> cap 85s
    off_peak                    -> cap 80s
    night                       -> cap 75s

  Q-learning: Q[congestion_level][green_time] = observed reward (-wait_time)
  Agent explores nearby green-time actions and gradually prefers the one
  with the best (least negative) reward for that congestion level.
"""

import pickle
import random


class JunctionAgent:
    CONGESTION_NAMES = ["LOW", "MEDIUM", "HIGH"]

    # Phase 3A base green times
    BASE_GREEN = {0: 60, 1: 70, 2: 90}

    # Phase 3A time-period caps (None = no cap)
    PERIOD_CAP = {
        "morning_peak": None,
        "evening_peak": None,
        "afternoon_peak": 85,
        "off_peak": 80,
        "night": 75,
    }

    # Candidate actions Q-learning is allowed to explore around the base
    CANDIDATE_GREEN_TIMES = [50, 60, 70, 80, 90, 100]

    FAIRNESS_MIN_GREEN = 30  # Phase 4B fairness minimum

    def __init__(self, road_name, model_path=None, epsilon=0.15):
        self.road_name = road_name
        self.model = None
        self.epsilon = epsilon  # exploration rate for Q-learning

        if model_path:
            try:
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
            except Exception:
                # Model file missing / xgboost not installed / version mismatch.
                # Fall back to the rule-based classifier below so the agent
                # still works end-to-end.
                self.model = None

        # Latest observation
        self.vehicle_count = 0
        self.wait_time = 0
        self.queue_length = 0
        self.time_period = "off_peak"
        self.direction_demand = {}

        # Latest prediction
        self.congestion_level = 0  # 0=LOW,1=MEDIUM,2=HIGH

        # Q-table: {congestion_level: {green_time: reward}}
        self.q_table = {0: {}, 1: {}, 2: {}}
