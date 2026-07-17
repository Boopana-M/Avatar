import os
import re
import sys
from nltk.stem import WordNetLemmatizer

# Initialize lemmatizer
lemmatizer = WordNetLemmatizer()

def normalize(label):
    """
    Normalizes dataset labels and gloss words identically:
    Converts to uppercase, strips, replaces underscores/hyphens/newlines with spaces, and collapses multiple spaces.
    """
    if not label:
        return ""
    # Convert to string and uppercase
    s = str(label).upper().strip()
    # Replace hyphens, underscores, and whitespace sequences with a single space
    s = re.sub(r'[\s_-]+', ' ', s)
    return s

def build_dataset_index(data_dir):
    """
    Scans the data directories and builds an index mapping normalized words to their sources and files.
    Returns:
        dict: { normalized_word: [ { 'source': str, 'files': [str], 'matched_word': str } ] }
    """
    index = {}
    
    # 1. Word-level ISL Landmarks (isl-words-landmarks)
    landmarks_dir = os.path.join(data_dir, "isl-words-landmarks", "ProcessedData_vivit")
    if os.path.exists(landmarks_dir):
        for folder in os.listdir(landmarks_dir):
            folder_path = os.path.join(landmarks_dir, folder)
            if os.path.isdir(folder_path):
                norm = normalize(folder)
                if norm:
                    # Find all .MOV files
                    mov_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(".mov")]
                    if mov_files:
                        index.setdefault(norm, []).append({
                            "source": "landmarks",
                            "matched_word": norm,
                            "files": sorted(mov_files)
                        })
                        
    # 2. Word-level ISL videos (isl-word-videos)
    videos_dir = os.path.join(data_dir, "isl-word-videos")
    folder_to_word = {
        "1": "hello",
        "2": "bye",
        "3": "yes",
        "4": "no",
        "5": "good",
        "6": "morning",
        "7": "welcome",
        "8": "thank you",
        "9": "work",
        "10": "nice",
        "11": "house"
    }
    if os.path.exists(videos_dir):
        for num_folder in os.listdir(videos_dir):
            if num_folder in folder_to_word:
                word = folder_to_word[num_folder]
                norm = normalize(word)
                num_path = os.path.join(videos_dir, num_folder)
                if os.path.isdir(num_path):
                    mp4_files = []
                    for root, dirs, files in os.walk(num_path):
                        for f in files:
                            if f.lower().endswith(".mp4"):
                                mp4_files.append(os.path.join(root, f))
                    if mp4_files:
                        index.setdefault(norm, []).append({
                            "source": "videos",
                            "matched_word": norm,
                            "files": sorted(mp4_files)
                        })
                        
    # 3. ISL-CSLTR Word Level Frames (isl-csltr)
    csltr_dir = os.path.join(data_dir, "isl-csltr", "ISL_CSLRT_Corpus", "ISL_CSLRT_Corpus", "Frames_Word_Level")
    if os.path.exists(csltr_dir):
        for folder in os.listdir(csltr_dir):
            folder_path = os.path.join(csltr_dir, folder)
            if os.path.isdir(folder_path):
                norm = normalize(folder)
                if norm:
                    # Find all jpg/png frames
                    img_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
                    if img_files:
                        index.setdefault(norm, []).append({
                            "source": "csltr",
                            "matched_word": norm,
                            "files": sorted(img_files)
                        })
                        
    return index

def get_fingerspelling_letter_path(letter, fingerspelling_dir):
    """
    Returns the path to a static image representing the given letter.
    Falls back to 'a' if the letter folder does not exist.
    """
    base_gesture_dir = os.path.join(fingerspelling_dir, "dataset - Gesture Speech")
    letter_dir = os.path.join(base_gesture_dir, letter.lower())
    
    # Fallback if specific letter folder doesn't exist
    if not os.path.exists(letter_dir) or not os.path.isdir(letter_dir):
        letter_dir = os.path.join(base_gesture_dir, "a")
        
    if os.path.exists(letter_dir):
        files = sorted([f for f in os.listdir(letter_dir) if f.lower().endswith((".jpg", ".png", ".jpeg"))])
        if files:
            return os.path.join(letter_dir, files[0])
            
    return None

def lookup_sign(gloss_word, dataset_index, fingerspelling_dir):
    """
    Performs three-tier lookup for a gloss word.
    Returns a dict with match details, or list of dicts for fingerspelled letters.
    """
    norm_word = normalize(gloss_word)
    if not norm_word:
        return None
        
    # TIER 1: Exact Match
    if norm_word in dataset_index:
        # Prioritize sources: landmarks > videos > csltr
        matches = dataset_index[norm_word]
        matches_by_src = {m["source"]: m for m in matches}
        for src in ["landmarks", "videos", "csltr"]:
            if src in matches_by_src:
                match = matches_by_src[src]
                return {
                    "word": gloss_word,
                    "tier": 1,
                    "source": match["source"],
                    "matched_word": match["matched_word"],
                    "files": match["files"]
                }
                
    # TIER 2: Lemmatization Match
    lemma = normalize(lemmatizer.lemmatize(norm_word.lower()))
    if lemma in dataset_index:
        matches = dataset_index[lemma]
        matches_by_src = {m["source"]: m for m in matches}
        for src in ["landmarks", "videos", "csltr"]:
            if src in matches_by_src:
                match = matches_by_src[src]
                return {
                    "word": gloss_word,
                    "tier": 2,
                    "source": match["source"],
                    "matched_word": match["matched_word"],
                    "files": match["files"]
                }
                
    # TIER 3: Fingerspelling Fallback
    # Split the word into individual letters
    letters_data = []
    for char in norm_word:
        if char.isalnum():  # skip non-alphanumeric chars
            img_path = get_fingerspelling_letter_path(char, fingerspelling_dir)
            if img_path:
                letters_data.append({
                    "word": char,
                    "tier": 3,
                    "source": "fingerspelling",
                    "matched_word": char,
                    "files": [img_path]
                })
                
    if letters_data:
        return {
            "word": gloss_word,
            "tier": 3,
            "source": "fingerspelling",
            "matched_word": norm_word,
            "letters": letters_data
        }
        
    return {
        "word": gloss_word,
        "tier": 3,
        "source": "unmatched",
        "matched_word": norm_word,
        "files": []
    }

if __name__ == "__main__":
    # Base directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    data_dir = os.path.join(project_root, "data")
    fingerspelling_dir = os.path.join(data_dir, "fingerspelling")
    
    print("=== TESTING THREE-TIER SIGN LOOKUP ===")
    print("Building dataset index...")
    index = build_dataset_index(data_dir)
    print(f"Index built. Total unique normalized words: {len(index)}")
    
    # Required output representation for Step 5: print 30 normalized labels next to 10 gloss words
    print("\n--- FIRST 30 NORMALIZED LABELS IN INDEX ---")
    sorted_labels = sorted(list(index.keys()))
    for idx, label in enumerate(sorted_labels[:30], 1):
        print(f"  {idx:2d}. {label}")
        
    test_gloss_words = [
        "HELLO", "BYE", "DOG", "DOGS", "ANIMAL", "AFTERNOON", "TOMORROW", "CAT", "X", "XYZ"
    ]
    
    print("\n--- 10 GLOSS WORDS LOOKUP TEST ---")
    for word in test_gloss_words:
        res = lookup_sign(word, index, fingerspelling_dir)
        if res["tier"] == 3 and "letters" in res:
            letters_desc = ", ".join([f"{l['word']} (from {l['files'][0][-30:]})" for l in res["letters"]])
            print(f"Word: '{word}' -> Tier 3 (Fingerspelling): {letters_desc}")
        elif res["source"] == "unmatched":
            print(f"Word: '{word}' -> Unmatched")
        else:
            first_file_snippet = res["files"][0][-50:] if res["files"] else "None"
            print(f"Word: '{word}' -> Tier {res['tier']} ({res['source']}), Matched: '{res['matched_word']}', Files count: {len(res['files'])}, Sample file: ...{first_file_snippet}")
