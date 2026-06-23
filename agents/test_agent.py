from junction_agent import JunctionAgent

# Create agent and load the ML model
agent = JunctionAgent("kaduwela", "models/kaduwela_congestion_model.pkl")

# Test 1: LOW congestion (few vehicles)
print("Test 1: LOW congestion")
agent.observe(vehicle_count=25, wait_time=10, queue_length=10, time_period="night")
green_time = agent.execute()
print(f"  Congestion: {agent.congestion_level}, Green time: {green_time} seconds\n")

# Test 2: MEDIUM congestion
print("Test 2: MEDIUM congestion")
agent.observe(vehicle_count=60, wait_time=35, queue_length=30, time_period="off_peak")
green_time = agent.execute()
print(f"  Congestion: {agent.congestion_level}, Green time: {green_time} seconds\n")

# Test 3: HIGH congestion (morning peak)
print("Test 3: HIGH congestion (morning peak)")
agent.observe(vehicle_count=85, wait_time=55, queue_length=40, time_period="morning_peak")
green_time = agent.execute()
print(f"  Congestion: {agent.congestion_level}, Green time: {green_time} seconds\n")

# Test 4: HIGH congestion (night - should be capped)
print("Test 4: HIGH congestion (night - capped)")
agent.observe(vehicle_count=90, wait_time=60, queue_length=45, time_period="night")
green_time = agent.execute()
print(f"  Congestion: {agent.congestion_level}, Green time: {green_time} seconds\n")