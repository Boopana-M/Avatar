import os
import sys
import json
import sqlite3
import threading
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Adjust paths to import pipeline modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(os.path.join(project_root, "backend", "pipeline"))

from captions import get_captions, extract_video_id
from asr_fallback import transcribe_audio
from gloss_generator import generate_gloss
from pose_matcher import build_dataset_index, lookup_sign
from keypoint_extractor import get_keypoints
from rig_mapper import map_captions_to_animation

app = FastAPI(title="Indian Sign Language Avatar API")

# Add CORS Middleware to support browser extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(project_root, "backend", "cache", "cache.db")
CACHE_DIR = os.path.join(project_root, "backend", "cache")
DATA_DIR = os.path.join(project_root, "data")
FINGERSPELLING_DIR = os.path.join(DATA_DIR, "fingerspelling")

def safe_log(msg):
    """
    Encode-safe logging for Windows and non-ASCII characters (e.g. music notes)
    """
    try:
        encoding = sys.stdout.encoding or 'utf-8'
        print(msg.encode(encoding, errors='replace').decode(encoding))
    except Exception:
        print(msg.encode('ascii', errors='replace').decode('ascii'))

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translations (
            video_id TEXT PRIMARY KEY,
            gloss_sequence TEXT,
            animation_data TEXT,
            unmatched_list TEXT,
            tier_info TEXT
        )
    """)
    conn.commit()
    # Add caption_blocks column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE translations ADD COLUMN caption_blocks TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()

init_db()

class TranslationRequest(BaseModel):
    video_url: str

def get_cached_translation(video_id: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT gloss_sequence, animation_data, unmatched_list, tier_info, caption_blocks FROM translations WHERE video_id = ?",
            (video_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "gloss_sequence": json.loads(row[0]),
                "animation_data": json.loads(row[1]),
                "unmatched_list": json.loads(row[2]),
                "tier_info": json.loads(row[3]),
                "caption_blocks": json.loads(row[4]) if len(row) > 4 and row[4] else []
            }
    except Exception as e:
        safe_log(f"Cache read error: {e}")
    return None

def set_cached_translation(video_id: str, data: dict):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO translations (video_id, gloss_sequence, animation_data, unmatched_list, tier_info, caption_blocks) VALUES (?, ?, ?, ?, ?, ?)",
            (
                video_id,
                json.dumps(data["gloss_sequence"]),
                json.dumps(data["animation_data"]),
                json.dumps(data["unmatched_list"]),
                json.dumps(data["tier_info"]),
                json.dumps(data["caption_blocks"])
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        safe_log(f"Cache write error: {e}")

@app.get("/avatar.vrm")
def get_avatar_vrm():
    """
    Serves the 3D VRM model with proper CORS and content headers
    """
    vrm_path = os.path.join(project_root, "backend", "models", "avatar.vrm")
    if not os.path.exists(vrm_path):
        vrm_path = os.path.join(project_root, "backend", "models", "Avatar.vrm")
    if not os.path.exists(vrm_path):
        raise HTTPException(status_code=404, detail="Avatar.vrm not found in backend/models/")
    return FileResponse(vrm_path, media_type="application/octet-stream")

ACTIVE_TASKS = {}
ACTIVE_TASKS_LOCK = threading.Lock()

def run_translation_pipeline(video_id: str, youtube_url: str):
    try:
        # Step 1: Set status to fetching_captions
        with ACTIVE_TASKS_LOCK:
            ACTIVE_TASKS[video_id] = {
                "status": "fetching_captions",
                "video_id": video_id,
                "caption_blocks": [],
                "processed_indices": [],
                "unmatched_list": [],
                "tier_info": [],
                "gloss_sequence": [],
                "animation_data": None,
                "new_blocks_queue": [],  # blocks processed but not yet picked up by polling
                "error": None
            }
        
        # Step 2: Fetch captions
        safe_log(f"Background task: Attempting standard captions retrieval for {video_id}...")
        captions = []
        try:
            captions = get_captions(youtube_url)
            safe_log(f"Background task: Retrieved {len(captions)} caption blocks.")
        except Exception as e:
            safe_log(f"Background task: Captions unavailable ({e}). Falling back to Whisper...")
            try:
                captions = transcribe_audio(youtube_url, model_name="tiny")
                safe_log(f"Background task: Whisper transcription completed. Found {len(captions)} blocks.")
            except Exception as asr_err:
                safe_log(f"Background task: ASR fallback failed: {asr_err}")
                with ACTIVE_TASKS_LOCK:
                    ACTIVE_TASKS[video_id]["status"] = "failed"
                    ACTIVE_TASKS[video_id]["error"] = f"ASR transcription failed: {asr_err}"
                return
                
        if not captions:
            with ACTIVE_TASKS_LOCK:
                ACTIVE_TASKS[video_id]["status"] = "failed"
                ACTIVE_TASKS[video_id]["error"] = "No captions or speech detected in the video."
            return
            
        # Create lightweight version of caption blocks for frontend HUD
        frontend_caption_blocks = []
        for block in captions:
            frontend_caption_blocks.append({
                "start": block["start"],
                "end": block["end"],
                "text": block["text"],
                "words": []  # will be filled progressively as blocks are processed
            })
            
        with ACTIVE_TASKS_LOCK:
            task = ACTIVE_TASKS[video_id]
            task["caption_blocks"] = frontend_caption_blocks
            task["status"] = "processing"
            
        # Step 3: Build dataset index
        dataset_index = build_dataset_index(DATA_DIR)
        
        processed_blocks = [None] * len(captions)
        unmatched_set = set()
        tier_info_list = []
        global_gloss_seq = []
        
        # Step 4: Process blocks one by one
        for idx, block in enumerate(captions):
            text = block["text"]
            safe_log(f"Background task: Processing block {idx+1}/{len(captions)}: [{block['start']}s - {block['end']}s] {text}")
            
            # Translate English -> ISL gloss
            try:
                gloss_text = generate_gloss(text)
                safe_log(f"  Gloss: {gloss_text}")
            except Exception as gloss_err:
                safe_log(f"  Gloss generation failed for '{text}': {gloss_err}")
                processed_blocks[idx] = {
                    "start": block["start"],
                    "end": block["end"],
                    "words": []
                }
                continue
                
            gloss_words = gloss_text.split()
            block_words_data = []
            words_light = []
            
            for word in gloss_words:
                global_gloss_seq.append(word)
                
                # Lookup
                res = lookup_sign(word, dataset_index, FINGERSPELLING_DIR)
                source = res["source"]
                tier = res["tier"]
                
                # Retrieve keypoints
                try:
                    if source == "fingerspelling":
                        for letter_entry in res.get("letters", []):
                            letter_entry["keypoints"] = get_keypoints(letter_entry, CACHE_DIR)
                    elif source in ("landmarks", "videos", "csltr"):
                        res["keypoints"] = get_keypoints(res, CACHE_DIR)
                except Exception as kp_err:
                    safe_log(f"    Keypoint extraction failed for '{word}': {kp_err}")
                    source = "unmatched"
                    res["source"] = "unmatched"
                    res["keypoints"] = []
                    
                if source == "unmatched":
                    unmatched_set.add(word)
                    
                word_tier_item = {
                    "word": word,
                    "tier": tier if source != "unmatched" else 3,
                    "source": source
                }
                tier_info_list.append(word_tier_item)
                words_light.append(word_tier_item)
                block_words_data.append(res)
                
            processed_blocks[idx] = {
                "start": block["start"],
                "end": block["end"],
                "words": block_words_data
            }
            
            # Step 5: Run rig mapper globally on all currently processed blocks to get correct blend animations
            active_processed_blocks = [pb for pb in processed_blocks if pb is not None]
            try:
                global_animation = map_captions_to_animation(active_processed_blocks, fps=30)
            except Exception as map_err:
                safe_log(f"Rig mapping failed during progressive generation: {map_err}")
                continue
                
            # Step 6: Extract frames corresponding to this specific block (with 0.5s padding for transitions)
            block_start_pad = max(0.0, block["start"] - 0.5)
            block_end_pad = block["end"] + 0.5
            
            block_frames = []
            for frame in global_animation.get("frames", []):
                if block_start_pad <= frame["time"] <= block_end_pad:
                    block_frames.append(frame)
                    
            # Step 7: Push the newly finished block into the new_blocks_queue
            new_block_data = {
                "block_idx": idx,
                "words": words_light,
                "frames": block_frames
            }
            
            with ACTIVE_TASKS_LOCK:
                task = ACTIVE_TASKS[video_id]
                task["new_blocks_queue"].append(new_block_data)
                task["processed_indices"].append(idx)
                task["unmatched_list"] = list(unmatched_set)
                task["tier_info"] = tier_info_list
                task["gloss_sequence"] = global_gloss_seq
                task["animation_data"] = global_animation
                
        # Step 8: Completed! Cache and set status
        # Build final complete response_data
        response_data = {
            "gloss_sequence": global_gloss_seq,
            "animation_data": global_animation,
            "unmatched_list": list(unmatched_set),
            "tier_info": tier_info_list,
            "caption_blocks": [
                {
                    "start": b["start"],
                    "end": b["end"],
                    "text": b["text"],
                    "words": processed_blocks[i]["words"] if (i < len(processed_blocks) and processed_blocks[i]) else []
                }
                for i, b in enumerate(captions)
            ]
        }
        
        # Format caption blocks lightweight for JSON storage
        for cb in response_data["caption_blocks"]:
            words_light = []
            for w in cb.get("words", []):
                words_light.append({
                    "word": w.get("word", ""),
                    "tier": w.get("tier", 3),
                    "source": w.get("source", "unmatched")
                })
            cb["words"] = words_light
            
        set_cached_translation(video_id, response_data)
        safe_log(f"Background task: Completed and cached translation for {video_id}.")
        
        with ACTIVE_TASKS_LOCK:
            ACTIVE_TASKS[video_id]["status"] = "completed"
            
    except Exception as exc:
        safe_log(f"Background task error: {exc}")
        with ACTIVE_TASKS_LOCK:
            if video_id in ACTIVE_TASKS:
                ACTIVE_TASKS[video_id]["status"] = "failed"
                ACTIVE_TASKS[video_id]["error"] = str(exc)

@app.post("/translate")
def translate_video(payload: TranslationRequest):
    youtube_url = payload.video_url
    safe_log(f"Received translation request for: {youtube_url}")
    
    try:
        video_id = extract_video_id(youtube_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid YouTube URL: {e}")
        
    # Check cache first
    cached = get_cached_translation(video_id)
    if cached:
        safe_log(f"Cache HIT for video_id: {video_id}")
        return {
            "status": "completed",
            "video_id": video_id,
            "caption_blocks": cached["caption_blocks"],
            "animation_data": cached["animation_data"],
            "unmatched_list": cached["unmatched_list"],
            "tier_info": cached["tier_info"],
            "gloss_sequence": cached["gloss_sequence"]
        }
        
    # Check if task is already running
    with ACTIVE_TASKS_LOCK:
        task = ACTIVE_TASKS.get(video_id)
        
    if task:
        safe_log(f"Task already active for video_id: {video_id}")
        return {
            "status": task["status"],
            "video_id": video_id,
            "caption_blocks": task["caption_blocks"]
        }
        
    # Start task in background thread
    safe_log(f"Starting background translation task for: {video_id}")
    thread = threading.Thread(target=run_translation_pipeline, args=(video_id, youtube_url))
    thread.daemon = True
    thread.start()
    
    return {
        "status": "fetching_captions",
        "video_id": video_id,
        "caption_blocks": []
    }

@app.get("/translate/status")
def get_translation_status(video_id: str, received_blocks: str = ""):
    with ACTIVE_TASKS_LOCK:
        task = ACTIVE_TASKS.get(video_id)
        
    if not task:
        # Check if it is already in cache
        cached = get_cached_translation(video_id)
        if cached:
            return {
                "status": "completed",
                "video_id": video_id,
                "caption_blocks": cached["caption_blocks"],
                "new_blocks": []
            }
        raise HTTPException(status_code=404, detail="Task not found")
        
    status = task["status"]
    error = task["error"]
    
    if status == "failed":
        return {
            "status": "failed",
            "video_id": video_id,
            "error": error
        }
        
    if status == "fetching_captions":
        return {
            "status": "fetching_captions",
            "video_id": video_id
        }
        
    # parse received blocks
    received_set = set()
    if received_blocks:
        try:
            received_set = {int(x) for x in received_blocks.split(",") if x.strip().isdigit()}
        except Exception:
            pass
            
    # Find which blocks in task["new_blocks_queue"] have NOT been received
    new_blocks_to_send = []
    with ACTIVE_TASKS_LOCK:
        for item in task["new_blocks_queue"]:
            if item["block_idx"] not in received_set:
                new_blocks_to_send.append(item)
                
    response = {
        "status": status,
        "video_id": video_id,
        "caption_blocks": task["caption_blocks"],
        "new_blocks": new_blocks_to_send,
        "unmatched_list": task["unmatched_list"],
        "tier_info": task["tier_info"],
        "gloss_sequence": task["gloss_sequence"]
    }
    
    return response

if __name__ == "__main__":
    import uvicorn
    # Set default port to 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
