import os
import sys
import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, classification_report

def train_model():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    csv_path = os.path.join(project_root, "data", "processed", "kaduwela_corridor_7day.csv")

    # Check if the unified dataset is missing or is just a sample stub
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) < 1000000:
        print(f"Dataset {csv_path} is missing or incomplete. Generating the full 7-day dataset (50,400 rows)...")
        try:
            from data.processed.generate_7day_csv import generate
            generate(csv_path)
            print("Dataset generation complete!")
        except Exception as e:
            print(f"Error generating 7-day CSV: {e}")
            raise e

    # Load the full 7-day dataset
    df = pd.read_csv(csv_path)

    print("Dataset loaded successfully!")
    print("Initial shape:", df.shape)

    # Junction arms definition
    JUNCTION_ARMS = {
        "Kaduwela": ["malabe", "biyagama", "kotikawatta", "ranala"],
        "Malabe": ["kaduwela", "athurugiriya", "battaramulla"],
        "Biyagama": ["kaduwela", "industrial", "kelaniya"],
        "Kotikawatta": ["kaduwela", "kolonnawa", "mulleriyawa"],
        "Ranala": ["kaduwela", "hanwella", "avissawella"]
    }

    # Calculate average wait time, queue length, and total vehicles for each junction row
    df['avg_wait'] = 0.0
    df['avg_queue'] = 0.0
    df['total_vehicles'] = 0.0

    for jname, arms in JUNCTION_ARMS.items():
        mask = df['junction'] == jname
        if mask.any():
            wait_cols = [f"{arm}_wait_sec" for arm in arms]
            queue_cols = [f"{arm}_queue" for arm in arms]
            total_cols = [f"{arm}_total" for arm in arms]
            
            df.loc[mask, 'avg_wait'] = df.loc[mask, wait_cols].mean(axis=1)
            df.loc[mask, 'avg_queue'] = df.loc[mask, queue_cols].mean(axis=1)
            df.loc[mask, 'total_vehicles'] = df.loc[mask, total_cols].sum(axis=1)

    # Map current congestion level based on average metrics
    def get_congestion_level(wait, queue):
        if wait > 60 or queue > 50:
            return 2  # HIGH
        elif (30 <= wait <= 60) or (25 <= queue <= 50):
            return 1  # MEDIUM
        else:
            return 0  # LOW

    df['congestion_level'] = df.apply(
        lambda r: get_congestion_level(r['avg_wait'], r['avg_queue']),
        axis=1
    )

    # Target: Shift congestion level by -15 minutes (15 rows) per junction per day
    df['future_congestion'] = df.groupby(['junction', 'date'])['congestion_level'].shift(-15)

    # Drop rows where target is NaN (the last 15 minutes of each day)
    df = df.dropna(subset=['future_congestion'])
    df['future_congestion'] = df['future_congestion'].astype(int)

    # Encoding categorical maps
    junction_map = {"Kaduwela": 0, "Malabe": 1, "Biyagama": 2, "Kotikawatta": 3, "Ranala": 4}
    dow_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    weather_map = {"clear": 0, "overcast": 1, "foggy": 2, "light_rain": 3, "heavy_rain": 4}

    df['junction_encoded'] = df['junction'].map(junction_map)
    df['dow_encoded'] = df['day_of_week'].map(dow_map)
    df['weather_encoded'] = df['weather'].map(weather_map)

    # Feature and target columns
    feature_cols = [
        'junction_encoded', 'hour', 'dow_encoded', 'weather_encoded', 
        'total_vehicles', 'avg_wait', 'avg_queue'
    ]
    X = df[feature_cols]
    y = df['future_congestion']

    print("Features (X) shape:", X.shape)
    print("Target (y) shape:", y.shape)

    # Split into train/test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print(f"\nTraining set: {X_train.shape[0]} samples")
    print(f"Testing set: {X_test.shape[0]} samples")

    # Train XGBoost Classifier
    print("Training XGBoost Classifier...")
    model = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        verbosity=0
    )
    model.fit(X_train, y_train)
    print("Model training complete!")

    # Evaluation
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy: {accuracy * 100:.2f}%")
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['LOW', 'MEDIUM', 'HIGH']))

    # Save the model
    model_dir = os.path.join(project_root, "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "kaduwela_congestion_model.pkl")
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"Saved trained model to: {model_path}")

if __name__ == "__main__":
    train_model()


 