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
