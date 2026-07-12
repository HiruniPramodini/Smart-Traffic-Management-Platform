"""
JunctionAgent — Phase 3A (XGBoost prediction) + Phase 3B (Q-learning) + Phase 4 (Multi-Agent coordination)

Each agent monitors a junction, predicts the future congestion level (15 minutes ahead)
using our trained XGBoost model, and coordinates with neighboring agents to maintain the
Green Wave or perform Platoon Gapping.
"""

import pickle
import random


class JunctionAgent:
    CONGESTION_NAMES = ["LOW", "MEDIUM", "HIGH"]

    # Base green times per predicted future congestion level
    BASE_GREEN = {0: 45, 1: 65, 2: 90}

    # Standard Sri Lanka weather mapping
    junction_map = {"Kaduwela": 0, "Malabe": 1, "Biyagama": 2, "Kotikawatta": 3, "Ranala": 4}
    dow_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    weather_map = {"clear": 0, "overcast": 1, "foggy": 2, "light_rain": 3, "heavy_rain": 4}

    CANDIDATE_GREEN_TIMES = [45, 60, 75, 90, 105, 120]
    FAIRNESS_MIN_GREEN = 30

    def __init__(self, road_name, model_path=None, epsilon=0.15):
        self.road_name = road_name  # The junction name (e.g. "Kaduwela", "Malabe", etc.)
        self.model = None
        self.epsilon = epsilon  # exploration rate for Q-learning

        if model_path:
            try:
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
            except Exception:
                self.model = None

        # Observations
        self.junction_name = road_name
        self.hour = 8
        self.day_of_week = "Monday"
        self.weather = "clear"
        self.vehicle_count = 0
        self.wait_time = 0
        self.queue_length = 0
        self.direction_demand = {}

        # ML Predictions
        self.congestion_level = 0  # 0=LOW, 1=MEDIUM, 2=HIGH

        # Q-table: {congestion_level: {green_time: reward}}
        self.q_table = {0: {}, 1: {}, 2: {}}

        # Multi-agent virtual messaging network states
        self.received_messages = []
        self.green_wave_active = False
        self.green_wave_direction = None
        self.green_wave_timer = 0

        self.gapping_active = False
        self.gapping_timer = 0
        self.agent_logs = []

    def observe(self, junction_name, hour, day_of_week, weather, total_vehicles, avg_wait, avg_queue, direction_breakdown=None):
        self.junction_name = junction_name
        self.hour = hour
        self.day_of_week = day_of_week
        self.weather = weather
        self.vehicle_count = total_vehicles
        self.wait_time = avg_wait
        self.queue_length = avg_queue

        if direction_breakdown:
            total = sum(direction_breakdown.values()) or 1
            self.direction_demand = {d: v / total for d, v in direction_breakdown.items()}
        else:
            self.direction_demand = {}

    # ---------------- Multi-Agent Coordination Messages ----------------

    def receive_message(self, message):
        """Receive coordination signals from neighbors."""
        self.received_messages.append(message)

    def process_messages(self, current_time_seconds):
        """Processes received messages and updates coordination states."""
        # Clear expired states
        if self.green_wave_active and current_time_seconds > self.green_wave_timer:
            self.green_wave_active = False
            self.green_wave_direction = None

        if self.gapping_active and current_time_seconds > self.gapping_timer:
            self.gapping_active = False

        new_messages = []
        for msg in self.received_messages:
            msg_type = msg.get("type")
            sender = msg.get("sender")

            if msg_type == "platoon_release":
                # We expect a platoon from this neighbor. Activate Green Wave for their direction.
                # ETA determines when green wave should be locked in.
                eta = msg.get("eta", 30)
                self.green_wave_active = True
                self.green_wave_direction = sender
                self.green_wave_timer = current_time_seconds + eta + 45  # active for next 45s window
                log_msg = f"[{self.junction_name}] Received PLATOON signal from {sender}. ETA: {eta}s. Priority lock active."
                self.agent_logs.append(log_msg)

            elif msg_type == "congestion_warning":
                # Downstream is heavily congested. Ask for Platoon Gapping (slow down releases).
                self.gapping_active = True
                self.gapping_timer = current_time_seconds + 90  # meter traffic for next 90s
                log_msg = f"[{self.junction_name}] Received CONGESTION warning from {sender}. Activating Platoon Gapping meter."
                self.agent_logs.append(log_msg)
            
            else:
                new_messages.append(msg)
        
        self.received_messages = new_messages

    # ---------------- Phase 3A: XGBoost Congestion prediction ----------------

    def predict_congestion(self):
        """Uses the trained XGBoost model to predict 15-minute look-ahead congestion."""
        if self.model is not None:
            try:
                j_enc = self.junction_map.get(self.junction_name, 0)
                dow_enc = self.dow_map.get(self.day_of_week, 0)
                w_enc = self.weather_map.get(self.weather, 0)

                features = [[
                    j_enc,
                    self.hour,
                    dow_enc,
                    w_enc,
                    self.vehicle_count,
                    self.wait_time,
                    self.queue_length
                ]]
                # Predict future congestion level
                self.congestion_level = int(self.model.predict(features)[0])
                return self.congestion_level
            except Exception:
                pass

        # Fallback to mathematical rules if model fails or isn't loaded
        if self.wait_time > 60 or self.queue_length > 50:
            self.congestion_level = 2
        elif (30 <= self.wait_time <= 60) or (25 <= self.queue_length <= 50):
            self.congestion_level = 1
        else:
            self.congestion_level = 0
        return self.congestion_level

    # ---------------- Phase 3A/4: Decide Green Time ----------------

    def decide_green_time(self):
        """Decides final green time based on predictions and coordination rules."""
        base = self.BASE_GREEN[self.congestion_level]

        # Multi-Agent overrides:
        if self.green_wave_active:
            # Downstream Platoon Priority: Extend green duration to flush incoming vehicles
            base += 20
            log_msg = f"[{self.junction_name}] GREEN WAVE extension active! Added 20s green time."
            if log_msg not in self.agent_logs[-3:]:
                self.agent_logs.append(log_msg)

        if self.gapping_active:
            # Downstream Bottleneck: Shorten green duration to prevent flooding the bottleneck
            base = max(self.FAIRNESS_MIN_GREEN, base - 15)
            log_msg = f"[{self.junction_name}] PLATOON GAPPING active. Metering flow (-15s green)."
            if log_msg not in self.agent_logs[-3:]:
                self.agent_logs.append(log_msg)

        # Cap timings between absolute engineering limits
        return max(30, min(120, base))

    # ---------------- Phase 3B: Q-learning ----------------

    def _best_known_action(self):
        table = self.q_table[self.congestion_level]
        if not table:
            return None
        return max(table, key=table.get)

    def decide_green_time_rl(self):
        """Epsilon-greedy selection with coordination limits."""
        best = self._best_known_action()

        if best is not None and random.random() > self.epsilon:
            green_time = best
        else:
            green_time = random.choice(self.CANDIDATE_GREEN_TIMES)

        # Still respect multi-agent constraints
        if self.green_wave_active:
            green_time = min(120, green_time + 20)
        if self.gapping_active:
            green_time = max(self.FAIRNESS_MIN_GREEN, green_time - 15)

        return green_time

    def learn(self, actual_wait_time):
        """Q-learning reinforcement loop."""
        green_time = self.decide_green_time()
        reward = -actual_wait_time
        table = self.q_table[self.congestion_level]
        if green_time not in table or reward > table[green_time]:
            table[green_time] = reward

    # ---------------- Direction splits ----------------

    def per_direction_green_time(self):
        """Splits green time between main road corridors and cross-roads."""
        total_green = self.decide_green_time()

        if not self.direction_demand:
            return {"main_road": total_green, "cross_road": total_green}

        # Divide main corridor direction vs cross directions
        main_demand = sum(v for k, v in self.direction_demand.items() if "kaduwela" in k or "colombo" in k or "main" in k)
        cross_demand = 1.0 - main_demand

        # Proportional split with minimums
        n = 2
        min_total = self.FAIRNESS_MIN_GREEN * n
        pool = max(total_green, min_total) - min_total

        main_split = round(self.FAIRNESS_MIN_GREEN + pool * main_demand, 1)
        cross_split = round(self.FAIRNESS_MIN_GREEN + pool * cross_demand, 1)

        return {
            "main_road": main_split,
            "cross_road": cross_split
        }

    # ---------------- Public entry points ----------------

    def execute(self):
        """Observation prediction and decision loop."""
        self.predict_congestion()
        return {
            "road_name": self.road_name,
            "congestion_level": self.congestion_level,
            "congestion_name": self.CONGESTION_NAMES[self.congestion_level],
            "green_time": self.decide_green_time(),
            "per_direction_green_time": self.per_direction_green_time(),
            "green_wave_active": self.green_wave_active,
            "gapping_active": self.gapping_active,
            "logs": self.agent_logs[-5:]  # return last few log lines
        }

