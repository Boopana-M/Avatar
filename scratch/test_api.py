import requests

url = "http://localhost:8000/translate/status?video_id=9PXluC2FMD0"
res = requests.get(url)
data = res.json()
blocks = data.get("new_blocks", [])
for b in blocks:
    print(f"Block Index: {b['block_idx']}, Text: {data['caption_blocks'][b['block_idx']]['text']}, Words: {b['words']}")
