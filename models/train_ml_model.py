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
    
