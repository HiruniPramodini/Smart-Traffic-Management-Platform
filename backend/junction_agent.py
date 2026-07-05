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
