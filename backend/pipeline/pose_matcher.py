import os
import re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INCLUDE_DIR = os.path.join(BASE_DIR, "datasets", "include")

# Global dataframe cache
_metadata_df = None

def load_metadata():
    """
    Loads and concatenates the train, test, and val parquet metadata files for INCLUDE.
    """
    global _metadata_df
    if _metadata_df is not None:
        return _metadata_df
        
    dfs = []
    for split in ['train.parquet', 'test.parquet', 'val.parquet']:
        path = os.path.join(INCLUDE_DIR, split)
        if os.path.exists(path):
            try:
                dfs.append(pd.read_parquet(path))
            except Exception as e:
                print(f"[PoseMatcher] Warning: Failed to read {split}: {e}")
                
    if not dfs:
        print("[PoseMatcher] Warning: No metadata parquet files found in datasets/include/.")
        _metadata_df = pd.DataFrame(columns=['parent_label', 'label', 'video_path', 'include_50'])
        return _metadata_df
        
    df = pd.concat(dfs, ignore_index=True)
    
    # Normalize labels: uppercase, strip numbers like '48. Hello' -> 'HELLO'
    def normalize_label(label_str):
        if not isinstance(label_str, str):
            return ""
        # Remove numbers and dots at the start (e.g., "48. Hello" -> "Hello")
        cleaned = re.sub(r'^\d+\.\s*', '', label_str)
        # Convert to uppercase and strip
        return cleaned.strip().upper()
        
    df['normalized_label'] = df['label'].apply(normalize_label)
    _metadata_df = df
    print(f"[PoseMatcher] Loaded {len(df)} metadata rows. Unique normalized labels: {len(df['normalized_label'].unique())}")
    return _metadata_df

def find_video_for_gloss(gloss_word: str) -> str:
    """
    Given a gloss word, returns the absolute path of a matching video file in the INCLUDE dataset.
    Returns None if no matching video is found or if the file does not exist on disk.
    """
    df = load_metadata()
    gloss_word = gloss_word.strip().upper()
    
    # Try exact match first
    matches = df[df['normalized_label'] == gloss_word]
    
    # Try fuzzy/partial match if exact match fails
    if matches.empty:
        # Check if the gloss is contained in any label, or vice versa
        matches = df[df['normalized_label'].str.contains(gloss_word, na=False) | 
                     df['normalized_label'].apply(lambda x: gloss_word in x or x in gloss_word)]
                     
    if matches.empty:
        return None
        
    # Check if any matching video file actually exists on disk
    for _, row in matches.iterrows():
        rel_path = row['video_path']
        # The path in the metadata is like 'Greetings/48. Hello/MVI_0031.MOV'
        # We try joining it directly
        abs_path = os.path.join(INCLUDE_DIR, rel_path)
        
        if os.path.exists(abs_path):
            return abs_path
            
        # Try case insensitive check or replacing extension (.mov vs .MOV vs .mp4)
        # Zenodo uploads might have changed extensions
        dir_name = os.path.dirname(abs_path)
        base_name = os.path.basename(abs_path)
        base_name_no_ext, _ = os.path.splitext(base_name)
        
        if os.path.exists(dir_name):
            for file in os.listdir(dir_name):
                f_no_ext, _ = os.path.splitext(file)
                if f_no_ext.lower() == base_name_no_ext.lower():
                    matched_path = os.path.join(dir_name, file)
                    return matched_path
                    
    # None of the matched videos exist on disk
    return None

if __name__ == "__main__":
    print("Testing Pose Matcher...")
    # Load metadata
    load_metadata()
    
    # Test lookups
    test_words = ["HELLO", "THANK YOU", "GOOD MORNING", "I", "YOU", "CAR", "HOUSE", "UNKNOWN_WORD"]
    print("\nMatching results:")
    for word in test_words:
        video_path = find_video_for_gloss(word)
        if video_path:
            print(f"  {word:<15} -> FOUND: {os.path.basename(video_path)} ({video_path})")
        else:
            print(f"  {word:<15} -> NOT FOUND (either missing from dataset or not downloaded yet)")
