import os
import sys

def verify_datasets():
    # Base directory is the workspace root (two levels up from backend/verify)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    data_dir = os.path.join(base_dir, "data")
    
    datasets = {
        "Word-level ISL Landmarks (isl-words-landmarks)": "isl-words-landmarks",
        "Word-level ISL Videos (isl-word-videos)": "isl-word-videos",
        "ISL-CSLTR (isl-csltr)": "isl-csltr",
        "Fingerspelling (fingerspelling)": "fingerspelling"
    }
    
    print("=== ISL AVATAR DATASET VERIFICATION ===")
    print(f"Project root directory: {base_dir}")
    print(f"Data directory: {data_dir}\n")
    
    all_pass = True
    
    for name, folder_name in datasets.items():
        folder_path = os.path.join(data_dir, folder_name)
        print(f"Checking {name} in {folder_path}...")
        
        if not os.path.exists(folder_path):
            print(f"  [FAIL] Directory does not exist.")
            all_pass = False
            continue
            
        if not os.path.isdir(folder_path):
            print(f"  [FAIL] Path exists but is not a directory.")
            all_pass = False
            continue
            
        # Count files in the directory tree
        file_count = 0
        for root, dirs, files in os.walk(folder_path):
            file_count += len(files)
            
        if file_count == 0:
            print(f"  [FAIL] Directory is empty.")
            all_pass = False
        else:
            print(f"  [PASS] Found {file_count} files.")
            
    print("\n=======================================")
    if all_pass:
        print("OVERALL RESULT: PASS - All datasets verified and present.")
        sys.exit(0)
    else:
        print("OVERALL RESULT: FAIL - Some datasets are missing or empty.")
        sys.exit(1)

if __name__ == "__main__":
    verify_datasets()
