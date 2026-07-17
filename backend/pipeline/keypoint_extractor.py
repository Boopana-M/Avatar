import os
import cv2
import json
import mediapipe as mp

# Initialize MediaPipe solutions
mp_holistic = mp.solutions.holistic
mp_hands = mp.solutions.hands

def extract_video_keypoints(video_path):
    """
    Extracts pose, left hand, and right hand keypoints frame-by-frame from a video.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Failed to open video file: {video_path}")
        
    frames_keypoints = []
    
    with mp_holistic.Holistic(
        static_image_mode=False, 
        model_complexity=1, 
        min_detection_confidence=0.5, 
        min_tracking_confidence=0.5
    ) as holistic:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = holistic.process(image_rgb)
            
            # Extract Pose (33 landmarks)
            pose_list = []
            if results.pose_landmarks:
                for lm in results.pose_landmarks.landmark:
                    pose_list.append([lm.x, lm.y, lm.z, lm.visibility])
            else:
                pose_list = [[0.0, 0.0, 0.0, 0.0] for _ in range(33)]
                
            # Extract Left Hand (21 landmarks)
            left_hand_list = []
            if results.left_hand_landmarks:
                for lm in results.left_hand_landmarks.landmark:
                    left_hand_list.append([lm.x, lm.y, lm.z])
            else:
                left_hand_list = [[0.0, 0.0, 0.0] for _ in range(21)]
                
            # Extract Right Hand (21 landmarks)
            right_hand_list = []
            if results.right_hand_landmarks:
                for lm in results.right_hand_landmarks.landmark:
                    right_hand_list.append([lm.x, lm.y, lm.z])
            else:
                right_hand_list = [[0.0, 0.0, 0.0] for _ in range(21)]
                
            frames_keypoints.append({
                "pose": pose_list,
                "left_hand": left_hand_list,
                "right_hand": right_hand_list
            })
            
    cap.release()
    return frames_keypoints

def extract_image_keypoints(image_path):
    """
    Extracts pose and hand keypoints from a static fingerspelling image.
    Uses MediaPipe Hands since static images typically only depict the hand.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise Exception(f"Failed to load image: {image_path}")
        
    image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    with mp_hands.Hands(
        static_image_mode=True, 
        max_num_hands=2, 
        min_detection_confidence=0.5
    ) as hands:
        results = hands.process(image_rgb)
        
        left_hand_list = [[0.0, 0.0, 0.0] for _ in range(21)]
        right_hand_list = [[0.0, 0.0, 0.0] for _ in range(21)]
        
        if results.multi_hand_landmarks:
            for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                handedness = results.multi_handedness[idx].classification[0].label  # 'Left' or 'Right'
                
                lm_list = []
                for lm in hand_landmarks.landmark:
                    lm_list.append([lm.x, lm.y, lm.z])
                    
                if handedness == 'Left':
                    left_hand_list = lm_list
                else:
                    right_hand_list = lm_list
                    
        # Pose landmarks mock (zeros) since static hand image contains no body
        pose_list = [[0.0, 0.0, 0.0, 0.0] for _ in range(33)]
        
        return [{
            "pose": pose_list,
            "left_hand": left_hand_list,
            "right_hand": right_hand_list
        }]

def extract_images_sequence_keypoints(image_paths):
    """
    Extracts keypoints frame-by-frame from a sequence of images (used for CSLTR Frames_Word_Level).
    """
    frames_keypoints = []
    
    with mp_holistic.Holistic(
        static_image_mode=True, 
        model_complexity=1, 
        min_detection_confidence=0.5
    ) as holistic:
        for img_path in image_paths:
            img = cv2.imread(img_path)
            if img is None:
                continue
                
            image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = holistic.process(image_rgb)
            
            # Pose
            pose_list = []
            if results.pose_landmarks:
                for lm in results.pose_landmarks.landmark:
                    pose_list.append([lm.x, lm.y, lm.z, lm.visibility])
            else:
                pose_list = [[0.0, 0.0, 0.0, 0.0] for _ in range(33)]
                
            # Left Hand
            left_hand_list = []
            if results.left_hand_landmarks:
                for lm in results.left_hand_landmarks.landmark:
                    left_hand_list.append([lm.x, lm.y, lm.z])
            else:
                left_hand_list = [[0.0, 0.0, 0.0] for _ in range(21)]
                
            # Right Hand
            right_hand_list = []
            if results.right_hand_landmarks:
                for lm in results.right_hand_landmarks.landmark:
                    right_hand_list.append([lm.x, lm.y, lm.z])
            else:
                right_hand_list = [[0.0, 0.0, 0.0] for _ in range(21)]
                
            frames_keypoints.append({
                "pose": pose_list,
                "left_hand": left_hand_list,
                "right_hand": right_hand_list
            })
            
    return frames_keypoints

def get_cache_path(input_path, cache_dir):
    """
    Generates a unique, sanitized cache filename for a single file.
    """
    project_root = os.path.dirname(os.path.dirname(cache_dir))
    rel_path = os.path.relpath(input_path, project_root)
    safe_name = rel_path.replace(os.sep, "_").replace(":", "_").replace("..", "up")
    return os.path.join(cache_dir, safe_name + ".json")

def get_sequence_cache_path(image_paths, cache_dir):
    """
    Generates a unique, sanitized cache filename for a sequence of image frames.
    """
    if not image_paths:
        return None
    parent_dir = os.path.dirname(image_paths[0])
    project_root = os.path.dirname(os.path.dirname(cache_dir))
    rel_path = os.path.relpath(parent_dir, project_root)
    safe_name = rel_path.replace(os.sep, "_").replace(":", "_").replace("..", "up")
    return os.path.join(cache_dir, safe_name + "_sequence.json")

def get_keypoints(match_entry, cache_dir):
    """
    Retrieves keypoints for a match, resolving from disk cache or running MediaPipe extractor.
    """
    os.makedirs(cache_dir, exist_ok=True)
    
    source = match_entry.get("source")
    files = match_entry.get("files", [])
    
    if source == "fingerspelling":
        if not files:
            return []
        img_path = files[0]
        cpath = get_cache_path(img_path, cache_dir)
        if os.path.exists(cpath):
            with open(cpath, 'r') as f:
                return json.load(f)
        keypoints = extract_image_keypoints(img_path)
        with open(cpath, 'w') as f:
            json.dump(keypoints, f)
        return keypoints
        
    elif source in ("landmarks", "videos"):
        if not files:
            return []
        video_path = files[0]
        cpath = get_cache_path(video_path, cache_dir)
        if os.path.exists(cpath):
            with open(cpath, 'r') as f:
                return json.load(f)
        keypoints = extract_video_keypoints(video_path)
        with open(cpath, 'w') as f:
            json.dump(keypoints, f)
        return keypoints
        
    elif source == "csltr":
        if not files:
            return []
        cpath = get_sequence_cache_path(files, cache_dir)
        if os.path.exists(cpath):
            with open(cpath, 'r') as f:
                return json.load(f)
        keypoints = extract_images_sequence_keypoints(files)
        with open(cpath, 'w') as f:
            json.dump(keypoints, f)
        return keypoints
        
    return []

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    cache_dir = os.path.join(project_root, "backend", "cache")
    
    print("=== TESTING KEYPOINT EXTRACTOR ===")
    
    # Mock lookup entries for test
    test_entries = [
        {
            "word": "A",
            "source": "fingerspelling",
            "files": [os.path.join(project_root, "data", "fingerspelling", "dataset - Gesture Speech", "a", "0.jpg")]
        }
    ]
    
    for entry in test_entries:
        word = entry["word"]
        print(f"Extracting keypoints for: '{word}'...")
        try:
            kps = get_keypoints(entry, cache_dir)
            print(f"Success! Extracted {len(kps)} frames of keypoints.")
            if kps:
                first_frame = kps[0]
                print(f"  Pose keypoints count: {len(first_frame['pose'])}")
                print(f"  Left Hand keypoints count: {len(first_frame['left_hand'])}")
                print(f"  Right Hand keypoints count: {len(first_frame['right_hand'])}")
        except Exception as e:
            print(f"Extraction failed for '{word}': {e}")
