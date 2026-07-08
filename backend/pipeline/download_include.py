import os
import zipfile
import urllib.request
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INCLUDE_DIR = os.path.join(BASE_DIR, "datasets", "include")

os.makedirs(INCLUDE_DIR, exist_ok=True)

files_to_download = {
    "Greetings_1of2.zip": "https://zenodo.org/records/4010759/files/Greetings_1of2.zip?download=1",
    "Greetings_2of2.zip": "https://zenodo.org/records/4010759/files/Greetings_2of2.zip?download=1"
}

def report_progress(block_num, block_size, total_size):
    global last_time
    read_so_far = block_num * block_size
    if total_size > 0:
        percent = read_so_far * 1e2 / total_size
        mb_so_far = read_so_far / (1024 * 1024)
        total_mb = total_size / (1024 * 1024)
        
        current_time = time.time()
        # Log progress every 2 seconds to not flood the logs
        if current_time - last_time > 2.0 or read_so_far >= total_size:
            print(f"Downloaded: {mb_so_far:.2f} MB / {total_mb:.2f} MB ({percent:.1f}%)")
            last_time = current_time
    else:
        print(f"Downloaded: {read_so_far / (1024 * 1024):.2f} MB")

def download_and_extract():
    global last_time
    print("=" * 60)
    print("STARTING DOWNLOAD AND EXTRACTION OF GREETINGS DATASET")
    print("=" * 60)
    print(f"Target Directory: {INCLUDE_DIR}\n")
    
    for filename, url in files_to_download.items():
        zip_path = os.path.join(INCLUDE_DIR, filename)
        
        print(f"Downloading {filename}...")
        print(f"URL: {url}")
        
        last_time = time.time()
        try:
            urllib.request.urlretrieve(url, zip_path, reporthook=report_progress)
            print(f"\nSuccessfully downloaded {filename}.")
            
            print(f"Extracting {filename}...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(INCLUDE_DIR)
            print(f"Finished extracting {filename}.")
            
            print(f"Deleting zip file to save space: {filename}")
            os.remove(zip_path)
            print(f"Deleted {filename}.\n")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            if os.path.exists(zip_path):
                os.remove(zip_path)
            return False
            
    print("=" * 60)
    print("GREETINGS DATASET READY!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    download_and_extract()
