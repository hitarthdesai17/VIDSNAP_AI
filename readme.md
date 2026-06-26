# VidSnap AI — Project Documentation

This document explains how the VidSnap AI backend works, function by function, and summarizes every problem encountered during development along with how each one was solved.

---

## 1. Project Overview

VidSnap AI lets a user upload a set of images/files along with a text description. The app then:
1. Converts the text into a voiceover using the ElevenLabs Text-to-Speech API
2. Stitches the uploaded images into a video using FFmpeg
3. Combines the voiceover audio with the stitched video into a final vertical "reel" (1080x1920, Instagram Reels / YouTube Shorts format)

The project has three core files:
- `main.py` — the Flask web server (handles routes, file uploads, starts background processing)
- `generate_process.py` — background worker that watches for new uploads and turns them into reels
- `text_to_audio.py` — wrapper around the ElevenLabs API for text-to-speech generation

---

## 2. `main.py` — Flask Server

### Purpose
Handles all web routes: the homepage, the create page (where uploads happen), and starts the background processing thread.

### Setup section
```python
UPLOAD_FOLDER = "user_uploads"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join("static", "reels"), exist_ok=True)
```
- `UPLOAD_FOLDER` — where raw user uploads are stored, organized by a unique ID per submission
- `ALLOWED_EXTENSIONS` — the only file types accepted (prevents arbitrary file uploads, e.g. `.exe`)
- `os.makedirs(..., exist_ok=True)` — ensures both folders exist before the app needs them, without crashing if they already exist

### `allowed_file(filename)`
Checks a filename's extension against `ALLOWED_EXTENSIONS`. Used to silently skip/reject any uploaded file that isn't a permitted image/PDF type.

### `home()` — route: `/`
Simply renders `index.html`, the landing page. No logic involved.

### `create()` — route: `/create` (GET and POST)
This is the core upload handler.

**On GET** (user just visits the page): generates a fresh UUID (`myid`) and renders the page with it. This UUID is meant to be embedded as a hidden form field, so the browser sends it back when the form is submitted.

**On POST** (user submits the form):
1. Reads `rec_id` (the UUID from the hidden form field) and `desc` (the text description for the voiceover)
2. Creates a folder `user_uploads/<rec_id>/` to hold everything for this specific submission
3. Loops through every uploaded file in `request.files`, validates its extension, sanitizes its name with `secure_filename()` (prevents path traversal attacks), and saves it into that folder
4. Writes the description text to `desc.txt` inside that folder — this is what gets converted to speech later
5. Writes `input.txt` — a file in the exact format FFmpeg's "concat demuxer" expects, listing every uploaded image with a `duration 1` (1 second per image) and repeating the last image once more (an FFmpeg quirk — without this, the final image gets cut off)
6. Writes `ready.flag` — an empty marker file written **last**, after everything else is fully saved. This signals to the background watcher that this folder is complete and safe to process. Without this, the watcher could try to process a folder while files are still mid-upload.

### `gallery()` — route: `/gallery`
Currently renders the gallery page (static for now — see note in Section 5, this has not been wired to show real generated reels yet).

### `if __name__ == "__main__":` block
```python
watcher_thread = threading.Thread(target=watch_loop, daemon=True)
watcher_thread.start()
app.run(debug=True, use_reloader=False)
```
- Starts the background watcher (`watch_loop`, imported from `generate_process.py`) as a daemon thread, so it runs continuously in the background for as long as the Flask app is alive
- `daemon=True` means this thread shuts down automatically when the main app process exits — no orphaned background processes
- `use_reloader=False` is **required**: Flask's debug mode normally auto-restarts the app on code changes by spawning a second process. Without disabling this, a second watcher thread would start too, causing every reel to be processed twice and creating race conditions

---

## 3. `generate_process.py` — Background Worker

### Purpose
Runs continuously in the background, looking for completed upload folders and turning them into finished reels (audio + video).

### `generate_audio(folder)`
1. Reads `desc.txt` from the given upload folder
2. Passes that text to `text_to_speech_file()` (from `text_to_audio.py`) to generate `audio.mp3` via ElevenLabs
3. Confirms the audio file was actually created on disk before reporting success
4. Returns `True`/`False` depending on whether audio generation succeeded

### `create_reel(folder)`
Builds and runs an FFmpeg command that:
- Reads `input.txt` (the image sequence list) using the concat demuxer
- Reads `audio.mp3` (the generated voiceover)
- Scales/pads every image to fit a 1080x1920 vertical frame (adding black bars if the aspect ratio doesn't match exactly)
- Encodes video with `libx264` and audio with `aac`
- Uses `-shortest` so the video length matches whichever of video/audio is shorter
- Outputs the final file to `static/reels/<folder>.mp4`

Returns `True`/`False` based on FFmpeg's exit code and whether the output file actually exists afterward.

### `watch_loop()`
The actual polling loop. Every 5 seconds:
1. Reads `done.txt` to get the list of folders already processed
2. Lists all folders inside `user_uploads/`
3. For each folder not already in `done.txt`:
   - Skips it if `ready.flag` doesn't exist yet (upload still in progress)
   - Calls `generate_audio()`, then `create_reel()` if audio succeeded
   - Appends the folder name to `done.txt` once processed (success or failure) — this prevents the watcher from endlessly retrying a permanently broken folder every 5 seconds forever
4. Catches any unexpected exceptions per-loop so one bad folder doesn't crash the entire watcher

### `if __name__ == "__main__":` block
Allows this file to still be run standalone for manual debugging (`python generate_process.py`), exactly as it could be used before being wired into `main.py`.

---

## 4. `text_to_audio.py` — ElevenLabs Text-to-Speech Wrapper

### Setup section
```python
load_dotenv()
API_KEY = os.getenv("ELEVENLABS_API_KEY")
elevenlabs = ElevenLabs(api_key=API_KEY)
```
Loads the API key from a local `.env` file (never hardcoded, never committed to git) and initializes the ElevenLabs client. Raises a clear error immediately on startup if the key is missing, rather than failing confusingly later.

### `text_to_speech_file(text, folder)`
1. Sends the given text to ElevenLabs' `text_to_speech.convert()` endpoint, specifying a voice ID, model, and voice settings (stability, similarity, style, speed)
2. Streams the returned audio back in chunks and writes them to `user_uploads/<folder>/audio.mp3`
3. Returns the saved file path on success, or `None` if anything goes wrong (caught and logged, not allowed to crash the caller)

---

## 5. Summary of Problems Encountered & How They Were Solved

| # | Problem | Cause | Solution |
|---|---------|-------|----------|
| 1 | `.env` file containing the ElevenLabs API key was committed and pushed to a public GitHub repo | No `.gitignore` was set up before the first commits | Revoked/rotated the exposed key immediately, removed `.env` from git tracking (`git rm --cached .env`), and added a proper `.gitignore` |
| 2 | `__pycache__/` and `user_uploads/` (test user files) were being tracked by git | Same root cause as above — no `.gitignore` existed when these were first committed | Added `__pycache__/`, `*.pyc`, and `user_uploads/` to `.gitignore`, then untracked already-committed copies with `git rm -r --cached` |
| 3 | `/create` route returned `405 Method Not Allowed` when the form was submitted | The route only accepted `GET` by default; Flask routes don't accept POST unless explicitly listed | Updated the route to `methods=["GET", "POST"]` and added logic to handle the POST case |
| 4 | App crashed with `TypeError` when the description field was empty | `request.form.get("text")` returns `None` if the field is missing, and `None` can't be written to a file | Changed to `request.form.get("text", "")` so a missing field defaults to an empty string instead of `None` |
| 5 | App could crash if the hidden UUID field wasn't submitted correctly | `rec_id = request.form.get("uuid")` could return `None`, breaking `os.path.join()` | Added a fallback: `rec_id = request.form.get("uuid") or myid` |
| 6 | Uploaded files weren't actually validated against allowed file types, despite `ALLOWED_EXTENSIONS` being defined | The variable existed but was never used in any check | Added an `allowed_file()` function and used it before saving each uploaded file |
| 7 | Audio and reel generation worked when testing manually, but never happened when uploading through the browser | `generate_process.py` was a separate standalone script with its own infinite loop. It only ran if started in a separate terminal — during browser testing, only `main.py` (Flask) was running, so nothing was watching for new uploads | Refactored `generate_process.py`'s loop into an importable `watch_loop()` function, and started it as a background daemon thread directly inside `main.py` on startup, so one command (`python main.py`) runs everything |
| 8 | Risk of the watcher processing an upload folder while files were still being written (partial/corrupted reels) | The original watcher only checked whether a folder existed, not whether the upload had fully finished | Added a `ready.flag` marker file, written only after all uploads, `desc.txt`, and `input.txt` are fully saved. The watcher now waits for this flag before processing a folder |
| 9 | Flask's debug auto-reloader risked starting a second watcher thread | By default, Flask's `debug=True` spawns a second process on every code change, which would have started its own duplicate watcher thread, causing reels to be processed twice | Added `use_reloader=False` to `app.run()` so only one process (and therefore one watcher thread) ever runs |
| 10 | The ElevenLabs API key was being printed directly to the console in `text_to_audio.py` | Leftover debug `print(API_KEY)` statement from early development | Removed the print statement; added a clear startup error instead if the key is missing, without ever exposing its value |

---

## 6. Current State of the Project

**Working:**
- Multi-file upload from the browser via the Create page
- Automatic, hands-off processing: upload → background thread → voiceover generation → FFmpeg video stitching → final reel saved to `static/reels/`
- All of this triggered by a single command: `python main.py`
- Secrets properly excluded from git via `.gitignore`

**Not yet implemented (intentionally left out of this document, to be covered separately):**
- Linking newly created reels to the Gallery page automatically

This document reflects the project as of the backend processing pipeline being completed, before gallery integration.