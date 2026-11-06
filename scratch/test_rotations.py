import requests

url = "http://localhost:8000/translate/status?video_id=9PXluC2FMD0"
res = requests.get(url)
data = res.json()
blocks = data.get("new_blocks", [])
if blocks:
    first_block = blocks[0]
    frames = first_block.get("frames", [])
    print("Block Index:", first_block["block_idx"])
    print("Total Frames:", len(frames))
    if len(frames) > 10:
        # print J_Bip_R_UpperArm rotations for frames 0, 5, 10, 20
        indices_to_check = [0, 5, 10, 20, 50, 100]
        for idx in indices_to_check:
            if idx < len(frames):
                f = frames[idx]
                rot = f.get("rotations", {})
                r_upper = rot.get("J_Bip_R_UpperArm")
                r_lower = rot.get("J_Bip_R_LowerArm")
                r_hand = rot.get("J_Bip_R_Hand")
                print(f"Frame {idx} (time: {f['time']}):")
                print(f"  J_Bip_R_UpperArm: {r_upper}")
                print(f"  J_Bip_R_LowerArm: {r_lower}")
                print(f"  J_Bip_R_Hand:     {r_hand}")
