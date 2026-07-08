import os

# Define the base workspace and datasets path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")

# Target folders for datasets
folders = {
    "ISLTranslate": os.path.join(DATASETS_DIR, "isltranslate"),
    "iSign": os.path.join(DATASETS_DIR, "isign"),
    "INCLUDE": os.path.join(DATASETS_DIR, "include"),
    "ISL-CSLTR": os.path.join(DATASETS_DIR, "isl-csltr")
}

def verify_datasets():
    print("=" * 60)
    print("ISL AVATAR EXTENSION - DATASET VERIFICATION")
    print("=" * 60)
    print(f"Base Directory: {BASE_DIR}")
    print(f"Datasets Root:  {DATASETS_DIR}\n")
    
    all_ok = True
    for name, path in folders.items():
        exists = os.path.exists(path)
        if not exists:
            print(f"[-] {name:<15}: Folder does NOT exist!")
            print(f"    Expected path: {path}")
            all_ok = False
        else:
            # Count files in the folder (recursively)
            file_count = 0
            dir_count = 0
            for root, dirs, files in os.walk(path):
                file_count += len(files)
                dir_count += len(dirs)
            
            if file_count == 0:
                print(f"[!] {name:<15}: Folder exists but is EMPTY!")
                print(f"    Path: {path}")
                all_ok = False
            else:
                print(f"[+] {name:<15}: OK ({file_count} files, {dir_count} directories)")
                print(f"    Path: {path}")
    
    print("=" * 60)
    if all_ok:
        print("SUCCESS: All datasets are verified successfully!")
    else:
        print("WARNING: Some datasets are missing or empty. Please download them.")
    print("=" * 60)

if __name__ == "__main__":
    verify_datasets()
