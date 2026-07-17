AGENT BUILD SPEC v2 — ISL Avatar Browser Extension (Hardened)

This replaces all previous specs. Read this entire file before writing any code or running any command.

Why this version is different

A previous attempt at this project had an AI agent silently generate a placeholder avatar file and then report it as if the user had manually created it. Soft instructions like "please don't fake this" were not enough to prevent that. This version fixes that by making every manual step verified programmatically, not taken on trust — and by defining an exact, rigid stop-and-acknowledge protocol you must follow with no exceptions.

A second issue in earlier attempts: the originally chosen datasets (ISLTranslate, iSign, INCLUDE via Zenodo, IEEE DataPort fingerspelling) were either gated behind manual approval requests, required owner permission, or were too large (INCLUDE's full set is ~57GB). This version replaces all of those with easily downloadable Kaggle-hosted alternatives, and removes one dataset dependency entirely by using hand-written few-shot examples instead of a downloaded gloss corpus.

A third issue: the original plan used Ready Player Me for the avatar. Ready Player Me shut down its public/developer services entirely on January 31, 2026 after being acquired by Netflix — it is permanently unavailable, not a temporary outage. This version replaces it with VRoid Studio, exporting to the VRM format, which the user has already used successfully — the avatar model already exists and has been manually verified to contain proper individual finger bones (verified in Blender, bone names follow the pattern J_Bip_L_[Finger][1/2/3] and J_Bip_R_[Finger][1/2/3], e.g. J_Bip_R_Index2).


PART 0 — Project overview (read this fully before anything else)

What this project is: A Chrome browser extension. When a user is watching any YouTube video, a "Use avatar" button appears near the player. When clicked, a small floating window appears in the bottom-right corner of the video — exactly like the small inset box a human sign language interpreter appears in during a televised broadcast (e.g. a news briefing with an interpreter boxed in the bottom-right corner). Inside that floating window is a 3D animated avatar (a stylized doll-like female character, not photorealistic) that signs Indian Sign Language (ISL) for everything spoken in the video, staying in sync with playback.

The full pipeline, conceptually, end to end:


User opens a YouTube video (captions may or may not exist) and clicks "Use avatar."
The system gets the spoken content as English text — either from existing YouTube captions, or by transcribing the audio if no captions exist.
That English text is converted into ISL gloss — a reordered, simplified word sequence that follows ISL grammar rules (not the same word order as English).
For every gloss word, the system finds a real recorded ISL sign video for that word if one exists in the datasets. If no direct sign exists for a word, the system spells that word letter-by-letter instead (fingerspelling), so no word is ever silently skipped.
Each matched sign clip (or fingerspelled letter sequence) is converted into pose keypoints (positions of the body, hands, and fingers over time).
Those keypoints are mapped onto the bones of a rigged 3D avatar model, so the avatar's arms, hands, and fingers move the same way the recorded human signer's did.
All of this is stitched into one continuous, timestamped animation for the whole video — not just isolated word clips, but a smooth continuous performance, with smoothing between transitions rather than jerky cuts.
This runs inside a floating overlay window injected into the YouTube page by the browser extension, and the avatar's playback position stays synced to the actual video's current playback time — including when the user pauses, seeks, or changes speed.


Non-negotiable constraints:


Every tool, library, dataset, and service used must be free of cost. No paid APIs, no paid hosting beyond free tiers, no paid datasets.
No free dataset covers every possible English word as a direct ISL sign — this is expected and is why fingerspelling exists as a fallback, not an afterthought.
The avatar's 3D model is created manually by the user using VRoid Studio (free desktop app), exported as VRM, and manually verified in Blender — this is a creative/manual task that cannot be automated, and is treated as such throughout this document. The avatar file for this project already exists and has already passed manual verification — see Step 6 for what this means for the agent.
This document is self-contained. Do not assume access to, or memory of, any prior conversation, previous file version, or previous coding session. Everything you need to build this is written below.



PART 1 — Hard rules (apply to every step, no exceptions)


You do not decide when a manual step is "done." A verification script decides, and the user runs it. For every step marked [MANUAL], you will write a small verification script first, before the user does anything. The user runs that script themselves and pastes you the output. You only proceed if that output shows a genuine PASS. You never accept a plain "yes I did it" as sufficient — you require the script's printed result.
You never create, download, substitute, or fabricate any file that a [MANUAL] step requires the user to provide. This includes: 3D model files, dataset files, API keys, or any asset requiring a human/creative/legal decision. If a required file is missing, you stop and say exactly what's missing and exactly how to get it — you do not generate a stand-in "just to keep things moving," even temporarily, even if you label it a placeholder.
Fixed status report format — use this exact structure after every step, no freestyle summaries:


   STEP [number] STATUS: [COMPLETE / BLOCKED / WAITING ON USER]
   What I built: ...
   Files changed: ...
   Verification run: [command] -> [actual output]
   Next: [what happens next, or what the user must do before I continue]


The literal phrase "WAITING FOR USER — DO NOT PROCEED" must appear at the end of every [MANUAL] step, followed by nothing else. You do not continue writing code, do not move to the next step, do not "get ahead" on non-dependent work, until the user replies with the exact confirmation phrase given in that step (each step specifies its own phrase below). If the user replies with anything else (a question, an error, a screenshot), you address that first and re-print the same waiting line again — you do not treat a partial or off-topic reply as permission to continue.
If you are ever unsure whether something counts as MANUAL or AGENT, treat it as MANUAL and ask. Guessing in the direction of "I'll just do it myself" is the exact failure this document exists to prevent.
Every tool, library, and dataset used must be free. Do not introduce anything paid without stopping and asking first.
Do not substitute any dataset link in this document for a different source you may know of (e.g. Zenodo INCLUDE, IEEE DataPort, ISLTranslate GitHub, iSign). Those were tried previously and failed due to size or access-approval gates. Use only the Kaggle links given in Step 1 below.
Do not suggest, reference, or attempt to use Ready Player Me for anything. It is permanently shut down. The avatar workflow is VRoid Studio → VRM export → Blender verification, described in Step 6.



PART 2 — Project structure

isl-avatar-extension/
├── data/
│   ├── isl-words-landmarks/
│   ├── isl-word-videos/
│   ├── isl-csltr/
│   └── fingerspelling/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── models/
│   │   └── avatar.vrm          <- [MANUAL] placed here by user only — already created and verified
│   ├── verify/
│   │   ├── verify_datasets.py
│   │   └── verify_avatar_rig.py
│   └── pipeline/
│       ├── captions.py
│       ├── asr_fallback.py
│       ├── gloss_generator.py
│       ├── pose_matcher.py
│       ├── keypoint_extractor.py
│       └── rig_mapper.py
└── extension/
    ├── manifest.json
    ├── content_script.js
    ├── overlay.js
    ├── popup.html
    └── lib/
        └── (three.js + @pixiv/three-vrm bundled locally)


STEP 0 — [MANUAL] Installs and accounts

Tell the user to install: Python 3.10+, Node.js, Blender, ffmpeg, VS Code, Google Chrome, Ollama with a code-capable model pulled, and VRoid Studio (free desktop app, vroid.com/en/studio — no account required to use it).
Tell the user to create free accounts on: Render or Railway, and Kaggle (for dataset downloads in Step 1).

Confirmation phrase required from user: STEP 0 DONE

WAITING FOR USER — DO NOT PROCEED


STEP 1 — [MANUAL, agent-verified] Download datasets

These sources were chosen specifically because they are single-click Kaggle downloads with no owner-approval step and no oversized (50GB+) archives. Do not substitute these for ISLTranslate, iSign, IEEE DataPort, or raw Zenodo INCLUDE — those are gated behind manual request/approval or are too large, and caused repeated download failures in earlier attempts.

Tell the user to manually download into /data/:


Word-level ISL signs (with pre-extracted pose landmarks, no MediaPipe extraction needed for these)
https://www.kaggle.com/datasets/kaushikyh/indian-sign-language-words-with-landmarks → /data/isl-words-landmarks/
Word-level ISL sign videos (raw video, backup/supplement to the above)
https://www.kaggle.com/datasets/harsh0239/isl-indian-sign-language-video-dataset → /data/isl-word-videos/
ISL-CSLTR (sentence-level videos + word-level images), Kaggle mirror
https://www.kaggle.com/datasets/drblack00/isl-csltr-indian-sign-language-dataset → /data/isl-csltr/
ISL fingerspelling alphabet (A–Z, digits), Kaggle
https://www.kaggle.com/datasets/rushilverma07/indian-sign-language-alphabet-dataset → /data/fingerspelling/


Tell the user: all four require only a free Kaggle account (no approval wait) and can be downloaded directly from the Kaggle page's Download button, or via the kaggle CLI (pip install kaggle, free) if they prefer scripted downloads. Each download is a .zip — extract its contents directly into the target folder.

No download needed for gloss few-shot examples. Instead of downloading a gloss-pair dataset (which caused repeated permission/access failures previously), you (the agent) will hand-write a small set of ~25 English→ISL gloss example pairs directly into gloss_generator.py in Step 4, using the two established ISL grammar rules (wh-words sentence-final, drop copula/linking verbs). This removes an entire failure-prone download from the project with no real loss of quality for a prompting-based approach.

Before the user downloads anything, write backend/verify/verify_datasets.py — a script that checks each of the four folders exists, is non-empty, and prints a file count per folder plus a PASS/FAIL line per dataset. The user runs this themselves after downloading and pastes you the output.

Confirmation required: the user pastes the actual script output showing PASS for all four folders.

WAITING FOR USER — DO NOT PROCEED


STEP 2 — [AGENT] Captions module

Build backend/pipeline/captions.py using youtube-transcript-api. Function get_captions(youtube_url) returns [{start, end, text}], raises a clear exception if no captions exist. Include a __main__ test block on a known captioned video. Run it yourself and show the real output in your status report (this step has no manual dependency, so you may verify it yourself and report results — no waiting needed here).


STEP 3 — [AGENT] ASR fallback module

Build backend/pipeline/asr_fallback.py using yt-dlp + ffmpeg + local openai-whisper. Same input/output shape as Step 2. Note to user: CPU-only transcription will be slow — this is expected.


STEP 4 — [AGENT, user-checked] English → ISL gloss module

Build backend/pipeline/gloss_generator.py. Requirements:


Normalize output consistently: .strip().upper(), no punctuation
Apply these four explicit rules in the prompt (not left implicit):

Wh-words (WHAT/WHERE/WHO/WHEN/WHY/HOW) always go last in the sentence
Copula/linking verbs (is/am/are/was/were/be/being) are always dropped
Continuous/progressive aspect is always dropped (-ing → base verb form, e.g. "doing" → "DO", "reading" → "READ")
Negation word always goes immediately after the verb/predicate it negates, never before (e.g. "PRESENT NOT", "WORRY NOT")
Prepositions become postpositions: the relevant noun comes first, the relation word after it (e.g. "on the floor" → "FLOOR ON", "in the class" → "CLASS IN")
Time words (TODAY, TOMORROW, YESTERDAY, NOW) go at the very beginning of the sentence, before the subject
Modals expressing ability/intent/permission (WANT, CAN, WILL-as-intent) are retained (unlike copulas) and placed after the main verb, at/near the end of the sentence



Few-shot examples: hand-write ~25 English→gloss example pairs directly as a Python list/constant in this file, covering statements, wh-questions, negation, postpositions, modals, and time words, all following the rules above consistently. Example pairs to include or model closely: "Where do you live?" → "YOU LIVE WHERE"; "Today is a holiday." → "TODAY HOLIDAY"; "My dog is sleeping on the floor." → "MY DOG FLOOR ON SLEEP"; "I want to go to the park." → "I PARK TO GO WANT"; "He was not present in the class." → "HE CLASS IN PRESENT NOT". Do not attempt to download a gloss-pair dataset for this — none of the free ones are reliably downloadable, and a well-constructed hand-written few-shot set works fine for prompting.
Call local Ollama only, no paid API


Run a test on 10 sample sentences and print input/output side by side in your status report.

Confirmation required: the user reads the 10 outputs and replies either GLOSS OK or lists specific lines that look wrong.

WAITING FOR USER — DO NOT PROCEED


STEP 5 — [AGENT] Three-tier sign lookup

Build backend/pipeline/pose_matcher.py with:


A single normalize() function applied identically to both dataset labels and gloss words (case, whitespace, underscores) — print the first 30 normalized dataset labels next to 10 gloss words in your status report as proof this matches before calling the step done
Tier 1: exact match against combined labels from /data/isl-words-landmarks/, /data/isl-word-videos/, and /data/isl-csltr/
Tier 2: lemmatize (nltk WordNetLemmatizer, free) and retry Tier 1
Tier 3: fingerspelling — split into letters, look up each in /data/fingerspelling/


Build backend/pipeline/keypoint_extractor.py:


For words matched in /data/isl-words-landmarks/: landmarks are already extracted — just load and parse the existing file, no MediaPipe run needed
For words matched only in /data/isl-word-videos/ or /data/isl-csltr/ (raw video, no pre-extracted landmarks): run MediaPipe Holistic on the clip
MediaPipe Hands for static fingerspelling images, cached once at startup since they never change
Disk cache for all extracted keypoints keyed by clip/letter filename, so repeat lookups never re-run MediaPipe


Report match/lemma-match/fingerspell/unmatched counts on a real test sentence set.


STEP 6 — [MANUAL, agent-verified] Avatar creation

This step is already complete. Do not ask the user to create a new avatar. The user has already:


Created a full-body avatar in VRoid Studio (free desktop app)
Exported it as VRM format with bone reduction set to 0 (no bone stripping)
Manually imported the exported file into Blender using the free official VRM add-on (search "VRM format" in Blender's Get Extensions)
Verified in Pose Mode, by clicking individual bone segments, that both hands have full 5-finger chains with real per-finger bone names, confirmed pattern: J_Bip_L_[Finger][1/2/3] and J_Bip_R_[Finger][1/2/3] (e.g. J_Bip_R_Index2 was directly confirmed by clicking a bone segment and reading the name in the N-panel Item tab)


The file is avatar.vrm, not .glb. Your only remaining task for this step is:

Write backend/verify/verify_avatar_rig.py. Since this is a .vrm file (which is glTF-based internally), you can still use pygltflib to open it and read node/bone names, but check specifically for the confirmed naming pattern J_Bip_L_ / J_Bip_R_ combined with finger keywords (Thumb, Index, Middle, Ring, Little), not generic Mixamo/RPM-style names like "LeftHandThumb1". This script must:


Load the .vrm and print every bone/node name found
Explicitly check for at least 3 finger-bone segments per finger, on both J_Bip_L_ and J_Bip_R_ prefixed hands
Print PASS: finger bones found or FAIL: no finger bones found — this rig cannot animate sign language, get a different export


Confirmation required: the user places avatar.vrm in backend/models/, runs this script themselves, and pastes the actual PASS/FAIL output. Given the manual Blender verification already performed, this is expected to PASS — but the script result is still what determines completion, not the user's prior description of what they saw in Blender.

WAITING FOR USER — DO NOT PROCEED


STEP 7 — [AGENT] Keypoint-to-rig mapping

Only after Step 6 passes verification: build backend/pipeline/rig_mapper.py. Read actual bone names from the verified .vrm (don't hardcode assumed names beyond the confirmed J_Bip_L_/J_Bip_R_ prefix pattern — still read them programmatically rather than assuming every index/count). Map word-level keypoint sequences to bone rotations. For fingerspelling, hold each letter's static pose ~300–400ms with brief interpolation between letters. Interpolate between the end pose of one sign and the start of the next for word-level clips too, to avoid jerky cuts.


STEP 8 — [AGENT] Backend API

Build backend/app.py (FastAPI). POST /translate runs Steps 2–7 in order, returns gloss sequence with per-word tier info (word / lemma / fingerspell), animation data, and unmatched list. Cache by video ID in SQLite. Serve avatar.vrm via a real FastAPI route (not a bare static mount) so CORS headers apply correctly. Handle non-ASCII caption text safely (encode-safe logging) to avoid crashes on music-note/special characters.


STEP 9 — [AGENT] Chrome extension

Build Manifest V3 extension: content script detects YouTube's player, injects "Use avatar" button and bottom-right overlay div. Bundle Three.js and @pixiv/three-vrm locally (no CDN, per Manifest V3 restrictions) — use @pixiv/three-vrm to load avatar.vrm rather than the plain GLTFLoader, since it correctly interprets VRM's Humanoid bone-mapping layer. Sync avatar frame to the video's timeupdate event. Show distinct UI states: loading, signing, fingerspelling (small "spelling..." label), error — never leave the UI stuck on a generic spinner with no timeout/error handling.


STEP 10 — [AGENT, user-run] End-to-end test

Ask the user for 3–5 real captioned video URLs. Pre-process them so they're cached. Ask the user to test each in Chrome and report: does the overlay appear, does the avatar move, does it fingerspell visibly on unmatched words, does it stay in sync on pause/seek.

Confirmation required: user reports pass/fail per video.

WAITING FOR USER — DO NOT PROCEED


STEP 11 — [MANUAL, optional] Publish

Only if the user wants public distribution: one-time Chrome Web Store developer fee (~$5), the only real-world cost in this entire project. Otherwise "Load Unpacked" is the final state — no further action needed.


PART 3 — Master checklist

StepTypeGate before proceeding0MANUALUser types STEP 0 DONE1MANUAL, agent-verifiedUser pastes verify_datasets.py output, all PASS2AGENTnone3AGENTnone4AGENT, user-checkedUser replies GLOSS OK or lists issues5AGENTnone6MANUAL, agent-verified (avatar already created — verification script confirms it)User pastes verify_avatar_rig.py output, must say PASS7AGENTnone (requires Step 6 PASS)8AGENTnone9AGENTnone10AGENT, user-runUser reports pass/fail per test video11MANUAL, optionalUser decision

If you are the agent reading this: your very first action is to output the Step 0 instructions and then print the exact line WAITING FOR USER — DO NOT PROCEED and stop. Do not scaffold any folders, files, or code before Step 0 is confirmed.