# AGENT BUILD SPEC v3 — ISL Avatar Standalone Web Platform

**This replaces all previous specs, including AGENT_BUILD_SPEC_v2_Hardened.md (the Chrome extension version). Read this entire file before writing any code or running any command.**

## Why this version is different from v2

v2 built this as a Chrome browser extension that injected an overlay directly into the live YouTube page. That approach caused repeated, hard-to-debug failures: CORS restrictions under Manifest V3, a broken VRM loader (`THREE.GLTFLoader is not a constructor`), the avatar rendering as a flat 2D placeholder icon instead of the real 3D model, and — most recently — every single word returning "not matched" even for words confirmed present in the dataset, including words that passed matching in earlier testing.

**v3 removes the browser extension entirely.** Instead, this is now a **standalone website**: the user pastes a YouTube URL into a page you control, the backend fully processes the video before anything is shown, and once done, a "Watch" button opens a page with the YouTube video (via YouTube's official embeddable IFrame Player, not DOM injection) alongside your avatar, playing a pre-computed animation synced to the embedded player's playback time. This removes the fragile live-DOM-injection layer that caused most prior failures, while keeping the entire ML/NLP/animation pipeline unchanged.

---

## PART 0 — Project overview (read this fully before anything else)

**What this project is now:** A website, not a browser extension. A user visits the site, pastes a YouTube video URL into an input box, and clicks "Translate." The backend processes the full video — extracting or transcribing its spoken content, converting it to ISL gloss, matching each gloss word to a recorded sign (or fingerspelling it if no direct sign exists), and stitching everything into one continuous animation. Once processing finishes, a "Watch" button appears. Clicking it opens a page showing the YouTube video (embedded via YouTube's official IFrame Player API) next to a 3D avatar that signs everything the video says, staying in sync with the video's playback position.

**The full pipeline, conceptually, end to end (unchanged from before at the core, only the delivery mechanism changed):**
1. User pastes a YouTube URL into the website and clicks "Translate."
2. The backend gets the spoken content as English text — from existing YouTube captions if available, or by transcribing the audio with Whisper if not.
3. That English text is converted into ISL gloss — a reordered, simplified word sequence following ISL grammar rules (not English word order).
4. For every gloss word, the backend looks up a matching real ISL sign in the dataset. If no direct sign exists, the word is fingerspelled letter by letter instead — no word is ever silently dropped.
5. Each matched sign (or fingerspelled sequence) is converted into pose keypoints (positions of body, hands, and fingers over time).
6. Those keypoints are mapped onto the bones of the rigged 3D avatar model.
7. Everything is stitched into one continuous, timestamped animation for the whole video, with smoothing between transitions.
8. This full result is cached and returned to the frontend once ready — no live real-time processing pressure, since it all happens before the user watches anything.
9. The "Watch" page embeds the actual YouTube video via the IFrame Player API and plays the avatar's pre-computed animation in sync with the embedded player's current playback time.

**Non-negotiable constraints:**
- Every tool, library, dataset, and service used must be free of cost. No paid APIs, no paid hosting beyond free tiers, no paid datasets.
- No free dataset covers every possible English word as a direct ISL sign — fingerspelling is the guaranteed fallback for this, not an afterthought.
- The avatar's 3D model already exists (`backend/models/avatar.vrm`) and has already passed manual finger-bone verification. **Do not ask the user to create a new avatar. Do not touch, replace, or regenerate this file.**
- There is a known, currently unresolved regression: in the previous (extension) version, every gloss word was returning "not matched," including words previously confirmed working (HELLO, DOG, CAT, FISH). This must be diagnosed and fixed as part of this rebuild — see Step 5 below.
- This document is self-contained. Do not assume access to, or memory of, any prior conversation, previous file version, or previous coding session.

---

## PART 1 — Hard rules (apply to every step, no exceptions)

1. **You do not decide when a manual step is "done." A verification script decides, and the user runs it.** For every step marked `[MANUAL]`, you will write a small verification script *first*, before the user does anything. The user runs that script themselves and pastes you the output. You only proceed if that output shows a genuine PASS. You never accept a plain "yes I did it" as sufficient.
2. **You never create, download, substitute, or fabricate any file that a `[MANUAL]` step requires the user to provide.** This includes: 3D model files, dataset files, API keys, or any asset requiring a human/creative/legal decision. If a required file is missing, you stop and say exactly what's missing and exactly how to get it — you never generate a stand-in, even temporarily, even labeled as a placeholder.
3. **Fixed status report format — use this exact structure after every step, no freestyle summaries:**
   ```
   STEP [number] STATUS: [COMPLETE / BLOCKED / WAITING ON USER]
   What I built: ...
   Files changed: ...
   Verification run: [command] -> [actual output]
   Next: [what happens next, or what the user must do before I continue]
   ```
4. **The literal phrase "WAITING FOR USER — DO NOT PROCEED" must appear at the end of every `[MANUAL]` step**, followed by nothing else. You do not continue writing code, do not move to the next step, until the user replies with that step's exact confirmation phrase. If the user replies with anything else (a question, an error, a screenshot), you address that first and re-print the same waiting line again.
5. **If you are ever unsure whether something counts as MANUAL or AGENT, treat it as MANUAL and ask.**
6. Every tool, library, and dataset used must be free. Do not introduce anything paid without stopping and asking first.
7. **Do not substitute any dataset link in this document for a different source** (e.g. Zenodo INCLUDE, IEEE DataPort, ISLTranslate GitHub, iSign). Those were tried previously and failed due to size or access-approval gates.
8. **Do not suggest, reference, or attempt to use Ready Player Me for anything.** It is permanently shut down. The avatar already exists — see Part 0.
9. **Do not claim any code "works" based on a standalone/isolated test alone if that code is meant to run inside the live `/translate` pipeline.** The regression described in Part 0 happened specifically because a component that passed its own isolated test was never actually being called correctly by the live pipeline. Every completion claim for pipeline-integrated code must be verified by testing it through the actual `/translate` endpoint, not just its own unit test.
10. **When you report a step complete, show real, runnable proof — actual printed output, actual logged values — never a description of what the code "should" do.**

---

## PART 2 — Project structure

```
isl-avatar-web/
├── data/
│   ├── isl-words-landmarks/
│   ├── isl-word-videos/
│   ├── isl-csltr/
│   └── fingerspelling/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── models/
│   │   └── avatar.vrm          <- [MANUAL] already exists, already verified — do not touch
│   ├── verify/
│   │   ├── verify_datasets.py
│   │   ├── verify_avatar_rig.py
│   │   └── verify_live_pipeline.py     <- NEW: tests pose_matcher through the actual /translate endpoint, not standalone
│   └── pipeline/
│       ├── captions.py
│       ├── asr_fallback.py
│       ├── gloss_generator.py
│       ├── pose_matcher.py
│       ├── keypoint_extractor.py
│       └── rig_mapper.py
└── frontend/
    ├── index.html          <- URL input + "Translate" button + processing status
    ├── watch.html          <- YouTube IFrame Player + avatar canvas, side by side
    ├── app.js              <- Translate page logic (calls backend, polls status, shows Watch button)
    ├── watch.js            <- Watch page logic (YouTube IFrame API + avatar sync)
    └── lib/
        └── (three.js + @pixiv/three-vrm bundled locally)
```

---

## STEP 0 — [MANUAL] Installs and accounts

Tell the user to install: Python 3.10+, Node.js, ffmpeg, VS Code, Google Chrome, Ollama with a code-capable model pulled (already have qwen2.5-coder:7b).
Tell the user to create free accounts on: Render or Railway (for backend hosting later), and Kaggle (for dataset downloads — likely already done from the previous build).

**Confirmation phrase required from user:** `STEP 0 DONE`

WAITING FOR USER — DO NOT PROCEED

---

## STEP 1 — [MANUAL, agent-verified] Confirm datasets are already in place

The datasets were already downloaded in the previous build attempt. Before re-downloading anything, write `backend/verify/verify_datasets.py` to check whether `/data/isl-words-landmarks/`, `/data/isl-word-videos/`, `/data/isl-csltr/`, and `/data/fingerspelling/` already exist and are non-empty (they likely do, since this is a rebuild, not a fresh start). If all four already exist with content, skip straight to reporting PASS — do not ask the user to re-download anything that's already there.

If any are missing, tell the user to download from these Kaggle sources only (do not substitute):
- `https://www.kaggle.com/datasets/kaushikyh/indian-sign-language-words-with-landmarks` → `/data/isl-words-landmarks/`
- `https://www.kaggle.com/datasets/harsh0239/isl-indian-sign-language-video-dataset` → `/data/isl-word-videos/`
- `https://www.kaggle.com/datasets/drblack00/isl-csltr-indian-sign-language-dataset` → `/data/isl-csltr/`
- `https://www.kaggle.com/datasets/rushilverma07/indian-sign-language-alphabet-dataset` → `/data/fingerspelling/`

**Confirmation required:** the user pastes the actual `verify_datasets.py` output showing PASS for all four folders.

WAITING FOR USER — DO NOT PROCEED

---

## STEP 2 — [AGENT] Captions module

Build/reuse `backend/pipeline/captions.py` using `youtube-transcript-api`. Function `get_captions(youtube_url)` returns `[{start, end, text}]`, raises a clear exception if no captions exist. Run it yourself on a known captioned video and show the real output in your status report.

---

## STEP 3 — [AGENT] ASR fallback module

Build/reuse `backend/pipeline/asr_fallback.py` using `yt-dlp` + `ffmpeg` + local `openai-whisper`. Same input/output shape as Step 2.

---

## STEP 4 — [AGENT, user-checked] English → ISL gloss module

Build/reuse `backend/pipeline/gloss_generator.py`. Requirements:
- Normalize output consistently: `.strip().upper()`, no punctuation
- Apply all of these rules explicitly in the prompt:
  1. Wh-words (WHAT/WHERE/WHO/WHEN/WHY/HOW) always go last in the sentence
  2. Copula/linking verbs (is/am/are/was/were/be/being) are always dropped
  3. Continuous/progressive aspect is always dropped (-ing → base verb)
  4. Negation word always goes immediately after the verb/predicate it negates
  5. Prepositions become postpositions (noun first, relation word after)
  6. Time words (TODAY, TOMORROW, YESTERDAY, NOW) go at the very beginning of the sentence
  7. Modals expressing ability/intent/permission (WANT, CAN) are retained and placed after the main verb
- Few-shot examples: ~25 hand-written English→gloss pairs covering all rules above. Do not download a gloss-pair dataset.
- Call local Ollama only, no paid API

Run a test on 10 sample sentences and print input/output side by side in your status report.

**Confirmation required:** the user reads the 10 outputs and replies either `GLOSS OK` or lists specific lines that look wrong.

WAITING FOR USER — DO NOT PROCEED

---

## STEP 5 — [AGENT] Three-tier sign lookup — MUST diagnose the known regression first

**Before writing or rewriting anything, first diagnose why every word was returning "not matched" in the previous version**, including words previously confirmed working. Do this in order:
1. Run `pose_matcher.py`'s own standalone test (the same kind of test that worked before) on a handful of known dataset words (HELLO, DOG, CAT, FISH). Show the real output.
2. If that standalone test passes, the bug is in how the live pipeline calls it — inspect and show exactly how `pose_matcher.py`'s lookup function gets invoked from `app.py`, and identify the mismatch (wrong function call, wrong index instance, path issue, or normalization mismatch between what's built at startup vs. what's queried per-request).
3. If the standalone test itself now fails, inspect the `normalize()` function and the dataset index-building code directly for a regression — check for accidental changes to folder paths, file extensions expected, or the normalization logic itself.
4. Report the root cause explicitly before writing the fix — do not silently patch without explaining what was actually broken.

Once diagnosed and fixed, build/reuse `backend/pipeline/pose_matcher.py` with:
- A single `normalize()` function applied identically everywhere it's used — at index-build time and at query time, no exceptions
- **Tier 1:** exact match against combined labels from all three word-level dataset folders
- **Tier 2:** lemmatize (nltk WordNetLemmatizer) and retry Tier 1
- **Tier 3:** fingerspelling — split into letters, look up each in `/data/fingerspelling/`

Build/reuse `backend/pipeline/keypoint_extractor.py` (pre-extracted landmarks loaded directly, MediaPipe run only on raw video/image sources, disk-cached).

**Critical:** write `backend/verify/verify_live_pipeline.py` — this script must call the actual `/translate`-path logic (not `pose_matcher.py` in isolation) on a short test video and print, for each word, which tier it matched through. This is what proves the regression is actually fixed, not just that the isolated function works again.

**Confirmation required:** the user runs `verify_live_pipeline.py` and pastes the output showing real matches (not 100% unmatched) for known dataset words.

WAITING FOR USER — DO NOT PROCEED

---

## STEP 6 — [MANUAL, already complete, agent re-verifies only] Avatar file

The avatar already exists at `backend/models/avatar.vrm` and has already passed finger-bone verification (confirmed bone names: `J_Bip_L/R_[Thumb/Index/Middle/Ring/Little][1/2/3]`). Do not ask the user to create a new one. Simply re-run `backend/verify/verify_avatar_rig.py` against the existing file to confirm it's still present and intact after the restructuring, and report the result.

WAITING FOR USER — DO NOT PROCEED (only if the file is missing or the script fails; otherwise report PASS and continue automatically since this was already verified in a prior session)

---

## STEP 7 — [AGENT] Keypoint-to-rig mapping

Build/reuse `backend/pipeline/rig_mapper.py`. Read actual bone names from the verified `.vrm`. Map word-level keypoint sequences to bone rotations. For fingerspelling, hold each letter's static pose ~300–400ms with brief interpolation between letters. Interpolate between the end pose of one sign and the start of the next. **Show real computed rotation values for at least one test word's bones as proof, not just a description.**

---

## STEP 8 — [AGENT] Backend API

Build `backend/app.py` (FastAPI):
- `POST /translate` — accepts `{youtube_url}`, kicks off full processing (Steps 2–7), returns immediately with a job ID or "processing" status (do not block the HTTP request for the full multi-minute processing time)
- `GET /translate/status/{video_id}` — the frontend polls this to check if processing is done
- `GET /translate/result/{video_id}` — once done, returns the full gloss sequence with per-word tier info and the complete animation data
- Cache everything by video ID in SQLite so repeat requests are instant
- Serve `avatar.vrm` via a proper FastAPI route with correct CORS headers
- Handle non-ASCII caption text safely (encode-safe logging)

---

## STEP 9 — [AGENT] Frontend website (replaces the Chrome extension entirely)

**`frontend/index.html` + `app.js` (Translate page):**
- URL input box, "Translate" button
- On submit, calls `POST /translate`, then polls `GET /translate/status/{video_id}` every few seconds
- Shows a clear processing state (not a silent infinite spinner — show elapsed time or a progress indicator if possible)
- Once status is "done," shows a "Watch" button linking to `watch.html?v={video_id}`

**`frontend/watch.html` + `watch.js` (Watch page):**
- Embed the YouTube video using YouTube's official **IFrame Player API** (`https://www.youtube.com/iframe_api`) — this is a supported, stable embedding method, not DOM injection into youtube.com itself
- Load the avatar using Three.js + `@pixiv/three-vrm` (bundled locally, per no-CDN-for-scripts-beyond-the-approved-list convention) in a canvas next to the video
- Poll the YouTube player's `getCurrentTime()` method continuously
- Look up the matching pre-computed animation frame (already fetched from `GET /translate/result/{video_id}`) for that timestamp and apply the corresponding bone rotations to the loaded VRM model
- Display the current gloss word and its match tier (word/lemma/fingerspell) as a visible label

No Chrome extension manifest, no content scripts, no injection into youtube.com's live page — this is a normal web page embedding a normal YouTube player.

---

## STEP 10 — [AGENT, user-run] End-to-end test

Ask the user for 2–3 real YouTube video URLs, including at least one built entirely from dataset-confirmed vocabulary (the user has one already prepared). Ask the user to run each through the website and report: does the "Watch" button appear after processing, does the avatar visibly animate (not a static or 2D placeholder), does it fingerspell visibly on unmatched words, does it stay in sync with pause/seek on the embedded player.

**Confirmation required:** user reports pass/fail per video, and confirms the avatar is genuinely a rendered 3D model (not a flat icon) — this specific check is required given the prior session's rendering bug.

WAITING FOR USER — DO NOT PROCEED

---

## STEP 11 — [MANUAL, optional] Deploy

If the user wants this publicly accessible rather than run locally: deploy the backend to Render/Railway free tier and the frontend as a static site (e.g. GitHub Pages, Netlify free tier, or Render static site). No cost required for this at demo scale.

---

## PART 3 — Master checklist

| Step | Type | Gate before proceeding |
|---|---|---|
| 0 | MANUAL | User types `STEP 0 DONE` |
| 1 | MANUAL, agent-verified | User pastes verify_datasets.py output, all PASS |
| 2 | AGENT | none |
| 3 | AGENT | none |
| 4 | AGENT, user-checked | User replies `GLOSS OK` or lists issues |
| 5 | AGENT, must diagnose known regression first | User pastes verify_live_pipeline.py output showing real matches |
| 6 | MANUAL (already done), agent re-verifies | PASS expected automatically; only waits if broken |
| 7 | AGENT | none |
| 8 | AGENT | none |
| 9 | AGENT | none |
| 10 | AGENT, user-run | User reports pass/fail per test video, confirms real 3D rendering |
| 11 | MANUAL, optional | User decision |

**If you are the agent reading this: your very first action is to output the Step 0 instructions and then print the exact line `WAITING FOR USER — DO NOT PROCEED` and stop. Do not scaffold any folders, files, or code before Step 0 is confirmed. If Steps 0/1/6 are already satisfied from a prior session, verify them quickly and move forward rather than repeating completed manual work.**
