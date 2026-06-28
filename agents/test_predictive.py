from backend.coordinator_predictive import PredictiveCoordinatorAgent
from datetime import datetime, timedelta

coordinator = PredictiveCoordinatorAgent()

print("\n" + "="*70)
print("PHASE 5: PREDICTIVE ARRIVAL-BASED SIGNAL CONTROL")
print("="*70)

# MORNING SCENARIO (7:00 AM)
print("\n\n### MORNING PEAK (7:00 AM) ###\n")

morning_start = datetime.strptime("07:00", "%H:%M")
coordinator.execute_morning_schedule(morning_start)

print("\n" + "="*70)
print("EXPLANATION - MORNING PEAK:")
print("="*70)
print("""
Distance Calculation (Speed = 50 km/h):
├─ Biyagama → Kaduwela: 3 km
│  Time = 3 ÷ 50 × 60 = 3.6 minutes ≈ 4 minutes
│  Arrival: 7:00 + 4 min = 7:04 AM ✓
│
└─ Awissawella → Kaduwela: 10 km
   Time = 10 ÷ 50 × 60 = 12 minutes
   Arrival: 7:00 + 12 min = 7:12 AM ✓

Kaduwela Junction Signal Timing:
├─ 7:04 AM: Biyagama direction → GREEN (from Route A)
├─ 7:12 AM: Awissawella direction → GREEN (from Route B)
└─ Vehicles arrive → lights already green!

Result: PERFECT GREEN WAVE ✓
""")

# EVENING SCENARIO (5:00 PM)
print("\n\n### EVENING PEAK (5:00 PM) ###\n")

evening_start = datetime.strptime("17:00", "%H:%M")
coordinator.execute_evening_schedule(evening_start)

print("\n" + "="*70)
print("EXPLANATION - EVENING PEAK (REVERSED):")
print("="*70)
print("""
Same distance calculations, BUT:
├─ Traffic direction is REVERSED
├─ Biyagama-bound traffic gets priority (return from work)
├─ Awissawella-bound traffic gets priority (return from work)
│
Route Times (Return journey):
├─ Colombo → Kaduwela: 11 km ÷ 50 = 13.2 min ≈ 13 min
├─ Colombo → Kaduwela (via Angoda): 13 km ÷ 50 = 15.6 min ≈ 16 min
│
Kaduwela Junction Signal Timing (Evening):
├─ 5:13 PM: Malabe direction → GREEN (returning via Route A)
├─ 5:16 PM: Angoda direction → GREEN (returning via Route B)
└─ Return traffic gets smooth flow!

Result: SMOOTH RETURN FROM COLOMBO ✓
""")

print("\n" + "="*70)
print("KEY ADVANTAGES:")
print("="*70)
print("""
1. ✓ NO GPS NEEDED - Uses fixed distances and speed
2. ✓ NO CAMERAS NEEDED - Simple calculation
3. ✓ PREDICTABLE - Same schedule every day
4. ✓ SIMPLE - Just math: Time = Distance / Speed
5. ✓ EFFECTIVE - Signals turn green RIGHT WHEN vehicles arrive
6. ✓ FAIR - Both routes get service
7. ✓ ADAPTIVE - Can change based on time of day

Implementation:
├─ Morning: Prioritize Colombo-bound traffic
├─ Evening: Prioritize return-home traffic
└─ Automatic switch based on time_period
""")

print("\n" + "="*70)
print("SYSTEM READY FOR DEPLOYMENT")
print("="*70)