import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq


# ============================================================
# PROJECT / ENVIRONMENT SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

GROQ_AUDIO_MODEL = os.getenv(
    "GROQ_AUDIO_MODEL",
    "whisper-large-v3-turbo"
)


if not GROQ_API_KEY:

    raise ValueError(
        "GROQ_API_KEY was not found in the project .env file"
    )


client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# SUPPORTED AUDIO FORMATS
# ============================================================

SUPPORTED_AUDIO_EXTENSIONS = {
    ".flac",
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".ogg",
    ".wav",
    ".webm",
}


# ============================================================
# AUDIO TRANSCRIPTION
# ============================================================

def transcribe_audio(
    audio_path: str | Path
) -> str:

    audio_path = Path(
        audio_path
    )


    # --------------------------------------------------------
    # FILE CHECK
    # --------------------------------------------------------

    if not audio_path.exists():

        raise FileNotFoundError(
            f"Audio file not found: {audio_path}"
        )


    extension = (
        audio_path
        .suffix
        .lower()
    )


    # --------------------------------------------------------
    # FORMAT CHECK
    # --------------------------------------------------------

    if extension not in SUPPORTED_AUDIO_EXTENSIONS:

        raise ValueError(
            "Unsupported audio format: "
            f"{extension}. "
            "Supported formats are "
            "FLAC, MP3, MP4, MPEG, MPGA, "
            "M4A, OGG, WAV and WEBM."
        )


    # --------------------------------------------------------
    # GROQ WHISPER TRANSCRIPTION
    # --------------------------------------------------------

    try:

        with audio_path.open(
            "rb"
        ) as audio_file:

            transcription = (
                client.audio.transcriptions.create(

                    file=(
                        audio_path.name,
                        audio_file.read()
                    ),

                    model=GROQ_AUDIO_MODEL,

                    prompt=(
                        "This is a construction site "
                        "Daily Progress Report supervisor update. "
                        "The speaker may use engineering terms "
                        "such as concreting, reinforcement, "
                        "excavation, shuttering, formwork, "
                        "piping, welding, cable tray, "
                        "electrical installation, foundation, "
                        "equipment tags, line numbers, "
                        "structure numbers and activity IDs."
                    ),

                    response_format="json",

                    temperature=0.0
                )
            )


    except Exception as exc:

        raise RuntimeError(
            "Audio transcription failed: "
            f"{exc}"
        ) from exc


    # --------------------------------------------------------
    # GET TRANSCRIBED TEXT
    # --------------------------------------------------------

    text = getattr(
        transcription,
        "text",
        None
    )


    if (
        not text
        or not text.strip()
    ):

        raise RuntimeError(
            "No speech could be detected "
            "in the uploaded audio."
        )


    return text.strip()


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Voice processor loaded successfully."
    )

    print(
        f"Audio model: {GROQ_AUDIO_MODEL}"
    )

    print(
        "Supported formats:",
        SUPPORTED_AUDIO_EXTENSIONS
    )