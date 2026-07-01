from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime, timedelta

app = FastAPI(
    title="Smart Traffic Management API",
    description="Adaptive traffic signal control for Malabe Junction",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VehiclePosition(BaseModel):
    vehicle_id: str
    route: str
    current_junction: str
    position_percent: float
    arrival_time: str
    status: str

class SignalState(BaseModel):
    junction_name: str
    direction: str
    color: str
    remaining_seconds: int
    priority: int

class SimulationRequest(BaseModel):
    start_time: str
    duration_minutes: int
    time_period: str

class StepRequest(BaseModel):
    steps: int = 1

class TrafficSimulator:
    def __init__(self):
        self.vehicles = []
        self.current_time = None
        self.signal_schedule = {}
        self.total_wait_time = 0
        self.vehicles_passed = 0
        
    def initialize_simulation(self, start_time_str, time_period):
        self.current_time = datetime.strptime(start_time_str, "%H:%M")
        self.time_period = time_period
        
        if time_period == "morning_peak":
            self.create_morning_vehicles()
        else:
            self.create_evening_vehicles()
        
        self.generate_signal_schedule(start_time_str, time_period)
        
    def create_morning_vehicles(self):
        self.vehicles = [
            {"vehicle_id": "CAR_001", "type": "car", "route": "Biyagama-Colombo", "origin": "Biyagama", "destination": "Colombo", "departure_time": datetime.strptime("07:00", "%H:%M"), "current_junction": "Biyagama", "journey": ["Biyagama", "Kaduwela", "Malabe", "Battaramulla", "Colombo"], "distances": [0, 3, 5, 9, 14], "status": "waiting", "total_wait_time": 0},
            {"vehicle_id": "CAR_002", "type": "car", "route": "Awissawella-Colombo", "origin": "Awissawella", "destination": "Colombo", "departure_time": datetime.strptime("07:00", "%H:%M"), "current_junction": "Awissawella", "journey": ["Awissawella", "Kaduwela", "Angoda", "Wellampitiya", "Colombo"], "distances": [0, 10, 13, 19, 23], "status": "waiting", "total_wait_time": 0},
            {"vehicle_id": "TRUCK_001", "type": "truck", "route": "Biyagama-Colombo", "origin": "Biyagama", "destination": "Colombo", "departure_time": datetime.strptime("07:02", "%H:%M"), "current_junction": "Biyagama", "journey": ["Biyagama", "Kaduwela", "Malabe", "Battaramulla", "Colombo"], "distances": [0, 3, 5, 9, 14], "status": "waiting", "total_wait_time": 0},
            {"vehicle_id": "BUS_001", "type": "bus", "route": "Awissawella-Colombo", "origin": "Awissawella", "destination": "Colombo", "departure_time": datetime.strptime("07:01", "%H:%M"), "current_junction": "Awissawella", "journey": ["Awissawella", "Kaduwela", "Angoda", "Wellampitiya", "Colombo"], "distances": [0, 10, 13, 19, 23], "status": "waiting", "total_wait_time": 0}
        ]
    
    def create_evening_vehicles(self):
        self.vehicles = [
            {"vehicle_id": "CAR_003", "type": "car", "route": "Colombo-Biyagama", "origin": "Colombo", "destination": "Biyagama", "departure_time": datetime.strptime("17:00", "%H:%M"), "current_junction": "Colombo", "journey": ["Colombo", "Battaramulla", "Malabe", "Kaduwela", "Biyagama"], "distances": [0, 5, 9, 11, 14], "status": "waiting", "total_wait_time": 0},
            {"vehicle_id": "CAR_004", "type": "car", "route": "Colombo-Awissawella", "origin": "Colombo", "destination": "Awissawella", "departure_time": datetime.strptime("17:00", "%H:%M"), "current_junction": "Colombo", "journey": ["Colombo", "Wellampitiya", "Angoda", "Kaduwela", "Awissawella"], "distances": [0, 4, 10, 13, 23], "status": "waiting", "total_wait_time": 0}
        ]
    
    def generate_signal_schedule(self, start_time_str, time_period):
        if time_period == "morning_peak":
            self.signal_schedule = {
                "Kaduwela": [
                    {"arrival_time": datetime.strptime("07:03:36", "%H:%M:%S"), "green_start": datetime.strptime("07:03:36", "%H:%M:%S"), "green_duration": 60, "direction": "from_Biyagama"},
                    {"arrival_time": datetime.strptime("07:12:00", "%H:%M:%S"), "green_start": datetime.strptime("07:12:00", "%H:%M:%S"), "green_duration": 60, "direction": "from_Awissawella"}
                ]
            }
        else:
            self.signal_schedule = {
                "Kaduwela": [
                    {"arrival_time": datetime.strptime("17:13:12", "%H:%M:%S"), "green_start": datetime.strptime("17:13:12", "%H:%M:%S"), "green_duration": 60, "direction": "from_Biyagama"},
                    {"arrival_time": datetime.strptime("17:15:36", "%H:%M:%S"), "green_start": datetime.strptime("17:15:36", "%H:%M:%S"), "green_duration": 60, "direction": "from_Awissawella"}
                ]
            }
    
    def get_signal_state_at_time(self, junction_name, current_time):
        if junction_name not in self.signal_schedule:
            return {"color": "RED", "remaining_seconds": 30, "priority": 0}
        
        signals = self.signal_schedule[junction_name]
        
        for signal in signals:
            green_start = signal["green_start"]
            green_end = green_start + timedelta(seconds=signal["green_duration"])
            
            if green_start <= current_time < green_end:
                remaining = (green_end - current_time).total_seconds()
                return {"color": "GREEN", "remaining_seconds": int(remaining), "priority": 1}
        
        return {"color": "RED", "remaining_seconds": 30, "priority": 0}
    
    def step_simulation(self, time_delta_seconds=1):
        self.current_time += timedelta(seconds=time_delta_seconds)
        for vehicle in self.vehicles:
            self.update_vehicle_position(vehicle)
    
    def update_vehicle_position(self, vehicle):
        departure = vehicle["departure_time"]
        elapsed_seconds = (self.current_time - departure).total_seconds()
        
        if elapsed_seconds < 0:
            vehicle["status"] = "waiting"
            return
        
        total_distance = vehicle["distances"][-1]
        current_distance = (total_distance / 3600) * 50 * elapsed_seconds
        
        for i in range(len(vehicle["journey"]) - 1):
            next_junction_dist = vehicle["distances"][i + 1]
            
            if current_distance >= next_junction_dist:
                vehicle["current_junction"] = vehicle["journey"][i + 1]
            else:
                vehicle["current_junction"] = vehicle["journey"][i]
                signal_state = self.get_signal_state_at_time(vehicle["current_junction"], self.current_time)
                
                if signal_state["color"] != "GREEN":
                    vehicle["status"] = "waiting"
                    vehicle["total_wait_time"] += 1
                    self.total_wait_time += 1
                else:
                    vehicle["status"] = "moving"
                break
        
        if vehicle["current_junction"] == vehicle["destination"]:
            vehicle["status"] = "arrived"
            self.vehicles_passed += 1
    
    def get_current_state(self):
        vehicle_positions = []
        for vehicle in self.vehicles:
            vehicle_positions.append({
                "vehicle_id": vehicle["vehicle_id"],
                "route": vehicle["route"],
                "current_junction": vehicle["current_junction"],
                "position_percent": self.calculate_position_percent(vehicle),
                "arrival_time": vehicle["departure_time"].strftime("%H:%M:%S"),
                "status": vehicle["status"]
            })
        
        signal_states = []
        directions = ["from_Biyagama", "from_Awissawella", "from_Malabe", "from_Battaramulla"]
        
        for direction in directions:
            signal_state = self.get_signal_state_at_time("Kaduwela", self.current_time)
            signal_states.append({
                "junction_name": "Kaduwela",
                "direction": direction,
                "color": signal_state["color"],
                "remaining_seconds": signal_state["remaining_seconds"],
                "priority": signal_state["priority"]
            })
        
        metrics = {
            "total_vehicles": len(self.vehicles),
            "vehicles_arrived": self.vehicles_passed,
            "average_wait_time": self.total_wait_time / max(len(self.vehicles), 1),
            "total_wait_time": self.total_wait_time,
            "current_time": self.current_time.strftime("%H:%M:%S")
        }
        
        return {
            "time": self.current_time.strftime("%H:%M:%S"),
            "vehicles": vehicle_positions,
            "signals": signal_states,
            "metrics": metrics
        }
    
    def calculate_position_percent(self, vehicle):
        departure = vehicle["departure_time"]
        elapsed_seconds = (self.current_time - departure).total_seconds()
        
        if elapsed_seconds < 0:
            return 0
        
        total_distance = vehicle["distances"][-1]
        current_distance = (total_distance / 3600) * 50 * elapsed_seconds
        
        return min(100, (current_distance / total_distance) * 100)

simulator = None

@app.get("/")
def read_root():
    return {"message": "Smart Traffic Management API", "version": "1.0.0", "status": "running"}

@app.post("/api/simulation/start")
def start_simulation(request: SimulationRequest):
    global simulator
    simulator = TrafficSimulator()
    simulator.initialize_simulation(request.start_time, request.time_period)
    return {"status": "started", "start_time": request.start_time, "time_period": request.time_period, "vehicles_count": len(simulator.vehicles)}

@app.post("/api/simulation/step")
def step_simulation(request: StepRequest = None):
    if simulator is None:
        return {"error": "Simulation not started"}
    steps = request.steps if request else 1
    for _ in range(steps):
        simulator.step_simulation(1)
    return simulator.get_current_state()

@app.get("/api/simulation/state")
def get_simulation_state():
    if simulator is None:
        return {"error": "Simulation not started"}
    return simulator.get_current_state()

@app.post("/api/simulation/reset")
def reset_simulation():
    global simulator
    simulator = None
    return {"status": "reset"}

@app.get("/api/signals/kaduwela")
def get_kaduwela_signals():
    if simulator is None:
        return {"error": "Simulation not started"}
    signals = []
    for direction in ["from_Biyagama", "from_Awissawella", "from_Malabe", "from_Battaramulla"]:
        signal_state = simulator.get_signal_state_at_time("Kaduwela", simulator.current_time)
        signals.append({"direction": direction, "color": signal_state["color"], "remaining_seconds": signal_state["remaining_seconds"]})
    return {"junction": "Kaduwela", "time": simulator.current_time.strftime("%H:%M:%S"), "signals": signals}

@app.get("/api/metrics")
def get_metrics():
    if simulator is None:
        return {"error": "Simulation not started"}
    return {"current_time": simulator.current_time.strftime("%H:%M:%S"), "total_vehicles": len(simulator.vehicles), "vehicles_arrived": simulator.vehicles_passed, "average_wait_time": round(simulator.total_wait_time / max(len(simulator.vehicles), 1), 2), "total_wait_time": simulator.total_wait_time}

@app.get("/api/routes")
def get_routes():
    return {"morning_peak": ["Biyagama → Kaduwela → Malabe → Battaramulla → Colombo", "Awissawella → Kaduwela → Angoda → Wellampitiya → Colombo"], "evening_peak": ["Colombo → Battaramulla → Malabe → Kaduwela → Biyagama", "Colombo → Wellampitiya → Angoda → Kaduwela → Awissawella"]}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Smart Traffic Management API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)