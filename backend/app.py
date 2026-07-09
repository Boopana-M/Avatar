import os
import json
import sqlite3
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Reconfigure stdout and stderr to UTF-8 to prevent UnicodeEncodeError on Windows terminals
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Import pipeline modules
from pipeline.captions import get_captions, extract_video_id, CaptionsNotFoundError
from pipeline.asr_fallback import transcribe_audio
from pipeline.gloss_generator import text_to_gloss
from pipeline.pose_matcher import find_video_for_gloss
from pipeline.keypoint_extractor import gloss_sequence_to_keypoints
from pipeline.rig_mapper import map_keypoints_to_rig_sequence

from fastapi.responses import FileResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

DB_PATH = os.path.join(CACHE_DIR, "translations.db")

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            video_id TEXT PRIMARY KEY,
            youtube_url TEXT NOT NULL,
            animation_data TEXT NOT NULL,
            unmatched_words TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

app = FastAPI(title="ISL Avatar Translation API")

# Enable CORS for Chrome Extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Extension runs from chrome-extension:// origins
    allow_credentials=False,  # Set to False to allow "*" origin wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve models static folder with CORS headers using FileResponse
@app.get("/models/{file_path:path}")
async def serve_model(file_path: str):
    path = os.path.join(MODELS_DIR, file_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)

class TranslationRequest(BaseModel):
    youtube_url: str

def get_cached_translation(video_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT animation_data, unmatched_words FROM translations WHERE video_id = ?", (video_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "animation_data": json.loads(row["animation_data"]),
            "unmatched_words": json.loads(row["unmatched_words"])
        }
    return None

def save_translation_to_cache(video_id: str, youtube_url: str, animation_data: list, unmatched_words: list):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO translations (video_id, youtube_url, animation_data, unmatched_words) VALUES (?, ?, ?, ?)",
        (video_id, youtube_url, json.dumps(animation_data), json.dumps(unmatched_words))
    )
    conn.commit()
    conn.close()

@app.post("/translate")
async def translate_video(request: TranslationRequest):
    youtube_url = request.youtube_url
    try:
        video_id = extract_video_id(youtube_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # Check cache first
    cached = get_cached_translation(video_id)
    if cached:
        print(f"[API] Serving cached translation for video: {video_id}")
        return {
            "status": "success",
            "video_id": video_id,
            "cached": True,
            "animation_data": cached["animation_data"],
            "unmatched_words": cached["unmatched_words"]
        }
        
    print(f"[API] Starting translation pipeline for video: {video_id}")
    
    # 1. Fetch captions (try manual/auto first, fallback to Whisper ASR)
    try:
        captions = get_captions(youtube_url)
        method = "youtube_captions"
    except CaptionsNotFoundError:
        print("[API] Caption API failed. Falling back to ASR transcription (Whisper)...")
        try:
            captions = transcribe_audio(youtube_url)
            method = "whisper_asr"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"ASR fallback failed: {str(e)}")
            
    # 2. Process each caption block
    global_animation_data = []
    all_unmatched_words = set()
    fps = 25.0
    frame_duration = 1.0 / fps
    
    for cap in captions:
        start_time = cap["start"]
        end_time = cap["end"]
        text = cap["text"]
        
        # Replace non-ASCII characters for safe terminal print
        safe_text = text.encode('ascii', errors='replace').decode('ascii')
        print(f"[API] Processing segment [{start_time}s - {end_time}s]: '{safe_text}'")
        
        # Translate to ISL Gloss
        gloss_string = text_to_gloss(text)
        gloss_words = [w for w in gloss_string.split() if w]
        if not gloss_words:
            continue
            
        print(f"[API] Generated Gloss: {gloss_words}")
        
        # Match sign clips & extract keypoints
        stitched_keypoints, unmatched = gloss_sequence_to_keypoints(gloss_words, find_video_for_gloss)
        all_unmatched_words.update(unmatched)
        
        if not stitched_keypoints:
            continue
            
        # Map keypoints to bone rotations
        bone_rotations = map_keypoints_to_rig_sequence(stitched_keypoints)
        
        # Offset time values of frames by the caption start time
        for frame in bone_rotations:
            relative_time = frame["time"]
            absolute_time = round(start_time + relative_time, 3)
            # Stop adding animation frames if they exceed the caption end time
            if absolute_time > end_time:
                break
            global_animation_data.append({
                "time": absolute_time,
                "rotations": frame["rotations"]
            })
            
    # Sort global animation by time just in case
    global_animation_data.sort(key=lambda x: x["time"])
    
    unmatched_list = list(all_unmatched_words)
    
    # Save to SQLite cache
    save_translation_to_cache(video_id, youtube_url, global_animation_data, unmatched_list)
    
    return {
        "status": "success",
        "video_id": video_id,
        "cached": False,
        "method": method,
        "animation_data": global_animation_data,
        "unmatched_words": unmatched_list
    }

@app.get("/translate/{video_id}")
async def get_translation(video_id: str):
    cached = get_cached_translation(video_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Translation not found in cache.")
    return {
        "status": "success",
        "video_id": video_id,
        "cached": True,
        "animation_data": cached["animation_data"],
        "unmatched_words": cached["unmatched_words"]
    }

if __name__ == "__main__":
    import uvicorn
    # Start the server locally
    print("[API] Starting FastAPI server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
