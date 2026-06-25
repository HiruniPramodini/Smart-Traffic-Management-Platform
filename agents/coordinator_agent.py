import pickle
from junction_agent import JunctionAgent

class CoordinatorAgent:
    def __init__(self):
        # Create 3 independent junction agents
        self.agents = {
            "Kaduwela": JunctionAgent("Kaduwela", "models/kaduwela_congestion_model.pkl"),
            "Koswatta": JunctionAgent("Koswatta", "models/kaduwela_congestion_model.pkl"),  # Use same model for demo
            "Battaramulla": JunctionAgent("Battaramulla", "models/kaduwela_congestion_model.pkl")  # Use same model for demo
        }
        
        # Store current state of all junctions
        self.junction_states = {}
        
        # Coordinated signal plan
        self.signal_plan = {}
    
    def observe_all(self, observations):
        """
        Observe all junctions
        
        observations format:
        {
            "Kaduwela": {"vehicle_count": 85, "wait_time": 55, "queue_length": 40, "time_period": "morning_peak"},
            "Koswatta": {...},
            "Battaramulla": {...}
        }
        """
        for junction_name, data in observations.items():
            if junction_name in self.agents:
                self.agents[junction_name].observe(
                    data["vehicle_count"],
                    data["wait_time"],
                    data["queue_length"],
                    data["time_period"]
                )
                self.junction_states[junction_name] = data
    
    def get_individual_predictions(self):
        """Get congestion predictions from all agents"""
        predictions = {}
        for junction_name, agent in self.agents.items():
            agent.predict_congestion()
            predictions[junction_name] = {
                "congestion_level": agent.congestion_level,
                "road_name": agent.road_name
            }
        return predictions
    
    def coordinate_green_wave(self):
        """
        Coordinator decides optimal timing for all junctions
        
        Goal: Create green wave so vehicles flow smoothly
        
        Strategy:
        1. Give more green time to busier junctions
        2. Offset signal timing so vehicles can flow continuously
        3. Balance fairness across junctions
        """
        
        # Get individual decisions first
        individual_decisions = {}
        for junction_name, agent in self.agents.items():
            green_time = agent.decide_green_time()
            
            individual_decisions[junction_name] = green_time
        
        # Get congestion levels
        congestion_levels = {}
        for junction_name, agent in self.agents.items():
            congestion_levels[junction_name] = agent.congestion_level
        
        # Coordinator logic: adjust timings for green wave
        self.signal_plan = {}
        current_offset = 0
        
        # Sort junctions by congestion (HIGH first, LOW last)
        # This gives priority to busier junctions
        sorted_junctions = sorted(
            congestion_levels.items(),
            key=lambda x: x[1],
            reverse=True  # HIGH (2) → MEDIUM (1) → LOW (0)
        )
        
        for junction_name, congestion in sorted_junctions:
            green_time = individual_decisions[junction_name]
            
            self.signal_plan[junction_name] = {
                "green_time": green_time,
                "start_offset": current_offset,
                "congestion": congestion
            }
            
            # Next junction starts after this one finishes
            current_offset += green_time + 4  # +4 for yellow light
        
        return self.signal_plan
    
    def learn_all(self, actual_wait_times):
        """
        All agents learn from actual results
        
        actual_wait_times format:
        {
            "Kaduwela": 52,
            "Koswatta": 35,
            "Battaramulla": 40
        }
        """
        for junction_name, wait_time in actual_wait_times.items():
            if junction_name in self.agents:
                self.agents[junction_name].learn(wait_time)
    
    def execute(self):
        """Main workflow: predict → coordinate → return plan"""
        self.get_individual_predictions()
        coordinated_plan = self.coordinate_green_wave()
        return coordinated_plan
    
    def print_plan(self):
        """Display the coordinated signal plan"""
        print("\n=== COORDINATOR SIGNAL PLAN ===\n")
        total_cycle = sum(
            plan["green_time"] + 4 
            for plan in self.signal_plan.values()
        )
        
        for junction_name, plan in self.signal_plan.items():
            congestion_name = ["LOW", "MEDIUM", "HIGH"][plan["congestion"]]
            print(f"{junction_name}:")
            print(f"  Congestion: {congestion_name}")
            print(f"  Green time: {plan['green_time']} seconds")
            print(f"  Start offset: {plan['start_offset']} seconds")
            print()
        
        print(f"Total cycle time: {total_cycle} seconds\n")