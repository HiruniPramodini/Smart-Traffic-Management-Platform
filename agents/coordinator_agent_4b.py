import pickle
from junction_agent import JunctionAgent

class CoordinatorAgentV2:
    """Phase 4B: Demand-Responsive Coordinator with Directional Awareness"""
    
    def __init__(self):
        # Create 3 independent junction agents
        self.agents = {
            "Kaduwela": JunctionAgent("Kaduwela", "models/kaduwela_congestion_model.pkl"),
            "Koswatta": JunctionAgent("Koswatta", "models/kaduwela_congestion_model.pkl"),
            "Battaramulla": JunctionAgent("Battaramulla", "models/kaduwela_congestion_model.pkl")
        }
        
        # Store current state
        self.junction_states = {}
        self.signal_plan = {}
        self.time_period = None
    
    def observe_all(self, observations):
        """
        Observe all junctions WITH DIRECTION DATA
        
        observations format:
        {
            "Kaduwela": {
                "vehicle_count": 85,
                "wait_time": 55,
                "queue_length": 40,
                "time_period": "morning_peak",
                "direction_breakdown": {
                    "toward_colombo": 60,
                    "toward_malabe": 15,
                    "other": 10
                }
            },
            ...
        }
        """
        for junction_name, data in observations.items():
            if junction_name in self.agents:
                self.agents[junction_name].observe(
                    data["vehicle_count"],
                    data["wait_time"],
                    data["queue_length"],
                    data["time_period"],
                    direction_breakdown=data.get("direction_breakdown", None)
                )
                self.junction_states[junction_name] = data
                self.time_period = data["time_period"]
    
    def get_individual_predictions(self):
        """Get congestion predictions from all agents"""
        predictions = {}
        for junction_name, agent in self.agents.items():
            agent.predict_congestion()
            predictions[junction_name] = {
                "congestion_level": agent.congestion_level,
                "road_name": agent.road_name,
                "direction_demand": agent.direction_demand
            }
        return predictions
    
    def coordinate_green_wave_with_direction(self):
        """
        Coordinator decides optimal timing for all junctions AND directions
        
        Strategy:
        1. Give more green to directions with higher demand
        2. Maintain fairness minimum for all directions
        3. Offset signals for green wave
        4. Prioritize during peak times
        """
        
        self.signal_plan = {}
        current_offset = 0
        
        # Get individual decisions (per-direction)
        individual_decisions = {}
        congestion_levels = {}
        
        for junction_name, agent in self.agents.items():
            result = agent.execute()
            individual_decisions[junction_name] = result["per_direction_green_time"]
            congestion_levels[junction_name] = result["congestion_level"]
        
        # Sort junctions by congestion
        sorted_junctions = sorted(
            congestion_levels.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Coordinate each junction
        for junction_name, congestion in sorted_junctions:
            per_direction_times = individual_decisions[junction_name]
            direction_demand = self.agents[junction_name].direction_demand
            
            self.signal_plan[junction_name] = {}
            
            # For each direction in this junction
            for direction, green_time in per_direction_times.items():
                demand = direction_demand.get(direction, 0)
                
                self.signal_plan[junction_name][direction] = {
                    "green_time": green_time,
                    "start_offset": current_offset,
                    "congestion": congestion,
                    "demand_percentage": demand * 100
                }
            
            # Calculate max green time for this junction
            max_green = max(per_direction_times.values()) if per_direction_times else 60
            
            # Next junction starts after this one finishes
            current_offset += max_green + 4  # +4 for yellow light
        
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
        coordinated_plan = self.coordinate_green_wave_with_direction()
        return coordinated_plan
    
    def print_plan(self):
        """Display the coordinated signal plan with direction awareness"""
        print("\n" + "="*70)
        print("PHASE 4B: DEMAND-RESPONSIVE COORDINATOR SIGNAL PLAN")
        print("="*70 + "\n")
        
        for junction_name, directions in self.signal_plan.items():
            print(f"\n{junction_name.upper()} JUNCTION:")
            print("-" * 70)
            
            for direction, plan in directions.items():
                congestion_names = ["LOW", "MEDIUM", "HIGH"]
                congestion_name = congestion_names[plan["congestion"]]
                
                print(f"  Direction: {direction}")
                print(f"    ├─ Congestion: {congestion_name}")
                print(f"    ├─ Demand: {plan['demand_percentage']:.1f}% of vehicles")
                print(f"    ├─ Green time: {plan['green_time']:.0f} seconds")
                print(f"    └─ Start offset: {plan['start_offset']:.0f} seconds")
            
            print()
        
        print("="*70)
        print("STRATEGY: Priority given to high-demand directions")
        print("FAIRNESS: All directions get minimum 30 seconds green time")
        print("="*70 + "\n")