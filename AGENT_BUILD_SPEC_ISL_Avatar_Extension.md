# AGENT BUILD SPEC — ISL Avatar Browser Extension

**Read this entire file before writing any code.**

You are an autonomous coding agent. Your job is to build a Chrome browser extension that overlays an animated Indian Sign Language (ISL) avatar, bottom-right, on top of YouTube videos, synced to playback. The user has already selected the full tech stack below — do not substitute any tool, library, or service for a different one, even if you think an alternative is better. Every tool listed is free; do not introduce anything paid.

## Rules you must follow throughout this project

1. Some steps in this document are marked **[MANUAL — USER]**. You cannot complete these steps yourself. When you reach one, STOP, clearly tell the user exactly what they need to do, what file/folder to put the result in, and what filename/format you expect back. Then wait — do not simulate, fake, or placeholder-skip past a manual step by inventing fake output that pretends the step was done.
2. Steps marked **[AGENT]** are yours to fully implement — write real, complete, runnable code. Do not leave TODO stubs on agent steps unless you explicitly say so to the user and explain what's left.
3. Steps marked **[AGENT + USER CHECK]** means you implement it, but you must ask the user to manually verify the output before you proceed (e.g., checking gloss quality, checking the rig moves correctly). State clearly what they should look at and what "correct" looks like.
4. After finishing each numbered step, output a short status update: what you built, what file(s) it's in, what (if anything) the user needs to do before the next step, and how to run/test what you just built.
5. Never mark a step complete if it isn't runnable. If something can't be finished without a manual dependency (e.g., no avatar file yet), say so explicitly and move to a step that doesn't depend on it, then come back.
6. Keep all code inside a single project root folder. Suggested structure:

```
isl-avatar-extension/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── pipeline/
│   │   ├── captions.py
│   │   ├── asr_fallback.py
│   │   ├── gloss_generator.py
│   │   ├── pose_matcher.py
│   │   └── keypoint_extractor.py
│   ├── cache/
│   └── models/            <- [MANUAL] avatar .glb file goes here
├── extension/
│   ├── manifest.json
│   ├── content_script.js
│   ├── overlay.js
│   ├── popup.html
│   └── lib/                <- three.js, loaders
└── data/                    <- [MANUAL] downloaded datasets go here
```

---

## STEP 0 — [MANUAL — USER] Accounts and local installs

Tell the user to do the following before you write any code, and wait for confirmation:
- Install Python 3.10+, Node.js, Blender, ffmpeg, VS Code, Google Chrome
- Install Ollama locally (already have it) and confirm a code-capable model is pulled (e.g. `ollama pull qwen2.5-coder` or whichever model they're running you on)
- Create a free account on readyplayer.me
- Create a free account on Render or Railway (for later deployment)
- Confirm they have ~2GB free disk space for datasets

Do not proceed to Step 1 until the user confirms these are done.

---

## STEP 1 — [MANUAL — USER] Download datasets

Instruct the user to manually download these into `/data/`:
- ISLTranslate (github.com/Exploration-Lab/ISLTranslate) → `/data/isltranslate/`
- iSign dataset (Hugging Face: Exploration-Lab/iSign) → `/data/isign/`
- INCLUDE / INCLUDE-50 → `/data/include/`
- ISL-CSLTR (Mendeley Data) → `/data/isl-csltr/`

You cannot download these yourself (they require manual access/agreement on some sites). Wait for the user to confirm the folders exist and are non-empty before continuing. Once confirmed, write a small Python script `backend/pipeline/verify_datasets.py` that checks these folders exist and prints a summary of file counts, so the user can sanity-check their download.

---

## STEP 2 — [AGENT] Caption extraction module

Build `backend/pipeline/captions.py`:
- Function `get_captions(youtube_url) -> list[{start, end, text}]`
- Use the `youtube-transcript-api` Python package (pip install, free, no key)
- If no captions are available, raise a clear exception that the caller can catch to trigger the ASR fallback

Add this dependency to `requirements.txt`. Write a small test at the bottom of the file (`if __name__ == "__main__":`) that runs on a hardcoded well-known captioned YouTube video URL and prints the first 5 caption lines, so the user can confirm it works by running `python backend/pipeline/captions.py`.

---

## STEP 3 — [AGENT] ASR fallback module

Build `backend/pipeline/asr_fallback.py`:
- Function `transcribe_audio(youtube_url) -> list[{start, end, text}]`
- Use `yt-dlp` (free) to download audio only, `ffmpeg` to convert if needed, then `openai-whisper` (free, local) to transcribe
- Return the same shape as `captions.py`'s output so the rest of the pipeline doesn't need to care which path was used

Note to user after this step: local Whisper transcription can be slow on CPU-only machines — tell the user if their machine has no GPU, to expect this step to take longer per video, and that this is expected, not a bug.

---

## STEP 4 — [AGENT + USER CHECK] English → ISL gloss module

Build `backend/pipeline/gloss_generator.py`:
- Function `text_to_gloss(sentence) -> gloss_string`
- Load 10–15 few-shot examples from the ISLTranslate dataset (downloaded in Step 1) directly into the prompt
- Call the local Ollama model via its local API (`http://localhost:11434/api/generate` or the `ollama` Python package) — do not call any paid API
- Write a test script that runs this on 10 sample sentences and prints input/output side by side

**Ask the user to manually read the 10 test outputs** and confirm the gloss looks reasonable (shorter than the English, keywords in a sensible order, no hallucinated words). Tell them explicitly: "Please check these 10 outputs and tell me if any look wrong before I continue." Do not proceed to Step 5 until they respond.

---

## STEP 5 — [AGENT] Gloss → sign clip matching + keypoint extraction

Build `backend/pipeline/pose_matcher.py` and `backend/pipeline/keypoint_extractor.py`:
- `pose_matcher.py`: given a gloss word, look up a matching video clip filename in the INCLUDE/ISL-CSLTR metadata (downloaded in Step 1)
- `keypoint_extractor.py`: given a clip filename, run MediaPipe Holistic (pip install `mediapipe`) over it and return a list of frame-by-frame keypoints (body, hand, face landmarks)
- Combine into a function `gloss_sequence_to_keypoints(gloss_words: list[str]) -> list[frame_keypoints]`

**Tell the user explicitly**: some gloss words will have no matching clip in the dataset — list these as "unmatched words" in the function's output rather than failing silently, so the user can see coverage gaps.

---

## STEP 6 — [MANUAL — USER] Build and style the avatar

You (the agent) cannot create 3D art. Tell the user clearly:
- Go to readyplayer.me and generate a base rigged avatar
- **Confirm it exports with individual finger bones** — this is required, not optional, for sign language; if the free export doesn't include finger bones, they need to pick a different base/avatar option that does
- Import into Blender and adjust to match their reference: skin tone, hair, teal kurti top, navy trousers, brown shoes
- Export the final result as `models/avatar.glb`, keeping file size under ~10MB

Wait for the user to place `avatar.glb` in `backend/models/` before continuing to Step 7.

---

## STEP 7 — [AGENT] Keypoint-to-rig mapping

Once `avatar.glb` exists, build `backend/pipeline/rig_mapper.py`:
- Function that takes the keypoint sequences from Step 5 and maps them to bone rotations matching the avatar's skeleton hierarchy (read the `.glb`'s bone names using a library like `pygltflib` to confirm naming before hardcoding bone name assumptions)
- Interpolate between the end pose of one gloss word and the start pose of the next, rather than hard-cutting, to avoid jerky transitions
- Output: a timestamped JSON animation sequence

---

## STEP 8 — [AGENT] Backend API

Build `backend/app.py` using FastAPI:
- `POST /translate` — accepts `{youtube_url}`, runs Steps 2–7 in order, returns `{status, animation_data, unmatched_words}`
- Cache results keyed by YouTube video ID using SQLite (free, no separate server needed) so repeat requests are instant
- `GET /translate/{video_id}` — returns cached result if it exists

Write a `requirements.txt` covering every dependency used across all pipeline files.

---

## STEP 9 — [AGENT] Chrome extension

Build in `/extension/`:
- `manifest.json` (Manifest V3)
- `content_script.js`: detects YouTube's `#movie_player`, injects a "Use avatar" button and a bottom-right floating `<div>` overlay container
- `overlay.js`: on button click, calls the backend `/translate` endpoint; while waiting, show a "Preparing avatar..." state; once data returns, load `avatar.glb` via Three.js (bundle Three.js locally in `/extension/lib/`, don't rely on a CDN since Manifest V3 restricts remote code) and play the animation
- Sync logic: listen to the YouTube `<video>` element's `timeupdate` event and drive the correct animation frame from it

Tell the user how to load it: "Go to chrome://extensions, enable Developer Mode, click Load Unpacked, and select the `/extension` folder."

---

## STEP 10 — [AGENT + USER CHECK] End-to-end test

- Ask the user to pick 3–5 real captioned YouTube videos
- Run the full pipeline on each ahead of time so they're cached
- Ask the user to open each video in Chrome with the extension loaded, click "Use avatar," and confirm: the overlay appears bottom-right, the avatar animates, and it stays roughly in sync when they pause/seek
- Ask them to report back anything broken (overlay position, sync drift, missing signs) so you can fix it

---

## STEP 11 — [MANUAL — USER, optional] Publish

If the user wants public distribution rather than local demo use only, tell them this is the only step in the whole project with any real-world cost: a one-time Chrome Web Store developer registration fee (~$5). Otherwise, "Load Unpacked" is sufficient for a free, fully working local build and demo.

---

## Summary table for the agent's own reference

| Step | Who does it |
|---|---|
| 0. Installs/accounts | MANUAL |
| 1. Download datasets | MANUAL |
| 2. Captions module | AGENT |
| 3. ASR fallback | AGENT |
| 4. Gloss generation | AGENT, user checks output |
| 5. Pose matching + keypoints | AGENT |
| 6. Avatar creation | MANUAL |
| 7. Rig mapping | AGENT |
| 8. Backend API | AGENT |
| 9. Chrome extension | AGENT |
| 10. End-to-end test | AGENT builds test harness, user runs/verifies |
| 11. Publish | MANUAL, optional |

If you (the agent) are ever unsure whether something is a manual or agent step, default to telling the user and asking, rather than guessing and producing fake output.
