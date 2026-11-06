import sys
import os
import time
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(os.path.join(project_root, "backend"))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

print("=== TESTING FASTAPI /translate ROUTE ===")
test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

response = client.post("/translate", json={"video_url": test_url})
print("POST /translate status:", response.status_code)
data = response.json()
print("Initial response payload:", json.dumps({k: v for k, v in data.items() if k != "animation_data"}, indent=2))

video_id = data.get("video_id")

if data.get("status") != "completed":
    print("\nPolling /translate/status...")
    for _ in range(30):
        time.sleep(2)
        res = client.get(f"/translate/status?video_id={video_id}")
        st = res.json()
        status = st.get("status")
        print(f"  Status: {status}, gloss words so far: {len(st.get('gloss_sequence', []))}")
        if status == "completed":
            data = client.post("/translate", json={"video_url": test_url}).json()
            break

if data.get("status") == "completed":
    print("\nTranslation Pipeline Completed Successfully!")
    print("Gloss Sequence:", data.get("gloss_sequence"))
    anim = data.get("animation_data", {})
    frames = anim.get("frames", [])
    print("Total animation frames:", len(frames))
    if frames:
        sample_frame = frames[min(10, len(frames)-1)]
        print("Sample frame rot (J_Bip_R_UpperArm):", sample_frame.get("rotations", {}).get("J_Bip_R_UpperArm"))
        print("Sample frame rot (J_Bip_R_Index1):", sample_frame.get("rotations", {}).get("J_Bip_R_Index1"))
