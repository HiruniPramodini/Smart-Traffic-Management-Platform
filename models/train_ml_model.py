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

# Verify it worked
print(df[['time_period', 'time_period_encoded', 'kaduwela_congestion', 'kaduwela_congestion_encoded']].head(15))

#Labled the data 
# Features (X) for Kaduwela
X = df[['time_period_encoded', 'kaduwela_total', 'kaduwela_wait_sec', 'kaduwela_queue']]

# Label (y) for Kaduwela
y = df['kaduwela_congestion_encoded']

print("X shape:", X.shape)
print("y shape:", y.shape)
print("\nFirst 5 rows of X:")
print(X.head(5))
print("\nFirst 5 rows of y:")
print(y.head(5))

#Split data 
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"Training set: {X_train.shape[0]} samples")
print(f"Testing set: {X_test.shape[0]} samples")