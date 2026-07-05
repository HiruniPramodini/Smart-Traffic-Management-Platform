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

    def initialize(self, start_time_str, time_period):
        self.time_period = time_period
        self.current_time = 0
        self.vehicles = []
        self.total_wait = 0
        self.vehicles_passed = 0
        self.active_phase = "A"
        self.phase_elapsed = 0
        self.in_yellow = False

        volumes = TRAFFIC_VOLUMES.get(time_period, TRAFFIC_VOLUMES["off_peak"])
        for location, volume in volumes.items():
            num_vehicles = max(1, int(volume / 30))  # scaled down for a browsable sim
            for i in range(num_vehicles):
                self.vehicles.append(SUMOVehicle(f"{location[0]}{i:04d}", location))

        self._recompute_active_phase_duration()

    def _queue_and_wait_for(self, locations):
        vs = [v for v in self.vehicles if v.origin in locations]
        waiting = [v for v in vs if v.status == "at_junction"]
        queue = len(waiting)
        avg_wait = sum(v.wait_time for v in waiting) / max(queue, 1)
        return len(vs), queue, avg_wait

    def _recompute_active_phase_duration(self):
        """Ask the active phase's JunctionAgent for a green time based on
        real, current demand — this is the ML/agent-driven part."""
        locations = PHASES[self.active_phase]
        count, queue, avg_wait = self._queue_and_wait_for(locations)

        breakdown = {}
        for loc in locations:
            n, _, _ = self._queue_and_wait_for([loc])
            breakdown[loc] = n

        agent = self.agents[self.active_phase]
        agent.observe(count, avg_wait, queue, self.time_period, direction_breakdown=breakdown)
        result = agent.execute()
        self.phase_green_duration = result["green_time"]
        self.last_decision = result  # exposed to the API for transparency

    def step(self):
        self.current_time += 1
        self.phase_elapsed += 1

        # Phase / yellow-light state machine
        if self.in_yellow:
            if self.phase_elapsed >= YELLOW_SECONDS:
                self.active_phase = "B" if self.active_phase == "A" else "A"
                self.phase_elapsed = 0
                self.in_yellow = False
                self._recompute_active_phase_duration()
        else:
            if self.phase_elapsed >= self.phase_green_duration:
                # Learn from what actually happened this phase, then switch
                locations = PHASES[self.active_phase]
                _, _, avg_wait = self._queue_and_wait_for(locations)
                self.agents[self.active_phase].learn(avg_wait)

                self.in_yellow = True
                self.phase_elapsed = 0

        green_locations = set(PHASES[self.active_phase]) if not self.in_yellow else set()

        for v in self.vehicles:
            if v.status == "approaching":
                v.distance_to_junction -= v.speed_kmh / 3.6
                if v.distance_to_junction <= 0:
                    v.status = "at_junction"
            elif v.status == "at_junction":
                if v.origin in green_locations:
                    v.status = "passed"
                    self.vehicles_passed += 1
                else:
                    v.wait_time += 1
                    self.total_wait += 1

    def get_current_signal(self, location):
        phase = "A" if location in PHASES["A"] else "B"
        if self.in_yellow:
            color = "YELLOW" if phase == self.active_phase else "RED"
        else:
            color = "GREEN" if phase == self.active_phase else "RED"

        remaining = max(0, self.phase_green_duration - self.phase_elapsed) \
            if not self.in_yellow else max(0, YELLOW_SECONDS - self.phase_elapsed)

        _, queue, avg_wait = self._queue_and_wait_for([location])
        return {"signal": color, "queue": queue, "remaining": remaining, "avg_wait": round(avg_wait, 1)}

    def get_state(self):
        locations = ["Biyagama", "Awissawella", "Malabe", "Angoda"]
        junction_state = {loc: self.get_current_signal(loc) for loc in locations}

        avg_wait = self.total_wait / max(self.vehicles_passed, 1)
        efficiency = round((self.vehicles_passed / max(len(self.vehicles), 1)) * 100, 1)

        return {
            "time": f"{int(self.current_time // 60):02d}:{int(self.current_time % 60):02d}",
            "active_phase": self.active_phase,
            "in_yellow": self.in_yellow,
            "junction": junction_state,
            "agent_decision": getattr(self, "last_decision", None),
            "metrics": {
                "total_vehicles": len(self.vehicles),
                "passed": self.vehicles_passed,
                "total_wait": self.total_wait,
                "average_wait": round(avg_wait, 2),
                "efficiency": f"{efficiency}%",
            },
            "vehicle_list": [
                {
                    "id": v.id, "origin": v.origin, "status": v.status,
                    "distance": round(max(0, v.distance_to_junction), 1),
                    "speed": round(v.speed_kmh, 1), "wait": v.wait_time,
                }
                for v in self.vehicles[:80]
            ],
        }


simulator = None


@app.get("/")
def root():
    return {"system": "Kaduwela Junction (fixed)", "version": "4.0", "status": "ready"}


@app.post("/api/simulation/start")
def start_simulation(request: StartRequest):
    global simulator
    simulator = KaduwelaSimulator()
    simulator.initialize(request.start_time, request.time_period)
    return {"status": "started", "total_vehicles": len(simulator.vehicles), "time_period": request.time_period}


@app.post("/api/simulation/step")
def step_simulation(request: StepRequest = None):
    if simulator is None:
        return {"error": "Start simulation first"}
    steps = request.steps if request else 1
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
    return {"status": "healthy", "version": "4.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
