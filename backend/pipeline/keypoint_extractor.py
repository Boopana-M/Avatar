import os
import json
import cv2
import mediapipe as mp

# Initialize MediaPipe Holistic
mp_holistic = mp.solutions.holistic

def extract_keypoints_from_video(video_path: str) -> list:
    """
    Runs MediaPipe Holistic on a video and extracts pose, face, and hand landmarks for each frame.
    Returns:
        list of dict: A sequence of frame data containing extracted keypoints.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    print(f"[Keypoints] Extracting keypoints from: {video_path}")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Could not open video file: {video_path}")
        
    frame_keypoints = []
    frame_index = 0
    
    # Use MediaPipe Holistic context manager
    with mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        refine_face_landmarks=True
    ) as holistic:
        
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break
                
            # Convert the BGR image to RGB
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame with MediaPipe Holistic
            results = holistic.process(image_rgb)
            
            # Helper function to serialize landmarks
            def serialize_landmarks(landmarks):
                if not landmarks:
                    return []
                return [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": getattr(lm, 'visibility', 1.0)} 
                        for lm in landmarks.landmark]
            
            # Extract landmarks for this frame
            frame_data = {
                "frame": frame_index,
                "pose": serialize_landmarks(results.pose_landmarks),
                "face": serialize_landmarks(results.face_landmarks),
                "left_hand": serialize_landmarks(results.left_hand_landmarks),
                "right_hand": serialize_landmarks(results.right_hand_landmarks)
            }
            
            frame_keypoints.append(frame_data)
            frame_index += 1
            
    cap.release()
    print(f"[Keypoints] Extracted keypoints for {len(frame_keypoints)} frames from {os.path.basename(video_path)}.")
    return frame_keypoints

def gloss_sequence_to_keypoints(gloss_words: list, find_video_fn) -> tuple:
    """
    Given a list of gloss words and a pose matching function, finds videos and extracts
    keypoints. Stitches the keypoints together.
    Returns:
        tuple: (list of stitched frame keypoints, list of unmatched words)
    """
    stitched_keypoints = []
    unmatched_words = []
    
    for word in gloss_words:
        video_path = find_video_fn(word)
        if not video_path:
            print(f"[Keypoints] No video found for word: {word}")
            unmatched_words.append(word)
            continue
            
        try:
            keypoints = extract_keypoints_from_video(video_path)
            stitched_keypoints.extend(keypoints)
        except Exception as e:
            print(f"[Keypoints] Error extracting keypoints for word '{word}' from {video_path}: {e}")
            unmatched_words.append(word)
            
    return stitched_keypoints, unmatched_words

if __name__ == "__main__":
    # Test block
    print("Testing Keypoint Extractor module...")
    # This requires an actual video file to run, so we'll test it end-to-end in Step 10
    print("Module compiled successfully. Ready for use.")
