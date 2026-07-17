import os
import re
import numpy as np
from pygltflib import GLTF2

# Vector and Quaternion math helpers in list/numpy format

def normalize_vector(v):
    norm = np.linalg.norm(v)
    if norm < 1e-6:
        return np.zeros(3)
    return v / norm

def q_multiply(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return [
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    ]

def q_conjugate(q):
    return [-q[0], -q[1], -q[2], q[3]]

def q_rotate_vector(q, v):
    q_v = [v[0], v[1], v[2], 0.0]
    q_conj = q_conjugate(q)
    res = q_multiply(q_multiply(q, q_v), q_conj)
    return np.array([res[0], res[1], res[2]])

def q_nlerp(q1, q2, t):
    dot = sum(a * b for a, b in zip(q1, q2))
    if dot < 0.0:
        q2 = [-x for x in q2]
        dot = -dot
    
    q_interp = [(1 - t) * a + t * b for a, b in zip(q1, q2)]
    norm = sum(x * x for x in q_interp) ** 0.5
    if norm < 1e-6:
        return q1
    return [x / norm for x in q_interp]

def rotation_between_vectors(v_from, v_to):
    v_from = normalize_vector(v_from)
    v_to = normalize_vector(v_to)
    
    cos_theta = np.dot(v_from, v_to)
    if cos_theta > 0.99999:
        return [0.0, 0.0, 0.0, 1.0]
    if cos_theta < -0.99999:
        orthogonal = np.array([0.0, 0.0, 0.0])
        if abs(v_from[0]) < 0.9:
            orthogonal[0] = 1.0
        else:
            orthogonal[1] = 1.0
        axis = np.cross(v_from, orthogonal)
        axis = normalize_vector(axis)
        return [axis[0], axis[1], axis[2], 0.0]
        
    axis = np.cross(v_from, v_to)
    axis = normalize_vector(axis)
    
    half_theta = np.arccos(cos_theta) / 2.0
    s = np.sin(half_theta)
    return [axis[0] * s, axis[1] * s, axis[2] * s, np.cos(half_theta)]

# VRM Bone discovery helper
def get_vrm_bone_names():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    
    vrm_path = os.path.join(project_root, "backend", "models", "avatar.vrm")
    if not os.path.exists(vrm_path):
        vrm_path = os.path.join(project_root, "backend", "models", "Avatar.vrm")
        
    if not os.path.exists(vrm_path):
        return []
        
    try:
        gltf = GLTF2().load_binary(vrm_path)
        return [node.name for node in gltf.nodes if node.name]
    except Exception:
        return []

# Resolve dynamic bone names from VRM
def discover_rig_mapping():
    bone_names = get_vrm_bone_names()
    
    def find_bone(pattern):
        pattern_lower = pattern.lower()
        for name in bone_names:
            if pattern_lower in name.lower():
                return name
        return None
        
    def find_finger_bones(prefix, finger):
        matches = [name for name in bone_names if name.startswith(prefix) and finger.lower() in name.lower()]
        matches.sort(key=lambda x: [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', x)])
        return matches

    mapping = {
        "L_UpperArm": find_bone("J_Bip_L_UpperArm") or "J_Bip_L_UpperArm",
        "L_LowerArm": find_bone("J_Bip_L_LowerArm") or "J_Bip_L_LowerArm",
        "L_Hand": find_bone("J_Bip_L_Hand") or "J_Bip_L_Hand",
        
        "R_UpperArm": find_bone("J_Bip_R_UpperArm") or "J_Bip_R_UpperArm",
        "R_LowerArm": find_bone("J_Bip_R_LowerArm") or "J_Bip_R_LowerArm",
        "R_Hand": find_bone("J_Bip_R_Hand") or "J_Bip_R_Hand",
    }
    
    fingers = ["Thumb", "Index", "Middle", "Ring", "Little"]
    for f in fingers:
        mapping[f"L_{f}"] = find_finger_bones("J_Bip_L_", f)
        mapping[f"R_{f}"] = find_finger_bones("J_Bip_R_", f)
        
    return mapping

# Global config mapping
RIG_MAP = discover_rig_mapping()

# Natural resting/idle pose rotations
# Instead of T-pose, arms hang down along the torso, slightly bent
REST_POSE = {
    RIG_MAP["L_UpperArm"]: [0.0, 0.0, -0.64279, 0.76604], # ~80 degrees down around Z
    RIG_MAP["R_UpperArm"]: [0.0, 0.0, 0.64279, 0.76604],  # ~80 degrees down around Z
    RIG_MAP["L_LowerArm"]: [0.0, 0.17365, 0.0, 0.98481],  # bent slightly
    RIG_MAP["R_LowerArm"]: [0.0, -0.17365, 0.0, 0.98481],
    RIG_MAP["L_Hand"]: [0.0, 0.0, 0.0, 1.0],
    RIG_MAP["R_Hand"]: [0.0, 0.0, 0.0, 1.0],
}

# Fill other joints with identity in rest pose
for finger_list in [RIG_MAP[f"L_{f}"] + RIG_MAP[f"R_{f}"] for f in ["Thumb", "Index", "Middle", "Ring", "Little"]]:
    for bone in finger_list:
        REST_POSE[bone] = [0.0, 0.0, 0.0, 1.0]

def map_single_frame(frame_keypoints):
    """
    Maps a single frame's keypoints to bone rotations. Falls back to REST_POSE if landmarks are missing.
    """
    pose = frame_keypoints.get("pose", [])
    left_hand = frame_keypoints.get("left_hand", [])
    right_hand = frame_keypoints.get("right_hand", [])
    
    # Check if landmarks are empty/invalid
    is_pose_valid = len(pose) > 16 and np.linalg.norm(pose[11][:3]) > 1e-4
    is_l_hand_valid = len(left_hand) > 0 and np.linalg.norm(left_hand[0]) > 1e-4
    is_r_hand_valid = len(right_hand) > 0 and np.linalg.norm(right_hand[0]) > 1e-4
    
    # Initialize with copy of rest pose
    rotations = REST_POSE.copy()
    
    if not is_pose_valid and not is_l_hand_valid and not is_r_hand_valid:
        return rotations

    def get_pose_pt(idx):
        if idx >= len(pose):
            return np.zeros(3)
        pt = pose[idx]
        return np.array([-pt[0], -pt[1], -pt[2]])
        
    def get_hand_pt(hand_list, idx):
        if idx >= len(hand_list):
            return np.zeros(3)
        pt = hand_list[idx]
        return np.array([-pt[0], -pt[1], -pt[2]])

    # 1. Map Left Arm
    p_l_shoulder = get_pose_pt(11)
    p_l_elbow = get_pose_pt(13)
    p_l_wrist = get_pose_pt(15)
    d_l_arm_default = np.array([1.0, 0.0, 0.0])
    
    q_l_upper = REST_POSE[RIG_MAP["L_UpperArm"]]
    v_l_upper = p_l_elbow - p_l_shoulder
    if np.linalg.norm(v_l_upper) > 1e-4:
        q_l_upper = rotation_between_vectors(d_l_arm_default, v_l_upper)
        rotations[RIG_MAP["L_UpperArm"]] = q_l_upper
        
    q_l_lower = REST_POSE[RIG_MAP["L_LowerArm"]]
    v_l_lower = p_l_wrist - p_l_elbow
    if np.linalg.norm(v_l_lower) > 1e-4:
        v_l_lower_local = q_rotate_vector(q_conjugate(q_l_upper), v_l_lower)
        q_l_lower = rotation_between_vectors(d_l_arm_default, v_l_lower_local)
        rotations[RIG_MAP["L_LowerArm"]] = q_l_lower
        
    p_l_hand_wrist = get_hand_pt(left_hand, 0)
    p_l_hand_middle_base = get_hand_pt(left_hand, 9)
    q_l_hand = REST_POSE[RIG_MAP["L_Hand"]]
    q_l_arm_cum = q_multiply(q_l_upper, q_l_lower)
    
    if np.linalg.norm(p_l_hand_middle_base - p_l_hand_wrist) > 1e-4:
        v_l_hand = p_l_hand_middle_base - p_l_hand_wrist
        v_l_hand_local = q_rotate_vector(q_conjugate(q_l_arm_cum), v_l_hand)
        q_l_hand = rotation_between_vectors(d_l_arm_default, v_l_hand_local)
        rotations[RIG_MAP["L_Hand"]] = q_l_hand
        
    q_l_hand_cum = q_multiply(q_l_arm_cum, q_l_hand)

    # 2. Map Right Arm
    p_r_shoulder = get_pose_pt(12)
    p_r_elbow = get_pose_pt(14)
    p_r_wrist = get_pose_pt(16)
    d_r_arm_default = np.array([-1.0, 0.0, 0.0])
    
    q_r_upper = REST_POSE[RIG_MAP["R_UpperArm"]]
    v_r_upper = p_r_elbow - p_r_shoulder
    if np.linalg.norm(v_r_upper) > 1e-4:
        q_r_upper = rotation_between_vectors(d_r_arm_default, v_r_upper)
        rotations[RIG_MAP["R_UpperArm"]] = q_r_upper
        
    q_r_lower = REST_POSE[RIG_MAP["R_LowerArm"]]
    v_r_lower = p_r_wrist - p_r_elbow
    if np.linalg.norm(v_r_lower) > 1e-4:
        v_r_lower_local = q_rotate_vector(q_conjugate(q_r_upper), v_r_lower)
        q_r_lower = rotation_between_vectors(d_r_arm_default, v_r_lower_local)
        rotations[RIG_MAP["R_LowerArm"]] = q_r_lower
        
    p_r_hand_wrist = get_hand_pt(right_hand, 0)
    p_r_hand_middle_base = get_hand_pt(right_hand, 9)
    q_r_hand = REST_POSE[RIG_MAP["R_Hand"]]
    q_r_arm_cum = q_multiply(q_r_upper, q_r_lower)
    
    if np.linalg.norm(p_r_hand_middle_base - p_r_hand_wrist) > 1e-4:
        v_r_hand = p_r_hand_middle_base - p_r_hand_wrist
        v_r_hand_local = q_rotate_vector(q_conjugate(q_r_arm_cum), v_r_hand)
        q_r_hand = rotation_between_vectors(d_r_arm_default, v_r_hand_local)
        rotations[RIG_MAP["R_Hand"]] = q_r_hand
        
    q_r_hand_cum = q_multiply(q_r_arm_cum, q_r_hand)

    # 3. Map Fingers
    fingers_mapping = [
        ("Thumb", [1, 2, 3, 4]),
        ("Index", [5, 6, 7, 8]),
        ("Middle", [9, 10, 11, 12]),
        ("Ring", [13, 14, 15, 16]),
        ("Little", [17, 18, 19, 20])
    ]
    
    if is_l_hand_valid:
        for f_name, indices in fingers_mapping:
            bone_list = RIG_MAP[f"L_{f_name}"]
            q_cum_parent = q_l_hand_cum
            for segment_idx in range(min(3, len(bone_list))):
                bone_name = bone_list[segment_idx]
                pt_start = get_hand_pt(left_hand, indices[segment_idx])
                pt_end = get_hand_pt(left_hand, indices[segment_idx + 1])
                v_segment = pt_end - pt_start
                
                q_seg = [0.0, 0.0, 0.0, 1.0]
                if np.linalg.norm(v_segment) > 1e-4:
                    v_seg_local = q_rotate_vector(q_conjugate(q_cum_parent), v_segment)
                    q_seg = rotation_between_vectors(d_l_arm_default, v_seg_local)
                
                rotations[bone_name] = q_seg
                q_cum_parent = q_multiply(q_cum_parent, q_seg)

    if is_r_hand_valid:
        for f_name, indices in fingers_mapping:
            bone_list = RIG_MAP[f"R_{f_name}"]
            q_cum_parent = q_r_hand_cum
            for segment_idx in range(min(3, len(bone_list))):
                bone_name = bone_list[segment_idx]
                pt_start = get_hand_pt(right_hand, indices[segment_idx])
                pt_end = get_hand_pt(right_hand, indices[segment_idx + 1])
                v_segment = pt_end - pt_start
                
                q_seg = [0.0, 0.0, 0.0, 1.0]
                if np.linalg.norm(v_segment) > 1e-4:
                    v_seg_local = q_rotate_vector(q_conjugate(q_cum_parent), v_segment)
                    q_seg = rotation_between_vectors(d_r_arm_default, v_seg_local)
                
                rotations[bone_name] = q_seg
                q_cum_parent = q_multiply(q_cum_parent, q_seg)
                
    return rotations

def map_captions_to_animation(caption_blocks, fps=30):
    """
    Maps list of caption blocks to a single continuous timeline synced with video playback.
    caption_blocks: List of dicts, each containing:
        - start: float
        - end: float
        - words: List of dicts, each containing:
            - word: string
            - source: string ("landmarks", "videos", "csltr", "fingerspelling", "unmatched")
            - keypoints: List of frames
            - letters: List of letter entries (if fingerspelling)
    """
    time_per_frame = 1.0 / fps
    final_frames = []
    
    # Setup intervals
    letter_hold_ms = 350
    letter_interp_ms = 100
    word_interp_ms = 200
    blend_rest_ms = 300 # blend to/from rest pose
    
    def get_interpolated_frames(rotations_start, rotations_end, duration_s):
        frames_count = max(1, int(round(duration_s / time_per_frame)))
        interp_list = []
        for i in range(frames_count):
            t = i / float(frames_count)
            all_bones = set(rotations_start.keys()).union(set(rotations_end.keys()))
            frame_rot = {}
            for bone in all_bones:
                q1 = rotations_start.get(bone, [0.0, 0.0, 0.0, 1.0])
                q2 = rotations_end.get(bone, [0.0, 0.0, 0.0, 1.0])
                frame_rot[bone] = q_nlerp(q1, q2, t)
            interp_list.append(frame_rot)
        return interp_list

    # 1. Process each caption block to generate its local sign animation sequence
    block_animations = []
    for block in caption_blocks:
        start_time = block["start"]
        end_time = block["end"]
        words = block.get("words", [])
        
        # Build raw word sequences for this block
        computed_segments = []
        for word_entry in words:
            source = word_entry.get("source", "unmatched")
            kps = word_entry.get("keypoints", [])
            
            if source == "unmatched" or not kps:
                # Mock rest pose for unmatched words (brief hold of 0.5s)
                computed_segments.append({
                    "poses": [REST_POSE] * int(0.5 / time_per_frame)
                })
                continue
                
            if source == "fingerspelling":
                letters = word_entry.get("letters", [])
                letter_poses = []
                for letter_entry in letters:
                    let_kps = letter_entry.get("keypoints", [])
                    pose = map_single_frame(let_kps[0]) if let_kps else REST_POSE.copy()
                    letter_poses.append(pose)
                
                if not letter_poses:
                    continue
                    
                poses_seq = []
                num_hold_frames = int(round((letter_hold_ms / 1000.0) / time_per_frame))
                for idx, pose in enumerate(letter_poses):
                    poses_seq.extend([pose] * num_hold_frames)
                    if idx < len(letter_poses) - 1:
                        interp_poses = get_interpolated_frames(pose, letter_poses[idx+1], letter_interp_ms / 1000.0)
                        poses_seq.extend(interp_poses)
                computed_segments.append({"poses": poses_seq})
                
            else:
                poses_seq = [map_single_frame(f) for f in kps]
                computed_segments.append({"poses": poses_seq})
                
        # Stitch word segments in this block together
        block_poses = []
        for i, segment in enumerate(computed_segments):
            poses = segment["poses"]
            block_poses.extend(poses)
            if i < len(computed_segments) - 1:
                next_poses = computed_segments[i+1]["poses"]
                if next_poses:
                    interp_poses = get_interpolated_frames(poses[-1], next_poses[0], word_interp_ms / 1000.0)
                    block_poses.extend(interp_poses)
                    
        block_animations.append({
            "start": start_time,
            "end": end_time,
            "poses": block_poses
        })
        
    if not block_animations:
        # Return empty animation with 1 rest frame
        return {
            "fps": fps,
            "duration": 1.0,
            "frames": [{"time": 0.0, "rotations": {k: [round(x, 5) for x in q] for k, q in REST_POSE.items()}}]
        }
        
    # 2. Stitch blocks on a global timeline with REST_POSE gaps
    # Max time is the end of the last caption block
    max_time = block_animations[-1]["end"]
    total_frames = int(round(max_time / time_per_frame)) + 30 # pad 1 sec at the end
    
    # Initialize timeline with None
    timeline_poses = [None] * total_frames
    
    for anim in block_animations:
        start_idx = int(round(anim["start"] / time_per_frame))
        poses = anim["poses"]
        
        # Place block poses on the timeline
        for offset, pose in enumerate(poses):
            idx = start_idx + offset
            if idx < len(timeline_poses):
                timeline_poses[idx] = pose
                
    # 3. Fill gaps with REST_POSE and blend transitions
    i = 0
    while i < len(timeline_poses):
        if timeline_poses[i] is None:
            # We are in a gap. Find where the gap ends.
            gap_start = i
            while i < len(timeline_poses) and timeline_poses[i] is None:
                i += 1
            gap_end = i # index of next active pose (or end of list)
            
            # Set center of gap to REST_POSE
            # Blend out from previous pose, and blend in to next pose
            blend_frames = int(round((blend_rest_ms / 1000.0) / time_per_frame))
            
            # Left blend boundary
            prev_pose = timeline_poses[gap_start - 1] if gap_start > 0 else REST_POSE
            # Right blend boundary
            next_pose = timeline_poses[gap_end] if gap_end < len(timeline_poses) else REST_POSE
            
            # Populate gap
            for k in range(gap_start, gap_end):
                dist_from_prev = k - gap_start + 1
                dist_to_next = gap_end - k
                
                if dist_from_prev <= blend_frames and dist_to_next <= blend_frames:
                    # Very short gap, blend directly between prev_pose and next_pose
                    factor = float(dist_from_prev) / (gap_end - gap_start)
                    timeline_poses[k] = {bone: q_nlerp(prev_pose.get(bone, [0.0,0.0,0.0,1.0]), next_pose.get(bone, [0.0,0.0,0.0,1.0]), factor) for bone in REST_POSE}
                elif dist_from_prev <= blend_frames:
                    # Blending out to REST_POSE
                    factor = float(dist_from_prev) / blend_frames
                    timeline_poses[k] = {bone: q_nlerp(prev_pose.get(bone, [0.0,0.0,0.0,1.0]), REST_POSE[bone], factor) for bone in REST_POSE}
                elif dist_to_next <= blend_frames:
                    # Blending in from REST_POSE
                    factor = 1.0 - (float(dist_to_next) / blend_frames)
                    timeline_poses[k] = {bone: q_nlerp(REST_POSE[bone], next_pose.get(bone, [0.0,0.0,0.0,1.0]), factor) for bone in REST_POSE}
                else:
                    # Stable rest pose in the middle of gap
                    timeline_poses[k] = REST_POSE
        else:
            i += 1
            
    # Convert timeline to final output format
    for frame_idx, pose in enumerate(timeline_poses):
        t = frame_idx * time_per_frame
        final_frames.append({
            "time": round(t, 4),
            "rotations": {k: [round(x, 5) for x in q] for k, q in pose.items()}
        })
        
    return {
        "fps": fps,
        "duration": round(len(timeline_poses) * time_per_frame, 4),
        "frames": final_frames
    }

# Retained for backwards compatibility/testing
def map_keypoints_to_animation(pipeline_output_words, fps=30):
    # Fallback/mock single caption block starting at 0
    mock_block = {
        "start": 0.0,
        "end": sum([len(w.get("keypoints", [])) * (1.0/fps) if w.get("source") != "fingerspelling" else 1.5 for w in pipeline_output_words]),
        "words": pipeline_output_words
    }
    return map_captions_to_animation([mock_block], fps)

if __name__ == "__main__":
    print("=== TESTING RIG MAPPER ===")
    print("Resolved dynamic bone mapping:")
    for k, v in RIG_MAP.items():
        print(f"  {k}: {v}")
