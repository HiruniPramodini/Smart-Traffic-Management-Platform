import pickle

class JunctionAgent:
    def __init__(self, road_name, model_path):
        # Load ML model
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)

        self.road_name = road_name
        
        # Q-Learning table (Phase 3B)
        self.q_table = {}
        self.learning_enabled = True
        self.last_green_time = None

        # Store current state
        self.vehicle_count = None
        self.wait_time = None
        self.queue_length = None
        self.time_period = None
        self.congestion_level = None

    def observe(self, vehicle_count, wait_time, queue_length, time_period):
        # Store the current state
        self.vehicle_count = vehicle_count
        self.wait_time = wait_time
        self.queue_length = queue_length
        self.time_period = time_period

    def predict_congestion(self):
        # Encode time period
        time_mapping = {
            'morning_peak': 0,
            'afternoon_peak': 1,
            'evening_peak': 2,
            'off_peak': 3,
            'night': 4
        }

        time_period_encoded = time_mapping.get(self.time_period, 0)

        # Prepare features
        features = [
            time_period_encoded,
            self.vehicle_count,
            self.wait_time,
            self.queue_length
        ]

        # Predict congestion
        self.congestion_level = self.model.predict([features])[0]

    def rule_based_decision(self):
        # Phase 3A: Rule-based logic (fallback)
        if self.congestion_level == 0:   # LOW
            base_time = 60
        elif self.congestion_level == 1: # MEDIUM
            base_time = 70
        else:                            # HIGH
            base_time = 90
        
        # Adjust based on time_period (Option Y)
        if self.time_period in ["morning_peak", "evening_peak"]:
            return base_time
        elif self.time_period == "afternoon_peak":
            return min(base_time, 85)
        elif self.time_period == "off_peak":
            return min(base_time, 80)
        elif self.time_period == "night":
            return min(base_time, 75)
        
        return base_time

    def decide_green_time(self):
        # Phase 3B: Check Q-Table first (learned values)
        if self.learning_enabled and self.congestion_level in self.q_table:
            # Use the best learned action
            learned_time = max(self.q_table[self.congestion_level], 
                              key=self.q_table[self.congestion_level].get)
            return learned_time
        
        # Phase 3A: Fall back to rule-based logic
        return self.rule_based_decision()

    def learn(self, actual_wait_time):
        # Update Q-Table based on actual results
        if self.congestion_level not in self.q_table:
            self.q_table[self.congestion_level] = {}
        
        # Reward = negative wait time (lower wait = higher reward)
        reward = -actual_wait_time
        
        # Store: for this congestion level, last_green_time gave this reward
        self.q_table[self.congestion_level][self.last_green_time] = reward
        
        print(f"[{self.road_name}] Learned: Congestion {self.congestion_level}, {self.last_green_time}s green → reward {reward}")

    def execute(self):
        # Step 1: Predict congestion
        self.predict_congestion()

        # Step 2: Decide green time
        green_time = self.decide_green_time()
        self.last_green_time = green_time  # Track for learning
        
        # Step 3: Return result
        return green_time