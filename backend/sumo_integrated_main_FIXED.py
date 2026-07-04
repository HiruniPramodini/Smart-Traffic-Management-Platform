"""
Kaduwela Junction backend — FIXED version.

Bugs fixed vs  original backend/sumo_integrated_main.py:

1. CONFLICTING GREEN LIGHTS (safety bug):
   The original checked each of the 4 directions independently against
   `current_time % 120`. Because Biyagama(52s)+Awissawella(48s)+Malabe(32s)
   +Angoda(28s) = 160s > the 120s cycle, and all four windows started at
   position 0, ALL FOUR approaches were GREEN simultaneously for the first
   28 seconds of every cycle. That's a real-world collision. Real junctions
   only let non-conflicting approaches go together.
   FIX: directions are grouped into two non-conflicting phases —
     Phase A: Biyagama <-> Malabe   (through-traffic on one road)
     Phase B: Awissawella <-> Angoda (through-traffic on the other road)
   Only one phase is GREEN at a time, with a 3s YELLOW clearance between.

2. STATIC TABLE INSTEAD OF YOUR ACTUAL AGENT/ML PIPELINE:
   The original hardcoded SIGNAL_TIMING dict ignored agents/junction_agent.py,
   agents/coordinator_agent_4b.py and models/kaduwela_congestion_model.pkl
   entirely. FIX: each phase now asks a JunctionAgent (backend/junction_agent.py)
   for a demand-responsive green time, which itself uses your trained
   congestion model (LOW/MEDIUM/HIGH -> 60/70/90s, capped by time period),
   exactly like docs/PROJECT_SUMMARY.md describes for Phase 3A-3B.

3. Per-direction queue length now actually drives the congestion prediction
   (previously queue was computed but never fed back into signal timing).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random

from backend.junction_agent import JunctionAgent

app = FastAPI(
    title="Kaduwela Junction - Corrected Signal Logic",
    description="Phase-paired signals driven by JunctionAgent + ML congestion model"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartRequest(BaseModel):
    start_time: str = "07:00"
    time_period: str = "morning_peak"


class StepRequest(BaseModel):
    steps: int = 1


# Two non-conflicting phases (matches the physical geometry: Biyagama and
# Malabe sit on the same straight road; Awissawella and Angoda sit on the
# other). Only one phase moves at a time.
PHASES = {
    "A": ["Biyagama", "Malabe"],
    "B": ["Awissawella", "Angoda"],
}

TRAFFIC_VOLUMES = {
    "morning_peak": {"Biyagama": 1800, "Awissawella": 1650, "Malabe": 980, "Angoda": 750},
    "evening_peak": {"Biyagama": 1200, "Awissawella": 1450, "Malabe": 880, "Angoda": 1100},
    "off_peak": {"Biyagama": 700, "Awissawella": 650, "Malabe": 400, "Angoda": 350},
    "night": {"Biyagama": 200, "Awissawella": 180, "Malabe": 120, "Angoda": 100},
}

YELLOW_SECONDS = 3


class SUMOVehicle:
    def __init__(self, vehicle_id, origin):
        self.id = vehicle_id
        self.origin = origin
        self.distance_to_junction = random.uniform(100, 2500)
        self.speed_kmh = random.uniform(30, 50)
        self.status = "approaching"
        self.wait_time = 0


class KaduwelaSimulator:
    def __init__(self):
        self.current_time = 0
        self.vehicles = []
        self.total_wait = 0
        self.vehicles_passed = 0
        self.time_period = "morning_peak"

        # One agent per phase group (so each phase gets its own ML-driven
        # congestion read + green-time decision)
        self.agents = {
            "A": JunctionAgent("Kaduwela-PhaseA", "models/kaduwela_congestion_model.pkl"),
            "B": JunctionAgent("Kaduwela-PhaseB", "models/kaduwela_congestion_model.pkl"),
        }

        self.active_phase = "A"
        self.phase_elapsed = 0
        self.phase_green_duration = 60
        self.in_yellow = False
