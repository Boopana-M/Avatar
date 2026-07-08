import os
import json
import math
import numpy as np
from pygltflib import GLTF2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AVATAR_DEFAULT_PATH = os.path.join(BASE_DIR, "backend", "models", "avatar.glb")

# Standard bone name mapping table (Mixamo / Ready Player Me naming)
DEFAULT_BONE_MAPPING = {
    "leftArm": "LeftArm",
    "leftForeArm": "LeftForeArm",
    "leftHand": "LeftHand",
    "rightArm": "RightArm",
    "rightForeArm": "RightForeArm",
    "rightHand": "RightHand",
    # Left fingers
    "leftThumb1": "LeftHandThumb1", "leftThumb2": "LeftHandThumb2", "leftThumb3": "LeftHandThumb3",
    "leftIndex1": "LeftHandIndex1", "leftIndex2": "LeftHandIndex2", "leftIndex3": "LeftHandIndex3",
    "leftMiddle1": "LeftHandMiddle1", "leftMiddle2": "LeftHandMiddle2", "leftMiddle3": "LeftHandMiddle3",
    "leftRing1": "LeftHandRing1", "leftRing2": "LeftHandRing2", "leftRing3": "LeftHandRing3",
    "leftPinky1": "LeftHandPinky1", "leftPinky2": "LeftHandPinky2", "leftPinky3": "LeftHandPinky3",
    # Right fingers
    "rightThumb1": "RightHandThumb1", "rightThumb2": "RightHandThumb2", "rightThumb3": "RightHandThumb3",
    "rightIndex1": "RightHandIndex1", "rightIndex2": "RightHandIndex2", "rightIndex3": "RightHandIndex3",
    "rightMiddle1": "RightHandMiddle1", "rightMiddle2": "RightHandMiddle2", "rightMiddle3": "RightHandMiddle3",
    "rightRing1": "RightHandRing1", "rightRing2": "RightHandRing2", "rightRing3": "RightHandRing3",
    "rightPinky1": "RightHandPinky1", "rightPinky2": "RightHandPinky2", "rightPinky3": "RightHandPinky3"
}

def get_avatar_bone_names(avatar_path=None) -> dict:
    """
    Reads the avatar GLB nodes using pygltflib to check actual bone names.
    Maps generic rig bone names to the actual bone names found in the GLB file.
    """
    if not avatar_path:
        avatar_path = AVATAR_DEFAULT_PATH
        
    mapping = DEFAULT_BONE_MAPPING.copy()
    if not os.path.exists(avatar_path):
        print(f"[RigMapper] Avatar model not found at {avatar_path}. Using default RPM naming.")
        return mapping
        
    try:
        gltf = GLTF2.load(avatar_path)
        node_names = [node.name for node in gltf.nodes if node.name]
        print(f"[RigMapper] Successfully loaded {avatar_path}. Found {len(node_names)} nodes.")
        
        # Check bone name prefixes (e.g. 'mixamorig:LeftArm' or 'Armature|LeftArm')
        # We search case-insensitively for the matching bone in the nodes list
        for key, default_val in DEFAULT_BONE_MAPPING.items():
            for node_name in node_names:
                # Match if node_name ends with default_val or matches standard mixamo formats
                if (node_name.lower().endswith(default_val.lower()) or 
                    default_val.lower() in node_name.lower()):
                    mapping[key] = node_name
                    break
                    
        print("[RigMapper] Custom GLB bone mapping initialized successfully.")
    except Exception as e:
        print(f"[RigMapper] Error parsing GLB file bone names: {e}. Falling back to default RPM naming.")
        
    return mapping

def nlerp_quaternion(q1, q2, t):
    """
    Spherical-like Normalized Linear Interpolation (NLERP) for two quaternions [x, y, z, w].
    """
    q1 = np.array(q1)
    q2 = np.array(q2)
    
    # Double cover check: if dot product is negative, invert one quaternion
    dot = np.dot(q1, q2)
    if dot < 0.0:
        q2 = -q2
        dot = -dot
        
    q_interp = q1 * (1.0 - t) + q2 * t
    norm = np.linalg.norm(q_interp)
    if norm < 1e-6:
        return list(q1)
    return list(q_interp / norm)

def get_rotation_quaternion(v_from, v_to):
    """
    Computes the quaternion that rotates vector v_from into vector v_to.
    """
    v_from_norm = np.linalg.norm(v_from)
    v_to_norm = np.linalg.norm(v_to)
    if v_from_norm < 1e-6 or v_to_norm < 1e-6:
        return [0.0, 0.0, 0.0, 1.0]
        
    v_from = v_from / v_from_norm
    v_to = v_to / v_to_norm
    
    dot = np.dot(v_from, v_to)
    if dot > 0.99999:
        return [0.0, 0.0, 0.0, 1.0]
    elif dot < -0.99999:
        # 180 degrees rotation: find any orthogonal axis
        orthogonal = np.array([1.0, 0.0, 0.0])
        if abs(v_from[0]) > 0.9:
            orthogonal = np.array([0.0, 1.0, 0.0])
        axis = np.cross(v_from, orthogonal)
        axis = axis / np.linalg.norm(axis)
        return [float(axis[0]), float(axis[1]), float(axis[2]), 0.0]
        
    cross = np.cross(v_from, v_to)
    s = math.sqrt((1.0 + dot) * 2.0)
    inv_s = 1.0 / s
    
    return [
        float(cross[0] * inv_s),
        float(cross[1] * inv_s),
        float(cross[2] * inv_s),
        float(s * 0.5)
    ]

def calculate_finger_bending_quaternion(finger_landmarks, is_left=True):
    """
    Estimates the bending quaternion of finger joints based on landmarks.
    A simplified model: we inspect the angle of the PIP joint.
    """
    if len(finger_landmarks) < 4:
        return [0.0, 0.0, 0.0, 1.0] # Default open
        
    # Landmarks: 0: MCP, 1: PIP, 2: DIP, 3: TIP
    p0 = np.array([finger_landmarks[0]['x'], finger_landmarks[0]['y'], finger_landmarks[0]['z']])
    p1 = np.array([finger_landmarks[1]['x'], finger_landmarks[1]['y'], finger_landmarks[1]['z']])
    p2 = np.array([finger_landmarks[2]['x'], finger_landmarks[2]['y'], finger_landmarks[2]['z']])
    
    v1 = p1 - p0
    v2 = p2 - p1
    
    v1_n = v1 / np.linalg.norm(v1) if np.linalg.norm(v1) > 1e-6 else v1
    v2_n = v2 / np.linalg.norm(v2) if np.linalg.norm(v2) > 1e-6 else v2
    
    dot = np.clip(np.dot(v1_n, v2_n), -1.0, 1.0)
    angle = math.acos(dot) # Angle in radians (0: open, 1.5+: closed)
    
    # Limit angle to maximum bending
    angle = np.clip(angle, 0.0, 1.4)
    
    # Left fingers bend in opposite direction along local Z axis in standard rigs
    direction = -1.0 if is_left else 1.0
    
    # Calculate quaternion for rotation around local Z axis (bending axis)
    half_angle = (angle * direction) / 2.0
    return [0.0, 0.0, math.sin(half_angle), math.cos(half_angle)]

def map_frame_keypoints_to_rotations(frame_data, bone_mapping) -> dict:
    """
    Maps a single frame of MediaPipe coordinates to a dict of bone names and quaternions.
    """
    rotations = {}
    pose = frame_data.get('pose', [])
    left_hand = frame_data.get('left_hand', [])
    right_hand = frame_data.get('right_hand', [])
    
    # --- Map Arm Rotations from Pose Landmarks ---
    # Index mappings for MediaPipe Pose:
    # 11: L_Shoulder, 13: L_Elbow, 15: L_Wrist
    # 12: R_Shoulder, 14: R_Elbow, 16: R_Wrist
    if len(pose) > 16:
        # Left Upper Arm
        p_l_shoulder = np.array([pose[11]['x'], pose[11]['y'], pose[11]['z']])
        p_l_elbow = np.array([pose[13]['x'], pose[13]['y'], pose[13]['z']])
        v_l_arm = p_l_elbow - p_l_shoulder
        # Default Left Arm points along +X in T-Pose
        rotations[bone_mapping['leftArm']] = get_rotation_quaternion(np.array([1.0, 0.0, 0.0]), v_l_arm)
        
        # Left Lower Arm (Forearm)
        p_l_wrist = np.array([pose[15]['x'], pose[15]['y'], pose[15]['z']])
        v_l_forearm = p_l_wrist - p_l_elbow
        rotations[bone_mapping['leftForeArm']] = get_rotation_quaternion(np.array([1.0, 0.0, 0.0]), v_l_forearm)
        
        # Right Upper Arm
        p_r_shoulder = np.array([pose[12]['x'], pose[12]['y'], pose[12]['z']])
        p_r_elbow = np.array([pose[14]['x'], pose[14]['y'], pose[14]['z']])
        v_r_arm = p_r_elbow - p_r_shoulder
        # Default Right Arm points along -X in T-Pose
        rotations[bone_mapping['rightArm']] = get_rotation_quaternion(np.array([-1.0, 0.0, 0.0]), v_r_arm)
        
        # Right Lower Arm (Forearm)
        p_r_wrist = np.array([pose[16]['x'], pose[16]['y'], pose[16]['z']])
        v_r_forearm = p_r_wrist - p_r_elbow
        rotations[bone_mapping['rightForeArm']] = get_rotation_quaternion(np.array([-1.0, 0.0, 0.0]), v_r_forearm)

    # --- Map Left Hand Fingers ---
    if left_hand and len(left_hand) == 21:
        # Landmarks are grouped: Thumb (1-4), Index (5-8), Middle (9-12), Ring (13-16), Pinky (17-20)
        rotations[bone_mapping['leftThumb1']] = calculate_finger_bending_quaternion(left_hand[1:5], is_left=True)
        rotations[bone_mapping['leftThumb2']] = calculate_finger_bending_quaternion(left_hand[2:5], is_left=True)
        
        rotations[bone_mapping['leftIndex1']] = calculate_finger_bending_quaternion(left_hand[5:9], is_left=True)
        rotations[bone_mapping['leftIndex2']] = calculate_finger_bending_quaternion(left_hand[6:9], is_left=True)
        
        rotations[bone_mapping['leftMiddle1']] = calculate_finger_bending_quaternion(left_hand[9:13], is_left=True)
        rotations[bone_mapping['leftMiddle2']] = calculate_finger_bending_quaternion(left_hand[10:13], is_left=True)
        
        rotations[bone_mapping['leftRing1']] = calculate_finger_bending_quaternion(left_hand[13:17], is_left=True)
        rotations[bone_mapping['leftRing2']] = calculate_finger_bending_quaternion(left_hand[14:17], is_left=True)
        
        rotations[bone_mapping['leftPinky1']] = calculate_finger_bending_quaternion(left_hand[17:21], is_left=True)
        rotations[bone_mapping['leftPinky2']] = calculate_finger_bending_quaternion(left_hand[18:21], is_left=True)
        
    # --- Map Right Hand Fingers ---
    if right_hand and len(right_hand) == 21:
        rotations[bone_mapping['rightThumb1']] = calculate_finger_bending_quaternion(right_hand[1:5], is_left=False)
        rotations[bone_mapping['rightThumb2']] = calculate_finger_bending_quaternion(right_hand[2:5], is_left=False)
        
        rotations[bone_mapping['rightIndex1']] = calculate_finger_bending_quaternion(right_hand[5:9], is_left=False)
        rotations[bone_mapping['rightIndex2']] = calculate_finger_bending_quaternion(right_hand[6:9], is_left=False)
        
        rotations[bone_mapping['rightMiddle1']] = calculate_finger_bending_quaternion(right_hand[9:13], is_left=False)
        rotations[bone_mapping['rightMiddle2']] = calculate_finger_bending_quaternion(right_hand[10:13], is_left=False)
        
        rotations[bone_mapping['rightRing1']] = calculate_finger_bending_quaternion(right_hand[13:17], is_left=False)
        rotations[bone_mapping['rightRing2']] = calculate_finger_bending_quaternion(right_hand[14:17], is_left=False)
        
        rotations[bone_mapping['rightPinky1']] = calculate_finger_bending_quaternion(right_hand[17:21], is_left=False)
        rotations[bone_mapping['rightPinky2']] = calculate_finger_bending_quaternion(right_hand[18:21], is_left=False)

    return rotations

def interpolate_poses(frame_rotations_1, frame_rotations_2, steps=10) -> list:
    """
    Interpolates between two poses (rotations) using NLERP over joint quaternions.
    """
    interpolated_sequence = []
    
    for i in range(1, steps + 1):
        t = i / float(steps + 1)
        interp_frame = {}
        
        # Interpolate all bones present in either frame
        all_bones = set(frame_rotations_1.keys()).union(set(frame_rotations_2.keys()))
        for bone in all_bones:
            q1 = frame_rotations_1.get(bone, [0.0, 0.0, 0.0, 1.0])
            q2 = frame_rotations_2.get(bone, [0.0, 0.0, 0.0, 1.0])
            interp_frame[bone] = nlerp_quaternion(q1, q2, t)
            
        interpolated_sequence.append(interp_frame)
        
    return interpolated_sequence

def map_keypoints_to_rig_sequence(stitched_keypoints, avatar_path=None) -> list:
    """
    Converts a stitched sequence of keypoints into bone rotations, inserting smooth
    interpolation between segments.
    """
    bone_mapping = get_avatar_bone_names(avatar_path)
    
    raw_rotations = []
    for frame in stitched_keypoints:
        raw_rotations.append(map_frame_keypoints_to_rotations(frame, bone_mapping))
        
    if not raw_rotations:
        return []
        
    # Insert smooth interpolation between separate signs/words if needed.
    # In this continuous translation, since we stitched frames directly,
    # let's insert 8 frames of interpolation at transitions where frames jump
    # (indicated by frame_index resets in stitched keypoints).
    smoothed_rotations = [raw_rotations[0]]
    
    for idx in range(1, len(raw_rotations)):
        current_frame = raw_rotations[idx]
        prev_frame = raw_rotations[idx-1]
        
        # Check if this frame is a transition to a new word.
        # We can look at the frame index of the raw keypoints.
        # If frame index went from N to 0, it means a new video started!
        curr_frame_idx = stitched_keypoints[idx]['frame']
        prev_frame_idx = stitched_keypoints[idx-1]['frame']
        
        if curr_frame_idx == 0 and prev_frame_idx > 0:
            # We are transitioning between two sign clips!
            # Insert 8 frames of interpolation to smooth the transition.
            transition_frames = interpolate_poses(prev_frame, current_frame, steps=8)
            smoothed_rotations.extend(transition_frames)
            
        smoothed_rotations.append(current_frame)
        
    # Format to timestamped animation data: [{time: float, rotations: {bone: [x,y,z,w]}}]
    # Assuming 25 frames per second (fps) -> 0.04s per frame
    fps = 25.0
    animation_sequence = []
    for idx, rot in enumerate(smoothed_rotations):
        animation_sequence.append({
            "time": round(idx / fps, 3),
            "rotations": rot
        })
        
    print(f"[RigMapper] Successfully mapped sequence to {len(animation_sequence)} animation frames.")
    return animation_sequence

if __name__ == "__main__":
    print("Testing Rig Mapper...")
    # Get standard names
    bone_map = get_avatar_bone_names()
    print("Mapped standard names sample:")
    print("  leftArm  ->", bone_map['leftArm'])
    print("  rightArm ->", bone_map['rightArm'])
    print("Rig Mapper ready.")
