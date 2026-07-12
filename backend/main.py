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
