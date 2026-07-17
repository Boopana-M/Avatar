import os
import sys
from pygltflib import GLTF2

def verify_avatar():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    
    # Check for both avatar.vrm and Avatar.vrm
    vrm_path = os.path.join(project_root, "backend", "models", "avatar.vrm")
    if not os.path.exists(vrm_path):
        vrm_path = os.path.join(project_root, "backend", "models", "Avatar.vrm")
        
    print("=== AVATAR RIG VERIFICATION ===")
    print(f"Checking VRM file at: {vrm_path}\n")
    
    if not os.path.exists(vrm_path):
        print(f"FAIL: avatar.vrm file not found at expected paths.")
        sys.exit(1)
        
    try:
        # VRM files are binary glTF (GLB), but since the extension is .vrm, 
        # load() may try to parse it as text JSON. We force load_binary() here.
        gltf = GLTF2().load_binary(vrm_path)
    except Exception as e:
        print(f"FAIL: Failed to load VRM file: {e}")
        sys.exit(1)
        
    nodes = gltf.nodes
    print(f"Loaded VRM. Found {len(nodes)} nodes.")
    
    # We print every bone/node name found
    print("\n--- Bone/Node List ---")
    node_names = []
    for idx, node in enumerate(nodes):
        name = node.name
        if name:
            node_names.append(name)
            print(f"  [{idx}]: {name}")
            
    # Check for confirmed naming patterns:
    # J_Bip_L_ / J_Bip_R_ combined with finger keywords (Thumb, Index, Middle, Ring, Little)
    fingers = ["Thumb", "Index", "Middle", "Ring", "Little"]
    left_hand_segments = {f: 0 for f in fingers}
    right_hand_segments = {f: 0 for f in fingers}
    
    for name in node_names:
        # Check Left hand
        if name.startswith("J_Bip_L_"):
            # Check which finger it is
            for f in fingers:
                if f in name:
                    left_hand_segments[f] += 1
        # Check Right hand
        elif name.startswith("J_Bip_R_"):
            for f in fingers:
                if f in name:
                    right_hand_segments[f] += 1
                    
    print("\n--- Summary of Finger Bone Segments ---")
    print("Left Hand Finger Segments:")
    for f, count in left_hand_segments.items():
        print(f"  {f}: {count}")
    print("Right Hand Finger Segments:")
    for f, count in right_hand_segments.items():
        print(f"  {f}: {count}")
        
    # Check if all fingers on both hands have at least 3 segments
    left_pass = all(count >= 3 for count in left_hand_segments.values())
    right_pass = all(count >= 3 for count in right_hand_segments.values())
    
    if left_pass and right_pass:
        print("\nPASS: finger bones found")
        sys.exit(0)
    else:
        print("\nFAIL: no finger bones found — this rig cannot animate sign language, get a different export")
        print("Required: at least 3 finger-bone segments per finger on both J_Bip_L_ and J_Bip_R_ prefixed hands.")
        sys.exit(1)

if __name__ == "__main__":
    verify_avatar()
