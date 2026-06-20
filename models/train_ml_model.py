import pandas as pd 
df = pd.read_csv("data/processed/malabe_traffic_data.csv")

print(df.head(5))
print(df.shape)
print(df.columns)

def get_congestion_level(waiting_time, queue_length):
    if (waiting_time > 60) or (queue_length > 50):
        return "HIGH"
    elif (waiting_time >= 30 and waiting_time <= 60) or (queue_length >= 25 and queue_length <= 50):
        return "MEDIUM"
    else:
        return "LOW"
    
#congestion COLUMNN

df['kaduwela_congestion'] = df.apply(
    lambda row: get_congestion_level(row['kaduwela_wait_sec'], row['kaduwela_queue']), #apply call to all rows 
    axis=1
)
df['athurugiriya_congestion'] = df.apply(
    lambda row: get_congestion_level(row['athurugiriya_wait_sec'], row['athurugiriya_queue']), #apply call to all rows 
    axis=1
)
df['battaramulla_congestion'] = df.apply(
    lambda row: get_congestion_level(row['battaramulla_wait_sec'], row['battaramulla_queue']), #apply call to all rows 
    axis=1
)

print(df[['kaduwela_wait_sec', 'kaduwela_queue', 'kaduwela_congestion']].head(10))

# Encode time_period (ONCE, not per road)
df['time_period_encoded'] = df['time_period'].map({
    'morning_peak': 0,
    'afternoon_peak': 1,
    'evening_peak': 2,
    'off_peak': 3,
    'night': 4
})

# Encode each road's congestion level
df['kaduwela_congestion_encoded'] = df['kaduwela_congestion'].map({
    'LOW': 0,
    'MEDIUM': 1,
    'HIGH': 2
})

df['athurugiriya_congestion_encoded'] = df['athurugiriya_congestion'].map({
    'LOW': 0,
    'MEDIUM': 1,
    'HIGH': 2
})

df['battaramulla_congestion_encoded'] = df['battaramulla_congestion'].map({
    'LOW': 0,
    'MEDIUM': 1,
    'HIGH': 2
})