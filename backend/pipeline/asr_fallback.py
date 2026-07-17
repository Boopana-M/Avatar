import os
import sys
import tempfile
import yt_dlp
import whisper

def transcribe_audio(youtube_url, model_name="base"):
    """
    Downloads audio from a YouTube URL and transcribes it using local openai-whisper.
    Returns:
        List of dicts: [{'start': float, 'end': float, 'text': str}]
    """
    # Use a temp directory inside the workspace to avoid writing outside it
    current_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    temp_dir = os.path.join(workspace_root, "tmp")
    os.makedirs(temp_dir, exist_ok=True)
    
    with tempfile.TemporaryDirectory(dir=temp_dir) as tmpdir:
        out_template = os.path.join(tmpdir, "audio.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
        
        print(f"Downloading audio from {youtube_url}...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
        except Exception as e:
            raise Exception(f"Failed to download audio using yt-dlp: {str(e)}")
            
        audio_path = os.path.join(tmpdir, "audio.wav")
        if not os.path.exists(audio_path):
            raise Exception("Downloaded audio file was not found or failed to convert to WAV.")
            
        print(f"Loading Whisper model '{model_name}' (this might take a moment to download on first run)...")
        try:
            model = whisper.load_model(model_name)
        except Exception as e:
            raise Exception(f"Failed to load Whisper model: {str(e)}")
            
        print("Transcribing audio...")
        try:
            # Transcribe audio with Whisper
            result = model.transcribe(audio_path)
        except Exception as e:
            raise Exception(f"Failed to transcribe audio: {str(e)}")
            
        captions = []
        for segment in result.get("segments", []):
            start = segment.get("start", 0.0)
            end = segment.get("end", 0.0)
            text = segment.get("text", "").strip()
            if text:
                captions.append({
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "text": text
                })
        return captions

if __name__ == "__main__":
    # Test on a short, public YouTube video: "Me at the zoo" (19 seconds)
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    print(f"Testing ASR fallback retrieval for: {test_url}")
    try:
        # Use "tiny" model for faster test execution in CPU environments
        caps = transcribe_audio(test_url, model_name="tiny")
        print(f"Successfully transcribed {len(caps)} segments.")
        for entry in caps:
            # Safe print for Windows terminal encoding
            safe_text = entry['text'].encode('ascii', errors='replace').decode('ascii')
            print(f"  [{entry['start']:.2f}s - {entry['end']:.2f}s]: {safe_text}")
    except Exception as e:
        print(f"ASR fallback test failed: {e}")
        sys.exit(1)
