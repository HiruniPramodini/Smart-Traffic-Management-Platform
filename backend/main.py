from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random
import os

from backend.junction_agent import JunctionAgent

app = FastAPI(
    title="Smart Traffic Management API",
    description="Coordinated multi-agent traffic control with 15-minute look-ahead XGBoost forecasting",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Pydantic Request Models ----------------
class SimulationRequest(BaseModel):
    start_time: str
    time_period: str
    weather: Optional[str] = "clear"

class StepRequest(BaseModel):
    steps: int = 1

# ---------------- Simulation Entities ----------------
class Vehicle:
    def __init__(self, vehicle_id, vehicle_type, route, route_name):
        self.id = vehicle_id
        self.type = vehicle_type
        self.route = route  # list of link names
        self.route_name = route_name  # name descriptor
        self.current_route_index = 0
        self.position_meters = 0.0
        self.speed_mps = 13.8  # default ~50 km/h
        self.wait_time = 0.0
        self.status = "moving"  # moving | waiting | arrived
        self.color = random.choice(["#38bdf8", "#34d399", "#fb923c", "#f472b6", "#a78bfa"])

    def current_link(self):
        if self.current_route_index < len(self.route):
            return self.route[self.current_route_index]
        return None

    def next_junction(self):
        # Determine which junction this vehicle is heading towards on its route
        for i in range(self.current_route_index, len(self.route)):
            link = self.route[i]
            if link in ["Ranala", "Kaduwela", "Kotikawatta", "Malabe", "Biyagama"]:
                return link
        return None

class TrafficSimulator:
    LINK_LENGTHS = {
        # Outer sources
        "Ranala_source": 500,
        "Kotikawatta_source": 500,
        "Malabe_source": 500,
        "Biyagama_source": 500,
        "Cross_source_Ranala": 300,
        "Cross_source_Malabe": 300,
        "Cross_source_Biyagama": 300,
        "Cross_source_Kotikawatta": 300,
        
        # Inter-junction links
        "Ranala_to_Kaduwela": 5000,
        "Kaduwela_to_Ranala": 5000,
        "Kotikawatta_to_Kaduwela": 2000,
        "Kaduwela_to_Kotikawatta": 2000,
        "Biyagama_to_Kaduwela": 3000,
        "Kaduwela_to_Biyagama": 3000,
        "Malabe_to_Kaduwela": 3500,
        "Kaduwela_to_Malabe": 3500,
        
        # Output exits
        "Ranala_exit": 500,
        "Kotikawatta_exit": 500,
        "Malabe_exit": 500,
        "Biyagama_exit": 500,
        "Cross_exit": 300
    }

    ROUTES = {
        "ranala_to_kotikawatta": ["Ranala_source", "Ranala", "Ranala_to_Kaduwela", "Kaduwela", "Kaduwela_to_Kotikawatta", "Kotikawatta", "Kotikawatta_exit"],
        "kotikawatta_to_ranala": ["Kotikawatta_source", "Kotikawatta", "Kotikawatta_to_Kaduwela", "Kaduwela", "Kaduwela_to_Ranala", "Ranala", "Ranala_exit"],
        "malabe_to_biyagama": ["Malabe_source", "Malabe", "Malabe_to_Kaduwela", "Kaduwela", "Kaduwela_to_Biyagama", "Biyagama", "Biyagama_exit"],
        "biyagama_to_malabe": ["Biyagama_source", "Biyagama", "Biyagama_to_Kaduwela", "Kaduwela", "Kaduwela_to_Malabe", "Malabe", "Malabe_exit"],
        
        # Local background cross-street routes
        "ranala_local": ["Cross_source_Ranala", "Ranala", "Cross_exit"],
        "malabe_local": ["Cross_source_Malabe", "Malabe", "Cross_exit"],
        "biyagama_local": ["Cross_source_Biyagama", "Biyagama", "Cross_exit"],
        "kotikawatta_local": ["Cross_source_Kotikawatta", "Kotikawatta", "Cross_exit"]
    }

    WEATHER_SPEED_SCALE = {
        "clear": 1.0,
        "overcast": 0.95,
        "foggy": 0.78,
        "light_rain": 0.85,
        "heavy_rain": 0.65
    }

    def __init__(self, start_time_str, time_period, weather="clear"):
        self.current_time = datetime.strptime(start_time_str, "%H:%M")
        self.time_period = time_period
        self.weather = weather
        self.vehicles: List[Vehicle] = []
        self.elapsed_seconds = 0
        self.total_wait_time = 0.0
        self.vehicles_spawned = 0
        self.vehicles_passed = 0
        # Agents setup
        model_path = "models/kaduwela_congestion_model.pkl"
        if not os.path.exists(model_path):
            print(f"XGBoost model pickle '{model_path}' not found.")
            print("Auto-training look-ahead congestion model on-the-fly...")
            try:
                import sys
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                from models.train_ml_model import train_model
                train_model()
            except Exception as e:
                print(f"Failed to auto-train model: {e}. Running in mathematical fallback mode.")

        self.agents = {
            "Kaduwela": JunctionAgent("Kaduwela", model_path),
            "Malabe": JunctionAgent("Malabe", model_path),
            "Biyagama": JunctionAgent("Biyagama", model_path),
            "Kotikawatta": JunctionAgent("Kotikawatta", model_path),
            "Ranala": JunctionAgent("Ranala", model_path)
        }

        
        # Junction traffic lights state machine
        self.junction_states = {}
        for jname in ["Ranala", "Kaduwela", "Kotikawatta", "Malabe", "Biyagama"]:
            self.junction_states[jname] = {
                "active_phase": "main_road",  # main_road | cross_road
                "in_yellow": False,
                "phase_elapsed": 0.0,
                "phase_duration": 45.0,  # dynamic green duration
                "agent_decision": {
                    "congestion_name": "LOW",
                    "green_time": 45,
                    "green_wave_active": False,
                    "gapping_active": False,
                    "logs": []
                }
            }
        
        # Multi-agent shared logs
        self.coordination_logs = []

    def spawn_vehicles(self):
        # Vehicle spawn frequency scales based on time period and weather
        spawn_multipliers = {
            "morning_peak": 1.8,
            "evening_peak": 1.6,
            "off_peak": 0.8,
            "night": 0.25
        }
        
        base_rate = spawn_multipliers.get(self.time_period, 1.0)
        # Weather decreases spawning rate slightly due to reduced departures
        weather_scale = 0.75 if self.weather in ["heavy_rain", "foggy"] else 1.0
        
        spawn_chance = 0.35 * base_rate * weather_scale
        
        if random.random() < spawn_chance:
            # Select route
            route_key = random.choices(
                list(self.ROUTES.keys()),
                weights=[2.5, 2.5, 2.0, 2.0, 0.8, 0.8, 0.8, 0.8],  # primary corridors are busiest
                k=1
            )[0]
            
            self.vehicles_spawned += 1
            v_type = random.choices(
                ["car", "bus", "truck", "tuk_tuk", "motorcycle"],
                weights=[0.55, 0.08, 0.04, 0.12, 0.21],
                k=1
            )[0]
            
            vehicle_id = f"{v_type.upper()}_{self.vehicles_spawned:04d}"
            route = self.ROUTES[route_key]
            
            v = Vehicle(vehicle_id, v_type, route, route_key)
            # Weather scale initial speed
            w_scale = self.WEATHER_SPEED_SCALE.get(self.weather, 1.0)
            v.speed_mps = random.uniform(11.0, 15.0) * w_scale
            
            self.vehicles.append(v)

    def recompute_agent_decision(self, jname):
        # Gather metrics for this junction
        j_vehicles = [v for v in self.vehicles if v.status != "arrived" and v.next_junction() == jname]
        total_vehicles = len(j_vehicles)
        waiting = [v for v in j_vehicles if v.status == "waiting"]
        avg_wait = sum(v.wait_time for v in waiting) / max(len(waiting), 1)
        avg_queue = len(waiting)
        
        # Observe
        agent = self.agents[jname]
        hour = self.current_time.hour
        dow_name = self.current_time.strftime("%A")
        
        # direction breakdown
        direction_breakdown = {"main_road": 0, "cross_road": 0}
        for v in j_vehicles:
            is_main = any(x in v.route_name for x in ["ranala", "kotikawatta", "colombo", "main"])
            if is_main:
                direction_breakdown["main_road"] += 1
            else:
                direction_breakdown["cross_road"] += 1
                
        agent.observe(
            junction_name=jname,
            hour=hour,
            day_of_week=dow_name,
            weather=self.weather,
            total_vehicles=total_vehicles,
            avg_wait=avg_wait,
            avg_queue=avg_queue,
            direction_breakdown=direction_breakdown
        )
        
        # Update messages
        agent.process_messages(self.elapsed_seconds)
        
        # Decide green wave and speeds
        res = agent.execute()
        
        # Update traffic light durations
        j = self.junction_states[jname]
        splits = res["per_direction_green_time"]
        if j["active_phase"] == "main_road":
            j["phase_duration"] = splits.get("main_road", 45)
        else:
            j["phase_duration"] = splits.get("cross_road", 45)
            
        j["agent_decision"] = res

        # Agent messaging logs
        for log in res["logs"]:
            if log not in self.coordination_logs[-8:]:
                self.coordination_logs.append(log)

    def step_simulation(self, dt=1.0):
        self.elapsed_seconds += int(dt)
        self.current_time += timedelta(seconds=dt)
        
        # 1. Spawn new vehicles
        self.spawn_vehicles()
        
        # 2. Update traffic light phase machine
        for jname in ["Ranala", "Kaduwela", "Kotikawatta", "Malabe", "Biyagama"]:
            j = self.junction_states[jname]
            j["phase_elapsed"] += dt
            
            if j["in_yellow"]:
                if j["phase_elapsed"] >= 3.0:  # Yellow light = 3s
                    j["in_yellow"] = False
                    j["phase_elapsed"] = 0
                    j["active_phase"] = "cross_road" if j["active_phase"] == "main_road" else "main_road"
                    self.recompute_agent_decision(jname)
            else:
                if j["phase_elapsed"] >= j["phase_duration"]:
                    j["in_yellow"] = True
                    j["phase_elapsed"] = 0
                    
                    # Release platoon message upstream/downstream when main road turns green
                    if jname == "Kaduwela" and j["active_phase"] == "main_road":
                        # Send Green Wave release signal downstream
                        self.agents["Kotikawatta"].receive_message({
                            "type": "platoon_release", "sender": "Kaduwela", "eta": 140
                        })
                        self.agents["Ranala"].receive_message({
                            "type": "platoon_release", "sender": "Kaduwela", "eta": 350
                        })
                    elif jname == "Kaduwela" and j["active_phase"] == "cross_road":
                        self.agents["Malabe"].receive_message({
                            "type": "platoon_release", "sender": "Kaduwela", "eta": 250
                        })
                        self.agents["Biyagama"].receive_message({
                            "type": "platoon_release", "sender": "Kaduwela", "eta": 210
                        })

                    # If this junction has high queues, warn upstream nodes (Platoon Gapping request)
                    waiting_here = len([v for v in self.vehicles if v.status != "arrived" and v.next_junction() == jname and v.status == "waiting"])
                    if waiting_here > 15:
                        if jname in ["Kotikawatta", "Ranala"]:
                            self.agents["Kaduwela"].receive_message({
                                "type": "congestion_warning", "sender": jname
                            })
                        elif jname in ["Malabe", "Biyagama"]:
                            self.agents["Kaduwela"].receive_message({
                                "type": "congestion_warning", "sender": jname
                            })

        # 3. Update vehicle movements
        for v in self.vehicles:
            if v.status == "arrived":
                continue
                
            current_link = v.current_link()
            if not current_link:
                v.status = "arrived"
                self.vehicles_passed += 1
                continue
                
            # If vehicle is on a link, move it forward
            if current_link not in ["Ranala", "Kaduwela", "Kotikawatta", "Malabe", "Biyagama"]:
                link_len = self.LINK_LENGTHS.get(current_link, 500)
                
                # Check if there is another vehicle ahead of it (to avoid collision)
                veh_ahead = [x for x in self.vehicles if x.status != "arrived" and x.id != v.id and x.current_link() == current_link and x.position_meters > v.position_meters]
                lead_pos = min([x.position_meters for x in veh_ahead]) if veh_ahead else link_len
                
                if lead_pos - v.position_meters < 15.0:  # keeping minimum gap of 15m
                    v.speed_mps = max(0, v.speed_mps - 4.0 * dt)
                else:
                    # accelerate to speed limit
                    w_scale = self.WEATHER_SPEED_SCALE.get(self.weather, 1.0)
                    target_speed = (16.0 if "to_Kaduwela" in current_link else 13.8) * w_scale
                    v.speed_mps = min(target_speed, v.speed_mps + 2.0 * dt)
                    
                v.position_meters += v.speed_mps * dt
                v.status = "moving"
                
                if v.position_meters >= link_len:
                    # move to next index (which is a junction)
                    v.position_meters = link_len
                    v.current_route_index += 1
                    
            # Vehicle is at a junction waiting or crossing
            else:
                jname = current_link
                j = self.junction_states[jname]
                
                # Check traffic light signal state for this vehicle's direction
                is_main_route = any(x in v.route_name for x in ["ranala", "kotikawatta", "colombo", "main"])
                light_green = False
                
                if j["active_phase"] == "main_road" and not j["in_yellow"] and is_main_route:
                    light_green = True
                elif j["active_phase"] == "cross_road" and not j["in_yellow"] and not is_main_route:
                    light_green = True
                
                if light_green:
                    v.current_route_index += 1
                    v.position_meters = 0.0
                    v.status = "moving"
                else:
                    v.status = "waiting"
                    v.wait_time += dt
                    self.total_wait_time += dt

        # Remove arrived vehicles
        self.vehicles = [v for v in self.vehicles if v.status != "arrived"]

    def get_state(self):
        # Format junction state
        j_data = {}
        for jname in ["Ranala", "Kaduwela", "Kotikawatta", "Malabe", "Biyagama"]:
            state = self.junction_states[jname]
            
            # Map signal colors per direction (Main and Cross)
            main_color = "RED"
            cross_color = "RED"
            if state["active_phase"] == "main_road":
                main_color = "YELLOW" if state["in_yellow"] else "GREEN"
            else:
                cross_color = "YELLOW" if state["in_yellow"] else "GREEN"
                
            j_data[jname] = {
                "active_phase": state["active_phase"],
                "in_yellow": state["in_yellow"],
                "main_color": main_color,
                "cross_color": cross_color,
                "remaining": round(max(0.0, (3.0 if state["in_yellow"] else state["phase_duration"]) - state["phase_elapsed"])),
                "congestion_level": state["agent_decision"]["congestion_level"],
                "congestion_name": state["agent_decision"]["congestion_name"],
                "green_wave_active": state["agent_decision"]["green_wave_active"],
                "gapping_active": state["agent_decision"]["gapping_active"]
            }

        avg_wait = self.total_wait_time / max(self.vehicles_passed, 1)
        
        return {
            "time": self.current_time.strftime("%H:%M:%S"),
            "elapsed_seconds": self.elapsed_seconds,
            "weather": self.weather,
            "junctions": j_data,
            "coordination_logs": self.coordination_logs[-6:],
            "metrics": {
                "total_vehicles": len(self.vehicles),
                "spawned": self.vehicles_spawned,
                "passed": self.vehicles_passed,
                "total_wait": round(self.total_wait_time),
                "average_wait": round(avg_wait, 1)
            },
            "vehicles": [
                {
                    "id": v.id,
                    "type": v.type,
                    "color": v.color,
                    "link": v.current_link(),
                    "progress_percent": round((v.position_meters / self.LINK_LENGTHS.get(v.current_link(), 500)) * 100) if v.current_link() and v.current_link() not in ["Ranala", "Kaduwela", "Kotikawatta", "Malabe", "Biyagama"] else 0,
                    "status": v.status,
                    "route": v.route_name
                }
                for v in self.vehicles[:150]  # Return up to 150 vehicles
            ]
        }

simulator = None

@app.get("/")
def read_root():
    return {"message": "Smart Traffic Management Coordinated 5-Junction API", "status": "running"}

@app.post("/api/simulation/start")
def start_simulation(request: SimulationRequest):
    global simulator
    simulator = TrafficSimulator(request.start_time, request.time_period, request.weather)
    # Perform an initial decision for all agents
    for jname in ["Ranala", "Kaduwela", "Kotikawatta", "Malabe", "Biyagama"]:
        simulator.recompute_agent_decision(jname)
    return {"status": "started", "start_time": request.start_time, "time_period": request.time_period, "weather": request.weather}

@app.post("/api/simulation/step")
def step_simulation(request: StepRequest = None):
    if simulator is None:
        return {"error": "Simulation not started"}
    steps = request.steps if request else 1
    # step second-by-second
    for _ in range(steps):
        simulator.step_simulation(1.0)
    return simulator.get_state()

@app.get("/api/simulation/state")
def get_simulation_state():
    if simulator is None:
        return {"error": "Simulation not started"}
    return simulator.get_state()

@app.post("/api/simulation/reset")
def reset_simulation():
    global simulator
    simulator = None
    return {"status": "reset"}

@app.get("/api/metrics")
def get_metrics():
    if simulator is None:
        return {"error": "Simulation not started"}
    state = simulator.get_state()
    return state["metrics"]

@app.get("/api/routes")
def get_routes():
    return {
        "corridors": [
            "Ranala ── Kaduwela ── Kotikawatta (West-to-East)",
            "Kotikawatta ── Kaduwela ── Ranala (East-to-West)",
            "Malabe ── Kaduwela ── Biyagama (North-to-South)",
            "Biyagama ── Kaduwela ── Malabe (South-to-North)"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)