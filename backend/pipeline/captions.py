import re
import sys
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def extract_video_id(youtube_url):
    """
    Extracts the 11-character YouTube video ID from various YouTube URL formats.
    """
    patterns = [
        r'(?:v=|\/v\/|embed\/|shorts\/|youtu\.be\/|\/embed\/|\/watch\?v=|\/shorts\/)([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
            
    # Check if the URL is already an 11-char ID
    if len(youtube_url) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', youtube_url):
        return youtube_url
        
    raise ValueError(f"Could not extract YouTube video ID from URL: {youtube_url}")

def get_captions(youtube_url):
    """
    Retrieves captions for a given YouTube URL.
    Returns:
        List of dicts: [{'start': float, 'end': float, 'text': str}]
    Raises:
        Exception: If captions are disabled or do not exist.
    """
    video_id = extract_video_id(youtube_url)
    api = YouTubeTranscriptApi()
    try:
        # Attempt to fetch English transcripts (including manual and auto-generated)
        transcript_list = api.fetch(video_id, languages=['en', 'en-US', 'en-GB'])
    except (TranscriptsDisabled, NoTranscriptFound):
        try:
            # Fallback to default (usually lists first available or fails)
            # In some versions, fetch() requires list of languages, so let's try calling list().find_transcript().fetch()
            # or just api.fetch(video_id)
            transcript_list = api.fetch(video_id)
        except Exception as inner_e:
            raise Exception(f"No captions exist or transcripts are disabled for video {video_id}: {str(inner_e)}")
    except Exception as e:
        raise Exception(f"Failed to retrieve captions for video {video_id}: {str(e)}")
        
    captions = []
    for entry in transcript_list:
        start = entry.start
        duration = entry.duration
        end = start + duration
        text = entry.text
        captions.append({
            'start': round(start, 3),
            'end': round(end, 3),
            'text': text.strip().replace('\n', ' ')
        })
    return captions

if __name__ == "__main__":
    # Test block on a known captioned video (e.g., Rick Astley - Never Gonna Give You Up)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"Testing captions retrieval for: {test_url}")
    try:
        caps = get_captions(test_url)
        print(f"Successfully retrieved {len(caps)} caption blocks.")
        print("First 5 caption entries:")
        for entry in caps[:5]:
            # Print using safe encoding for console representation
            safe_text = entry['text'].encode('ascii', errors='replace').decode('ascii')
            print(f"  [{entry['start']:.2f}s - {entry['end']:.2f}s]: {safe_text}")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
