import os
import yt_dlp
import whisper

def transcribe_audio(youtube_url: str) -> list:
    """
    Downloads audio from the given YouTube URL and transcribes it using local OpenAI Whisper.
    Returns:
        list of dict: [{'start': float, 'end': float, 'text': str}]
    """
    # Define cache directory inside workspace
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cache_dir = os.path.join(base_dir, "backend", "cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    print(f"[ASR] Downloading audio from: {youtube_url}")
    
    # Configure yt-dlp to download and convert to MP3
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(cache_dir, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            video_id = info['id']
            audio_path = os.path.join(cache_dir, f"{video_id}.mp3")
            
        print(f"[ASR] Audio downloaded to {audio_path}")
        
        # Load local whisper model (using tiny for speed and low memory usage)
        print("[ASR] Loading Whisper model 'tiny'...")
        model = whisper.load_model("tiny")
        
        print("[ASR] Transcribing audio...")
        result = model.transcribe(audio_path, language="en")
        
        formatted_captions = []
        for segment in result.get('segments', []):
            formatted_captions.append({
                'start': float(segment['start']),
                'end': float(segment['end']),
                'text': segment['text'].strip()
            })
            
        print(f"[ASR] Transcription complete. Extracted {len(formatted_captions)} segments.")
        
        # Clean up downloaded audio file to save disk space
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print("[ASR] Cleaned up temporary audio file.")
            
        return formatted_captions
        
    except Exception as e:
        print(f"[ASR] Error during audio transcription fallback: {e}")
        # Clean up in case of error
        if 'video_id' in locals():
            path_to_clean = os.path.join(cache_dir, f"{video_id}.mp3")
            if os.path.exists(path_to_clean):
                os.remove(path_to_clean)
        raise e

if __name__ == "__main__":
    # Test on a short video (e.g. a 5-second video or similar)
    # Using a short test video: https://www.youtube.com/watch?v=jNQXAC9IVRw (Me at the zoo - 19 seconds)
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    print(f"Testing ASR fallback with: {test_url}")
    try:
        caps = transcribe_audio(test_url)
        print("\nTranscription output:")
        for cap in caps:
            print(f"  [{cap['start']:.2f}s - {cap['end']:.2f}s]: {cap['text']}")
    except Exception as e:
        print(f"Test failed: {e}")
