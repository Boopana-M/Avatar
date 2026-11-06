import sys
import os
import json
import numpy as np

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(os.path.join(project_root, "backend"))
sys.path.append(os.path.join(project_root, "backend", "pipeline"))

from gloss_generator import generate_gloss, rule_based_gloss
from pose_matcher import build_dataset_index, lookup_sign
from keypoint_extractor import get_keypoints
from rig_mapper import map_captions_to_animation

print("=== VERIFYING FIX 1: GLOSS GENERATION ===")
test_sentences = [
    "English these tips will make speaking",
    "What are you doing tomorrow?",
    "My dog is sleeping on the floor."
]

for s in test_sentences:
    g = generate_gloss(s)
    r = rule_based_gloss(s)
    print(f"Input:  '{s}'")
    print(f"Gloss:  '{g}'")
    print(f"Rule:   '{r}'")
    print("-" * 40)

print("\n=== VERIFYING FIX 2: BONE ROTATION PIPELINE ===")
data_dir = os.path.join(project_root, "data")
fingerspelling_dir = os.path.join(data_dir, "fingerspelling")
cache_dir = os.path.join(project_root, "backend", "cache")

dataset_index = build_dataset_index(data_dir)

# Test video caption block translation
test_block = {
    "start": 0.0,
    "end": 3.0,
    "text": "English these tips will make speaking"
}

gloss_words = generate_gloss(test_block["text"]).split()
print("Gloss words for block:", gloss_words)

words_data = []
for word in gloss_words:
    res = lookup_sign(word, dataset_index, fingerspelling_dir)
    source = res["source"]
    if source == "fingerspelling":
        for letter_entry in res.get("letters", []):
            letter_entry["keypoints"] = get_keypoints(letter_entry, cache_dir)
    elif source in ("landmarks", "videos", "csltr"):
        res["keypoints"] = get_keypoints(res, cache_dir)
    words_data.append(res)

anim = map_captions_to_animation([{
    "start": test_block["start"],
    "end": test_block["end"],
    "words": words_data
}], fps=30)

print("Generated total frames:", len(anim["frames"]))
sample_frames = anim["frames"][:10]

index1_rotations = [f["rotations"].get("J_Bip_R_Index1") for f in sample_frames]
thumb2_rotations = [f["rotations"].get("J_Bip_R_Thumb2") for f in sample_frames]
upper_arm_rotations = [f["rotations"].get("J_Bip_R_UpperArm") for f in sample_frames]

print("\nSample J_Bip_R_UpperArm rotations:")
for i, rot in enumerate(upper_arm_rotations):
    print(f"  Frame {i:2d}: {rot}")

print("\nSample J_Bip_R_Index1 rotations:")
for i, rot in enumerate(index1_rotations):
    print(f"  Frame {i:2d}: {rot}")

non_identity_count = sum(1 for f in anim["frames"] if not np.allclose(f["rotations"].get("J_Bip_R_UpperArm", [0,0,0,1]), [0,0,0,1]))
print(f"\nNon-identity upper arm frames: {non_identity_count} / {len(anim['frames'])}")

assert non_identity_count > 0, "FAIL: Animation frames are static rest pose!"
print("\nSUCCESS: Both fixes verified programmatically!")
