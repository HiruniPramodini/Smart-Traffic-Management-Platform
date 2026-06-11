## Smart-Traffic-Management-Platform ##

# Collecting Data 

 ** YouTube footages **
pip install yt-dlp
yt-dlp "https://youtu.be/ANhIuoJcSm4" -o "srilanka_traffic.mp4"


 ** Run YOLO on it **
from ultralytics import YOLO
import cv2
import csv

model = YOLO("yolov8n.pt")  # downloads automatically first time

cap = cv2.VideoCapture("srilanka_traffic.mp4")
fps = cap.get(cv2.CAP_PROP_FPS)
frame_interval = int(fps * 2)  # one reading every 2 seconds

records = []
frame_count = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    if frame_count % frame_interval == 0:
        results = model(frame, classes=[2, 3, 5, 7])
        # 2=car, 3=motorcycle, 5=bus, 7=truck

        counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
        for box in results[0].boxes:
            label = model.names[int(box.cls)]
            if label in counts:
                counts[label] += 1

        records.append({
            "frame": frame_count,
            "time_sec": round(frame_count / fps, 1),
            **counts,
            "total": sum(counts.values())
        })

    frame_count += 1

cap.release()

with open("srilanka_traffic_data.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)

print(f"Done — {len(records)} records saved")
