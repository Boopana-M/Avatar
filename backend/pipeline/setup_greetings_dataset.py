import os
import subprocess
import zipfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INCLUDE_DIR = os.path.join(BASE_DIR, "datasets", "include")

os.makedirs(INCLUDE_DIR, exist_ok=True)

zip1_path = os.path.join(INCLUDE_DIR, "Greetings_1of2.zip")
zip2_path = os.path.join(INCLUDE_DIR, "Greetings_2of2.zip")

url1 = "https://zenodo.org/records/4010759/files/Greetings_1of2.zip?download=1"
url2 = "https://zenodo.org/records/4010759/files/Greetings_2of2.zip?download=1"

def download_bits(url, dest_path):
    print(f"[Dataset Setup] Downloading from {url} to {dest_path} using BITS...")
    # Escape single quotes in path for powershell
    escaped_dest = dest_path.replace("'", "''")
    cmd = f"Start-BitsTransfer -Source '{url}' -Destination '{escaped_dest}'"
    
    result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[Dataset Setup] BITS download completed successfully.")
        return True
    else:
        print(f"[Dataset Setup] BITS download failed. Error:\n{result.stderr}")
        return False

def extract_zip(zip_path):
    print(f"[Dataset Setup] Extracting {zip_path} to {INCLUDE_DIR}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(INCLUDE_DIR)
        print(f"[Dataset Setup] Extraction complete. Deleting zip file...")
        os.remove(zip_path)
        print(f"[Dataset Setup] Deleted zip file: {zip_path}")
        return True
    except Exception as e:
        print(f"[Dataset Setup] Extraction failed for {zip_path}: {e}")
        return False

def main():
    print("=" * 60)
    print("AUTOMATED GREETINGS DATASET SETUP SCRIPT")
    print("=" * 60)
    print(f"Target Directory: {INCLUDE_DIR}\n")
    
    # --- Step 1: Handle Greetings_1of2.zip ---
    # If BITS download is still active or already finished
    if os.path.exists(zip1_path):
        print(f"[Dataset Setup] Greetings_1of2.zip already downloaded.")
        extract_zip(zip1_path)
    else:
        # Check if the BITS download is currently running
        # We look for any BITS jobs with the destination containing 'Greetings_1of2.zip'
        cmd = "Get-BitsTransfer | Where-Object { $_.FileList | Where-Object { $_.LocalName -like '*Greetings_1of2.zip*' } }"
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
        if "Greetings_1of2.zip" in res.stdout:
            print("[Dataset Setup] BITS transfer for Greetings_1of2.zip is currently active. Waiting for it to finish...")
            # Run PowerShell synchronously to complete the active job
            wait_cmd = "Get-BitsTransfer | Where-Object { $_.FileList | Where-Object { $_.LocalName -like '*Greetings_1of2.zip*' } } | Wait-BitsTransfer"
            subprocess.run(["powershell", "-Command", wait_cmd])
            print("[Dataset Setup] Active BITS download finished.")
            # BITS downloads are renamed after completion, check if it's there
            if os.path.exists(zip1_path):
                extract_zip(zip1_path)
            else:
                # If wait failed or was interrupted, redownload
                if download_bits(url1, zip1_path):
                    extract_zip(zip1_path)
        else:
            # Not running and doesn't exist, download it
            if download_bits(url1, zip1_path):
                extract_zip(zip1_path)

    # --- Step 2: Handle Greetings_2of2.zip ---
    if os.path.exists(zip2_path):
        print(f"\n[Dataset Setup] Greetings_2of2.zip already downloaded.")
        extract_zip(zip2_path)
    else:
        print(f"\n[Dataset Setup] Starting download for Greetings_2of2.zip...")
        if download_bits(url2, zip2_path):
            extract_zip(zip2_path)
            
    print("\n" + "=" * 60)
    print("SETUP COMPLETE - GREETINGS CATEGORIES ARE READY!")
    print("=" * 60)

if __name__ == "__main__":
    main()
