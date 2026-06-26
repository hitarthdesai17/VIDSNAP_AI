import os
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Load environment variables
load_dotenv()

API_KEY = os.getenv("ELEVENLABS_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "ELEVENLABS_API_KEY not found. Make sure your .env file exists "
        "and contains ELEVENLABS_API_KEY=your_key_here"
    )

# Create ElevenLabs client
elevenlabs = ElevenLabs(api_key=API_KEY)


def text_to_speech_file(text: str, folder: str):
    try:
        print("Generating audio...")
        print("Folder:", folder)

        response = elevenlabs.text_to_speech.convert(
            voice_id="pNInz6obpgDQGcFmaJgB",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_flash_v2_5",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
                speed=1.0,
            ),
        )

        folder_path = os.path.join("user_uploads", folder)
        os.makedirs(folder_path, exist_ok=True)

        save_file_path = os.path.join(folder_path, "audio.mp3")

        print("Saving to:", save_file_path)

        with open(save_file_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

        print("✅ Audio saved successfully!")
        return save_file_path

    except Exception as e:
        print("❌ ElevenLabs Error")
        print(type(e).__name__)
        print(e)
        return None


if __name__ == "__main__":
    text_to_speech_file(
        "Hello, this is a test generated from ElevenLabs.",
        "test"
    )