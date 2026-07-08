import urllib.request
import json

def test_translation_api(youtube_url: str):
    print("=" * 60)
    print("TESTING END-TO-END TRANSLATION API")
    print("=" * 60)
    print(f"Request URL: {youtube_url}\n")
    
    payload = {"youtube_url": youtube_url}
    data = json.dumps(payload).encode('utf-8')
    headers = {"Content-Type": "application/json"}
    
    url = "http://localhost:8000/translate"
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        print("[Test] Sending request to local FastAPI server (http://localhost:8000/translate)...")
        with urllib.request.urlopen(req, timeout=120) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
            print("\n[Test] Response Status:", res_data.get("status"))
            print("[Test] Video ID:", res_data.get("video_id"))
            print("[Test] Cached:", res_data.get("cached"))
            print("[Test] Method Used:", res_data.get("method"))
            
            unmatched = res_data.get("unmatched_words", [])
            print(f"[Test] Unmatched Words Count: {len(unmatched)}")
            if unmatched:
                print(f"[Test] Unmatched Words (sample): {unmatched[:15]}")
                
            anim_data = res_data.get("animation_data", [])
            print(f"[Test] Mapped Animation Frames Count: {len(anim_data)}")
            if anim_data:
                print(f"[Test] First Frame Time: {anim_data[0]['time']}s")
                print(f"[Test] Last Frame Time: {anim_data[-1]['time']}s")
                
            print("\n[Test] SUCCESS: End-to-end API test completed successfully!")
            
    except Exception as e:
        print(f"\n[Test] ERROR: API call failed: {e}")
        print("[Test] Please verify that the FastAPI backend server is running.")
    print("=" * 60)

if __name__ == "__main__":
    # Test on a short video containing standard greetings
    # A video with captions: https://www.youtube.com/watch?v=9bZkp7q19f0 (Gangnam Style)
    # or any standard video
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    test_translation_api(test_url)
