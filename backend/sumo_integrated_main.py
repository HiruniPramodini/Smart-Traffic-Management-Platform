from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import random

app = FastAPI(
    title="Kaduwela Junction - SUMO + Real Traffic Engineering",
    description="SUMO vehicles + Real signal optimization + Prediction"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class StartRequest(BaseModel):
    start_time: str = "07:00"
    time_period: str = "morning_peak"

class StepRequest(BaseModel):
    steps: int = 1

# Traffic Engineering Data
SIGNAL_TIMING = {
    "morning_peak": {
        "Biyagama": {"GREEN": 52, "YELLOW": 3, "RED": 65},
        "Awissawella": {"GREEN": 48, "YELLOW": 3, "RED": 69},
        "Malabe": {"GREEN": 32, "YELLOW": 3, "RED": 85},
        "Angoda": {"GREEN": 28, "YELLOW": 3, "RED": 89}
    },
    "evening_peak": {
        "Biyagama": {"GREEN": 35, "YELLOW": 3, "RED": 82},
        "Awissawella": {"GREEN": 50, "YELLOW": 3, "RED": 67},
        "Malabe": {"GREEN": 40, "YELLOW": 3, "RED": 77},
        "Angoda": {"GREEN": 45, "YELLOW": 3, "RED": 72}
    }
}

TRAFFIC_VOLUMES = {
    "morning_peak": {
        "Biyagama": 1800,
        "Awissawella": 1650,
        "Malabe": 980,
        "Angoda": 750
    },
    "evening_peak": {
        "Biyagama": 1200,
        "Awissawella": 1450,
        "Malabe": 880,
        "Angoda": 1100
    }
}

class SUMOVehicle:
    def __init__(self, vehicle_id, origin):
        self.id = vehicle_id
        self.origin = origin
        self.distance_to_junction = random.uniform(100, 2500)
        self.speed_kmh = random.uniform(30, 50)
        self.status = "approaching"
        self.wait_time = 0
        self.predicted_arrival = None

class PredictionEngine:
    @staticmethod
    def predict_arrival_time(distance_m, speed_kmh):
        speed_ms = speed_kmh / 3.6
        arrival_seconds = distance_m / speed_ms
        return round(arrival_seconds, 1)
    
    @staticmethod
    def predict_signal_state(arrival_time_s, location, time_period="morning_peak"):
        timing = SIGNAL_TIMING[time_period][location]
        cycle_time = 120
        position = int(arrival_time_s) % cycle_time
        green_end = timing["GREEN"]
        yellow_end = green_end + timing["YELLOW"]
        
        if position < green_end:
            return {"signal": "GREEN", "wait_time": 0}
        elif position < yellow_end:
            return {"signal": "YELLOW", "wait_time": 0}
        else:
            time_until_next_green = cycle_time - position
            return {"signal": "RED", "wait_time": round(time_until_next_green, 1)}

class KaduwelaSUMOSimulator:
    def __init__(self):
        self.current_time = 0
        self.vehicles = []
        self.total_wait = 0
        self.vehicles_passed = 0
        self.predictions_made = 0
        self.time_period = "morning_peak"
        
    def initialize(self, start_time_str, time_period):
        self.time_period = time_period
        self.current_time = 0
        self.vehicles = []
        self.total_wait = 0
        self.vehicles_passed = 0
        self.predictions_made = 0
        
        locations = ["Biyagama", "Awissawella", "Malabe", "Angoda"]
        volumes = TRAFFIC_VOLUMES[time_period]
        
        for location in locations:
            num_vehicles = int(volumes[location] / 3)
            for i in range(num_vehicles):
                vehicle = SUMOVehicle(f"{location[0]}{i:04d}", location)
                self.vehicles.append(vehicle)
    
    def step(self):
        self.current_time += 1
        
        for vehicle in self.vehicles:
            if vehicle.status == "approaching":
                if vehicle.predicted_arrival is None:
                    vehicle.predicted_arrival = PredictionEngine.predict_arrival_time(
                        vehicle.distance_to_junction,
                        vehicle.speed_kmh
                    )
                
                vehicle.distance_to_junction -= vehicle.speed_kmh / 3.6
                
                if vehicle.distance_to_junction <= 0:
                    vehicle.status = "at_junction"
                    signal_pred = PredictionEngine.predict_signal_state(
                        vehicle.predicted_arrival,
                        vehicle.origin,
                        self.time_period
                    )
                    vehicle.wait_time = signal_pred["wait_time"]
                    self.predictions_made += 1
            
            elif vehicle.status == "at_junction":
                if vehicle.wait_time > 0:
                    vehicle.wait_time -= 1
                    self.total_wait += 1
                else:
                    vehicle.status = "passed"
                    self.vehicles_passed += 1
    
    def get_current_signal(self, location):
        timing = SIGNAL_TIMING[self.time_period][location]
        cycle_pos = self.current_time % 120
        green_end = timing["GREEN"]
        
        if cycle_pos < green_end:
            signal = "GREEN"
        else:
            signal = "RED"
        
        queue = len([v for v in self.vehicles 
                    if v.origin == location and v.status == "at_junction"])
        
        return {"signal": signal, "queue": queue}
    
    def get_state(self):
        locations = ["Biyagama", "Awissawella", "Malabe", "Angoda"]
        junction_state = {}
        
        for loc in locations:
            junction_state[loc] = self.get_current_signal(loc)
        
        avg_wait = self.total_wait / max(self.vehicles_passed, 1) if self.vehicles_passed > 0 else 0
        efficiency = round((self.vehicles_passed / max(len(self.vehicles), 1)) * 100, 1)
        
        return {
            "time": f"{int(self.current_time // 60):02d}:{int(self.current_time % 60):02d}",
            "junction": junction_state,
            "metrics": {
                "total_vehicles": len(self.vehicles),
                "passed": self.vehicles_passed,
                "total_wait": self.total_wait,
                "average_wait": round(avg_wait, 2),
                "efficiency": f"{efficiency}%",
                "predictions": self.predictions_made
            },
            "vehicle_list": [
                {
                    "id": v.id,
                    "origin": v.origin,
                    "status": v.status,
                    "distance": round(max(0, v.distance_to_junction), 1),
                    "speed": round(v.speed_kmh, 1),
                    "wait": v.wait_time,
                    "predicted_arrival": v.predicted_arrival if v.predicted_arrival else "calculating"
                }
                for v in self.vehicles[:80]
            ]
        }

simulator = None

@app.get("/")
def root():
    return {"system": "Kaduwela Junction", "version": "3.0", "status": "ready"}

@app.post("/api/simulation/start")
def start_simulation(request: StartRequest):
    global simulator
    simulator = KaduwelaSUMOSimulator()
    simulator.initialize(request.start_time, request.time_period)
    
    return {
        "status": "started",
        "total_vehicles": len(simulator.vehicles),
        "time_period": request.time_period
    }

@app.post("/api/simulation/step")
def step_simulation(request: StepRequest = None):
    if simulator is None:
        return {"error": "Start simulation first"}
    
    steps = 1
    if request:
        steps = request.steps
    
    for _ in range(steps):
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
    return {"status": "healthy", "version": "3.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
