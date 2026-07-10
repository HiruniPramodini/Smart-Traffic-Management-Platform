from backend.junction_agent import JunctionAgent

agent = JunctionAgent("kaduwela", "models/kaduwela_congestion_model.pkl")

print("=== Phase 3B: Q-Learning in Action ===\n")

# Simulate multiple decisions with feedback
scenarios = [
    (85, 55, 40, "morning_peak"),  # HIGH
    (85, 52, 38, "morning_peak"),  # HIGH (better)
    (60, 35, 30, "off_peak"),      # MEDIUM
    (60, 33, 28, "off_peak"),      # MEDIUM (better)
]

for i, (vc, wt, ql, tp) in enumerate(scenarios, 1):
    print(f"Trial {i}: {vc} vehicles, {tp}")
    agent.observe(vc, wt, ql, tp)
    green_time = agent.execute()
    print(f"  Decision: {green_time} seconds green")
    
    # Simulate actual wait time (feedback)
    agent.learn(actual_wait_time=wt)
    print()

# Show what agent learned
print("\n=== What Agent Learned ===")
for congestion, actions in agent.q_table.items():
    print(f"Congestion Level {congestion}:")
    for green_time, reward in actions.items():
        print(f"  {green_time}s green → reward {reward}")