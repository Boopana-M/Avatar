import os
import sys
from gloss_generator import generate_gloss
from pose_matcher import build_dataset_index, lookup_sign

def test_pipeline_matching(sentence, data_dir):
    print(f"\nProcessing sentence: \"{sentence}\"")
    
    # 1. Generate Gloss
    try:
        gloss_text = generate_gloss(sentence)
        print(f"Generated Gloss: {gloss_text}")
    except Exception as e:
        print(f"Gloss generation failed: {e}")
        return
        
    # 2. Build Index
    index = build_dataset_index(data_dir)
    fingerspelling_dir = os.path.join(data_dir, "fingerspelling")
    
    # 3. Match each word
    gloss_words = gloss_text.split()
    counts = {
        "tier1": 0,
        "tier2": 0,
        "tier3": 0,
        "unmatched": 0
    }
    
    matches_report = []
    
    for word in gloss_words:
        res = lookup_sign(word, index, fingerspelling_dir)
        tier = res["tier"]
        source = res["source"]
        
        if source == "unmatched":
            counts["unmatched"] += 1
            matches_report.append(f"  Word: '{word}' -> Unmatched")
        elif tier == 1:
            counts["tier1"] += 1
            matches_report.append(f"  Word: '{word}' -> Tier 1 Match ({source}) as '{res['matched_word']}'")
        elif tier == 2:
            counts["tier2"] += 1
            matches_report.append(f"  Word: '{word}' -> Tier 2 Match ({source}) as '{res['matched_word']}' (lemmatized)")
        elif tier == 3:
            counts["tier3"] += 1
            if "letters" in res:
                letters_str = "".join([l["word"] for l in res["letters"]])
                matches_report.append(f"  Word: '{word}' -> Tier 3 Fingerspelling ('{letters_str}')")
            else:
                matches_report.append(f"  Word: '{word}' -> Tier 3 Fingerspelling")
                
    print("\nMatching Details:")
    for rep in matches_report:
        print(rep)
        
    print("\nMatching Statistics:")
    print(f"  Tier 1 (Exact match):       {counts['tier1']}")
    print(f"  Tier 2 (Lemma match):       {counts['tier2']}")
    print(f"  Tier 3 (Fingerspelling):    {counts['tier3']}")
    print(f"  Unmatched:                  {counts['unmatched']}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    data_dir = os.path.join(project_root, "data")
    
    # Run test on 2 sample sentences
    test_pipeline_matching("Can you help me with this?", data_dir)
    test_pipeline_matching("My dog is sleeping on the floor.", data_dir)
