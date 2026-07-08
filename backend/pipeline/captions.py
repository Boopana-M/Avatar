import re
import urllib.parse
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

class CaptionsNotFoundError(Exception):
    """Custom exception raised when captions are not available for a video."""
    pass

def extract_video_id(url: str) -> str:
    """
    Extracts the video ID from various YouTube URL formats.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname in ('youtu.be', 'www.youtu.be'):
        return parsed.path[1:]
    if parsed.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        if parsed.path == '/watch':
            p = urllib.parse.parse_qs(parsed.query)
            return p.get('v', [None])[0]
        if parsed.path.startswith(('/embed/', '/v/', '/shorts/')):
            return parsed.path.split('/')[2]
    # Fallback regex search
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract YouTube video ID from URL: {url}")

def get_captions(youtube_url: str) -> list:
    """
    Retrieves captions for a given YouTube video URL.
    Returns:
        list of dict: [{'start': float, 'end': float, 'text': str}]
    Raises:
        CaptionsNotFoundError: if captions are disabled or unavailable.
    """
    try:
        video_id = extract_video_id(youtube_url)
        print(f"[Captions] Fetching captions for video ID: {video_id}")
        
        # Instantiate YouTubeTranscriptApi and fetch English captions
        api = YouTubeTranscriptApi()
        try:
            data = api.fetch(video_id, languages=['en', 'en-US'])
        except Exception as e:
            # Try to list and find English if direct fetch fails
            try:
                transcript_list = api.list(video_id)
                transcript = transcript_list.find_transcript(['en', 'en-US'])
                data = transcript.fetch()
            except Exception:
                raise CaptionsNotFoundError("No English captions found.")
            
        formatted_captions = []
        for entry in data:
            start = float(entry.start)
            duration = float(entry.duration)
            end = round(start + duration, 2)
            formatted_captions.append({
                'start': start,
                'end': end,
                'text': entry.text.replace('\n', ' ').strip()
            })
            
        print(f"[Captions] Successfully retrieved {len(formatted_captions)} caption entries.")
        return formatted_captions
        
    except Exception as e:
        print(f"[Captions] Failed to retrieve captions: {e}")
        raise CaptionsNotFoundError(f"Captions unavailable or disabled: {e}")

if __name__ == "__main__":
    # Test with a well-known captioned YouTube video: "Charlie at the Chocolate Factory" trailer or similar
    # Using a classic captioned video: https://www.youtube.com/watch?v=9bZkp7q19f0 (PSY - GANGNAM STYLE has captions, or standard tech reviews)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Rick Roll usually has English captions
    print(f"Testing caption extraction with: {test_url}")
    try:
        caps = get_captions(test_url)
        print("\nFirst 5 caption entries:")
        for cap in caps[:5]:
            safe_text = cap['text'].encode('ascii', errors='replace').decode('ascii')
            print(f"  [{cap['start']:.2f}s - {cap['end']:.2f}s]: {safe_text}")
    except Exception as e:
        print(f"Test failed: {e}")
