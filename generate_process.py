import os
import time
import subprocess
from text_to_audio import text_to_speech_file


def generate_audio(folder):
    """Generate audio from desc.txt using ElevenLabs."""

    desc_path = os.path.join("user_uploads", folder, "desc.txt")

    if not os.path.exists(desc_path):
        print(f"❌ desc.txt not found for {folder}")
        return False

    with open(desc_path, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        print(f"❌ desc.txt is empty for {folder}")
        return False

    result = text_to_speech_file(text, folder)

    if result is None:
        print(f"❌ ElevenLabs call failed for {folder}")
        return False

    audio_path = os.path.join("user_uploads", folder, "audio.mp3")

    if os.path.exists(audio_path):
        print("✅ Audio generated")
        return True

    print("❌ Audio generation failed")
    return False


def create_reel(folder):
    """Create reel using FFmpeg."""

    output_file = os.path.join("static", "reels", f"{folder}.mp4")

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        os.path.join("user_uploads", folder, "input.txt"),
        "-i",
        os.path.join("user_uploads", folder, "audio.mp3"),
        "-vf",
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-shortest",
        "-r",
        "30",
        "-pix_fmt",
        "yuv420p",
        output_file,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0 and os.path.exists(output_file):
        print(f"✅ Reel created: {output_file}")
        return True

    print("❌ FFmpeg Error")
    print(result.stderr)
    return False


def watch_loop():
    """
    Background watcher. Runs forever, checking user_uploads/ for folders
    that are fully written (signaled by ready.flag) and not yet processed
    (tracked in done.txt).
    """

    os.makedirs("user_uploads", exist_ok=True)
    os.makedirs(os.path.join("static", "reels"), exist_ok=True)

    if not os.path.exists("done.txt"):
        open("done.txt", "w").close()

    print("🟢 Background watcher started")

    while True:
        try:
            with open("done.txt", "r") as f:
                done_folders = {line.strip() for line in f.readlines()}

            folders = [
                folder
                for folder in os.listdir("user_uploads")
                if os.path.isdir(os.path.join("user_uploads", folder))
            ]

            for folder in folders:

                if folder in done_folders:
                    continue

                # Only process folders that finished uploading.
                # Without this check, the watcher can grab a folder
                # mid-upload (e.g. before desc.txt or input.txt exist yet),
                # which is the kind of timing bug that's very hard to
                # reproduce when testing manually/statically.
                ready_flag = os.path.join("user_uploads", folder, "ready.flag")
                if not os.path.exists(ready_flag):
                    continue

                print(f"\n📂 Processing: {folder}")

                if not generate_audio(folder):
                    # Mark as done anyway so a permanently-broken folder
                    # (e.g. ElevenLabs quota exceeded) doesn't get retried
                    # forever every 5 seconds. Remove this if you'd rather
                    # it keep retrying.
                    with open("done.txt", "a") as f:
                        f.write(folder + "\n")
                    continue

                if create_reel(folder):
                    with open("done.txt", "a") as f:
                        f.write(folder + "\n")
                    print(f"🎉 Finished processing: {folder}")
                else:
                    with open("done.txt", "a") as f:
                        f.write(folder + "\n")

        except Exception as e:
            print("❌ Watcher loop error")
            print(e)

        time.sleep(5)


if __name__ == "__main__":
    # Still runnable standalone for debugging, exactly like before.
    watch_loop()