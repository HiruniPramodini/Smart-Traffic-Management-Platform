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

