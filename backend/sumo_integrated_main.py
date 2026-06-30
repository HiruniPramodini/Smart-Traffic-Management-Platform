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
