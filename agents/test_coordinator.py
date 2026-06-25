from coordinator_agent import CoordinatorAgent

coordinator = CoordinatorAgent()

print("=" * 50)
print("PHASE 4: COORDINATOR AGENT TEST")
print("=" * 50)

# Define observations for all 3 junctions
observations = {
    "Kaduwela": {
        "vehicle_count": 85,
        "wait_time": 55,
        "queue_length": 40,
        "time_period": "morning_peak"
    },
    "Koswatta": {
        "vehicle_count": 45,
        "wait_time": 25,
        "queue_length": 20,
        "time_period": "morning_peak"
    },
    "Battaramulla": {
        "vehicle_count": 65,
        "wait_time": 40,
        "queue_length": 30,
        "time_period": "morning_peak"
    }
}

print("\n--- Input: Vehicle Observations ---")
for junction, data in observations.items():
    print(f"{junction}: {data['vehicle_count']} vehicles, {data['wait_time']}s wait")

# Step 1: Observe all junctions
coordinator.observe_all(observations)

# Step 2: Get predictions and coordinate
signal_plan = coordinator.execute()

# Step 3: Display coordinated plan
coordinator.print_plan()

print("--- Coordination Logic ---")
print("Priority: Kaduwela (busiest) → Battaramulla (medium) → Koswatta (lightest)")
print("Vehicles flow: Kaduwela GREEN → then Battaramulla GREEN → then Koswatta GREEN")
print("This creates a GREEN WAVE along the corridor\n")

# Simulate actual results and learning
actual_wait_times = {
    "Kaduwela": 48,    # Better than 55
    "Koswatta": 22,    # Better than 25
    "Battaramulla": 38  # Better than 40
}

print("--- Learning from Results ---")
coordinator.learn_all(actual_wait_times)

print("\n--- Q-Tables After Learning ---")
for junction_name, agent in coordinator.agents.items():
    if agent.q_table:
        print(f"\n{junction_name} Q-Table:")
        for congestion, actions in agent.q_table.items():
            print(f"  Congestion {congestion}: {actions}")
    else:
        print(f"\n{junction_name}: Not enough data to learn yet")