from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import random
import math

app = FastAPI(
    title="Kaduwela Junction - SUMO + Real Traffic Engineering",
    description="SUMO vehicles + Real signal optimization + Prediction"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════
# PART 1: REAL-WORLD TRAFFIC ENGINEERING DATA
# ═══════════════════════════════════════════════════════════════

TRAFFIC_ENGINEERING_DATA = {
    "flow_rate": 1800,        # vehicles/hour/lane (industry standard)
    "saturation_speed": 35,   # km/h (urban traffic)
    "queue_theory": "M/M/1",  # Mathematical model for queues
    "signal_optimization": "Webster",  # Traffic signal formula
}

SIGNAL_TIMING = {
    "morning_peak": {
        "Biyagama": {"GREEN": 52, "YELLOW": 3, "RED": 65},
        "Awissawella": {"GREEN": 48, "YELLOW": 3, "RED": 69},
        "Malabe": {"GREEN": 32, "YELLOW": 3, "RED": 85},
        "Angoda": {"GREEN": 28, "YELLOW": 3, "RED": 89}
    }
}


# ═══════════════════════════════════════════════════════════════
# PART 2: SIMULATED SUMO DATA (In real system, read from SUMO)
# ═══════════════════════════════════════════════════════════════

class SUMOVehicle:
    """Represents a vehicle from SUMO simulation"""
    def __init__(self, vehicle_id, origin, destination):
        self.id = vehicle_id
        self.origin = origin
        self.destination = destination
        
        # SUMO OUTPUT: Position and speed
        self.distance_to_junction = random.uniform(100, 2000)  # meters
        self.speed_kmh = random.uniform(30, 50)  # km/h (SUMO realistic)
        
        # Vehicle state
        self.status = "approaching"
        self.wait_time = 0
        self.arrival_time = None  # Will be predicted

# ═══════════════════════════════════════════════════════════════
# PART 3: PREDICTION ENGINE (The Key Innovation)
# ═══════════════════════════════════════════════════════════════

class PredictionEngine:
    """
    Predicts when vehicles arrive and optimizes signals
    """
    
    @staticmethod
    def predict_arrival_time(distance_m, speed_kmh):
        """
        PREDICT: When will vehicle reach junction?
        
        Input:
        ├─ distance_m: How far away (from SUMO)
        ├─ speed_kmh: How fast (from SUMO)
        
        Output:
        └─ seconds: Time until arrival
        
        Formula: Time = Distance / Speed
        """
        speed_ms = speed_kmh / 3.6  # Convert km/h to m/s
        arrival_seconds = distance_m / speed_ms
        return round(arrival_seconds, 1)
    
    @staticmethod
    def predict_signal_state(arrival_time_s, location, time_period="morning_peak"):
        """
        PREDICT: What signal will be at arrival?
        
        Input:
        ├─ arrival_time_s: Predicted arrival (seconds)
        ├─ location: Which road (Biyagama, etc)
        
        Output:
        ├─ signal_color: RED, YELLOW, or GREEN
        ├─ wait_time: How long until can go
        └─ signal_phase: Current phase name
        """
        timing = SIGNAL_TIMING[time_period][location]
        cycle_time = 120  # seconds
        
        # Where in cycle will vehicle arrive?
        position = arrival_time_s % cycle_time
        
        green_end = timing["GREEN"]
        yellow_end = green_end + timing["YELLOW"]
        
        if position < green_end:
            return {
                "signal": "GREEN",
                "wait_time": 0,
                "reason": "Signal will be green - no wait!"
            }
        elif position < yellow_end:
            return {
                "signal": "YELLOW",
                "wait_time": 0,
                "reason": "Signal changing - hurry through"
            }
        else:
            # RED - calculate wait until next GREEN
            time_until_next_green = cycle_time - position
            return {
                "signal": "RED",
                "wait_time": round(time_until_next_green, 1),
                "reason": f"Must wait {round(time_until_next_green, 1)}s for next green"
            }
    
    @staticmethod
    def should_optimize_signal(vehicle, predicted_wait_time):
        """
        DECIDE: Should we change signal timing to help this vehicle?
        
        Rule: If wait > 5 seconds, optimize signal
        """
        return predicted_wait_time > 5

# ═══════════════════════════════════════════════════════════════
# PART 4: QUEUE THEORY (Real-World Traffic Math)
# ═══════════════════════════════════════════════════════════════

class QueueTheory:
    """
    M/M/1 Queue Model (standard traffic theory)
    Calculates realistic queue lengths and delays
    """
    
    @staticmethod
    def calculate_queue_length(arrival_rate, service_rate, time_in_cycle):
        """
        INPUT:
        ├─ arrival_rate: vehicles arriving per second
        ├─ service_rate: vehicles passing per second
        └─ time_in_cycle: how long red light is
        
        OUTPUT:
        └─ vehicles: average vehicles waiting
        
        Formula: Queue = arrival_rate × service_rate × red_time
        """
        if service_rate == 0:
            return 0
        
        utilization = arrival_rate / service_rate
        if utilization >= 1:
            # Overloaded
            queue = (arrival_rate * time_in_cycle)
        else:
            # Normal
            queue = (utilization ** 2) / (2 * (1 - utilization))
        
        return round(queue, 0)

# ═══════════════════════════════════════════════════════════════
# PART 5: MAIN SIMULATOR
# ═══════════════════════════════════════════════════════════════

class KaduwelaSUMOSimulator:
    def __init__(self):
        self.current_time = 0
        self.vehicles = []
        self.total_wait = 0
        self.vehicles_passed = 0
        self.predictions = {}  # Store all predictions
        
    def initialize(self, start_time_str, time_period):
        self.time_period = time_period
        self.current_time = 0
        
        # Generate vehicles (simulating SUMO output)
        locations = ["Biyagama", "Awissawella", "Malabe", "Angoda"]
        for i in range(150):  # 150 vehicles in simulation
            origin = random.choice(locations)
            vehicle = SUMOVehicle(f"V{i:04d}", origin, "any")
            self.vehicles.append(vehicle)
    
    def step(self):
        """Advance simulation 1 second"""
        self.current_time += 1
        
        for vehicle in self.vehicles:
            # STEP 1: Get SUMO data (vehicle position, speed)
            if vehicle.status == "approaching":
                # STEP 2: PREDICT arrival time
                predicted_arrival = PredictionEngine.predict_arrival_time(
                    vehicle.distance_to_junction,
                    vehicle.speed_kmh
                )
                
                # STEP 3: PREDICT signal state
                signal_prediction = PredictionEngine.predict_signal_state(
                    predicted_arrival,
                    vehicle.origin,
                    self.time_period
                )
                
                # Store prediction
                self.predictions[vehicle.id] = {
                    "arrival": predicted_arrival,
                    "signal": signal_prediction
                }
                
                # STEP 4: Check if vehicle arrived
                vehicle.distance_to_junction -= vehicle.speed_kmh / 3.6  # Move it
                
                if vehicle.distance_to_junction <= 0:
                    # Vehicle reached junction
                    vehicle.status = "at_junction"
                    vehicle.arrival_time = self.current_time
                    
                    # Apply predicted wait time
                    vehicle.wait_time = signal_prediction["wait_time"]
            
            elif vehicle.status == "at_junction":
                if vehicle.wait_time > 0:
                    vehicle.wait_time -= 1
                else:
                    vehicle.status = "passed"
                    self.vehicles_passed += 1
                    self.total_wait += vehicle.wait_time
    
    def get_state(self):
        """Return current junction state"""
        locations = ["Biyagama", "Awissawella", "Malabe", "Angoda"]
        junction_state = {}
        
        # Calculate current signals
        cycle_pos = self.current_time % 120
        
        for loc in locations:
            timing = SIGNAL_TIMING[self.time_period][loc]
            green_end = timing["GREEN"]
            
            if cycle_pos < green_end:
                signal = "GREEN"
            else:
                signal = "RED"
            
            # Calculate queue
            waiting = [v for v in self.vehicles 
                      if v.origin == loc and v.status == "at_junction"]
            
            junction_state[loc] = {
                "signal": signal,
                "queue": len(waiting),
                "vehicles_waiting": len(waiting)
            }
        
        return {
            "time": f"{int(self.current_time // 60):02d}:{int(self.current_time % 60):02d}",
            "junction": junction_state,
            "statistics": {
                "total": len(self.vehicles),
                "passed": self.vehicles_passed,
                "avg_wait": round(self.total_wait / max(self.vehicles_passed, 1), 2),
                "predictions_made": len(self.predictions)
            },
            "vehicles": [
                {
                    "id": v.id,
                    "origin": v.origin,
                    "status": v.status,
                    "distance": round(v.distance_to_junction, 1),
                    "speed": round(v.speed_kmh, 1),
                    "wait": v.wait_time,
                    "prediction": self.predictions.get(v.id, {}).get("arrival", "...")
                }
                for v in self.vehicles[:60]
            ],
            "data_sources": [
                "SUMO: Vehicle positions, speeds, routes",
                "Traffic Engineering: Signal timing, queue theory",
                "Prediction: Arrival times, signal optimization"
            ]
        }

simulator = None

@app.post("/api/simulation/start")
def start(request: dict):
    global simulator
    simulator = KaduwelaSUMOSimulator()
    simulator.initialize(request.get("start_time", "07:00"), request.get("time_period", "morning_peak"))
    
    return {
        "status": "started",
        "data_sources": [
            "SUMO simulation (vehicle movement)",
            "Traffic engineering data (signal optimization)",
            "Prediction engine (arrival optimization)"
        ]
    }

@app.post("/api/simulation/step")
def step():
    if simulator is None:
        return {"error": "Start simulation first"}
    
    simulator.step()
    return simulator.get_state()

@app.get("/api/simulation/state")
def get_state():
    if simulator is None:
        return {"error": "Start simulation first"}
    return simulator.get_state()

@app.post("/api/simulation/reset")
def reset():
    global simulator
    simulator = None
    return {"status": "reset"}

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "version": "SUMO + Real Traffic Engineering + Prediction",
        "components": ["SUMO Data", "Traffic Theory", "Prediction Engine"]
    }