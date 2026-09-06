import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.services.dpr_extractor import (
    extract_dpr,
    extract_dpr_from_file,
)

from backend.services.activity_matcher import (
    ActivityMatcher,
)

from backend.services.voice_processor import (
    transcribe_audio,
    SUPPORTED_AUDIO_EXTENSIONS,
)


# ============================================================
# FASTAPI SETUP
# ============================================================

app = FastAPI(
    title="SIH26122 Progress Linking API",
    version="0.4.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class DPRRequest(BaseModel):
    text: str


# ============================================================
# ACTIVITY MATCHER
# ============================================================

matcher = ActivityMatcher()


# ============================================================
# MATCHING HELPER
# ============================================================

def match_extracted_activities(
    extraction
):

    processed_activities = []

    for activity in extraction.activities:

        match_result = (
            matcher.match_activity(

                activity_description=(
                    activity.activity_description
                ),

                discipline=(
                    activity.discipline
                ),

                tag=(
                    activity.tag
                ),

                top_k=3
            )
        )

        processed_activities.append({

            "extracted_activity":
                activity.model_dump(),

            "matching":
                match_result
        })

    return processed_activities


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "project": "SIH26122",
        "status": "Backend is running"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# ============================================================
# TEXT DPR
# ============================================================

@app.post("/process-dpr")
def process_dpr(
    request: DPRRequest
):

    try:

        extraction = extract_dpr(
            request.text
        )

        processed_activities = (
            match_extracted_activities(
                extraction
            )
        )

        return {

            "input_type":
                "text",

            "received_text":
                request.text,

            "activities":
                processed_activities
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# FILE DPR
# ============================================================

@app.post("/process-file")
async def process_file(
    file: UploadFile = File(...)
):

    allowed_extensions = {

        ".xlsx",
        ".xlsm",
        ".csv",
        ".pdf",
        ".txt",
    }


    original_filename = (
        file.filename
        or "uploaded_file"
    )


    extension = (
        Path(
            original_filename
        )
        .suffix
        .lower()
    )


    # --------------------------------------------------------
    # VALIDATE FILE
    # --------------------------------------------------------

    if extension not in allowed_extensions:

        raise HTTPException(

            status_code=400,

            detail=(
                "Unsupported file type. "
                "Supported formats: "
                "XLSX, XLSM, CSV, PDF and TXT."
            )
        )


    temporary_path = None


    try:

        file_content = await file.read()


        if not file_content:

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )


        # ----------------------------------------------------
        # CREATE TEMP FILE
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as temporary_file:

            temporary_file.write(
                file_content
            )

            temporary_path = (
                temporary_file.name
            )


        # ----------------------------------------------------
        # DPR EXTRACTION
        # ----------------------------------------------------

        extraction = (
            extract_dpr_from_file(
                temporary_path
            )
        )


        # ----------------------------------------------------
        # MATCHING
        # ----------------------------------------------------

        processed_activities = (
            match_extracted_activities(
                extraction
            )
        )


        return {

            "input_type":
                "file",

            "filename":
                original_filename,

            "file_type":
                extension,

            "activities":
                processed_activities
        }


    except HTTPException:

        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    finally:

        if (
            temporary_path
            and os.path.exists(
                temporary_path
            )
        ):

            os.remove(
                temporary_path
            )


# ============================================================
# VOICE / AUDIO DPR
# ============================================================

@app.post("/process-audio")
async def process_audio(
    file: UploadFile = File(...)
):

    original_filename = (
        file.filename
        or "voice_update.wav"
    )


    extension = (
        Path(
            original_filename
        )
        .suffix
        .lower()
    )


    # --------------------------------------------------------
    # VALIDATE AUDIO TYPE
    # --------------------------------------------------------

    if (
        extension
        not in SUPPORTED_AUDIO_EXTENSIONS
    ):

        raise HTTPException(

            status_code=400,

            detail=(
                "Unsupported audio format. "
                "Supported formats: "
                "FLAC, MP3, MP4, MPEG, MPGA, "
                "M4A, OGG, WAV and WEBM."
            )
        )


    temporary_path = None


    try:

        # ----------------------------------------------------
        # READ AUDIO
        # ----------------------------------------------------

        audio_content = (
            await file.read()
        )


        if not audio_content:

            raise HTTPException(
                status_code=400,
                detail="Uploaded audio file is empty."
            )


        # ----------------------------------------------------
        # MAXIMUM SIZE
        # ----------------------------------------------------

        max_size = (
            25
            * 1024
            * 1024
        )


        if len(
            audio_content
        ) > max_size:

            raise HTTPException(

                status_code=400,

                detail=(
                    "Audio file is too large. "
                    "Please upload an audio file "
                    "below 25 MB."
                )
            )


        # ----------------------------------------------------
        # TEMP AUDIO FILE
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as temporary_file:

            temporary_file.write(
                audio_content
            )

            temporary_path = (
                temporary_file.name
            )


        # ----------------------------------------------------
        # SPEECH TO TEXT
        # ----------------------------------------------------

        transcription = (
            transcribe_audio(
                temporary_path
            )
        )


        # ----------------------------------------------------
        # DPR EXTRACTION
        # ----------------------------------------------------

        extraction = extract_dpr(
            transcription
        )


        # ----------------------------------------------------
        # ACTIVITY MATCHING
        # ----------------------------------------------------

        processed_activities = (
            match_extracted_activities(
                extraction
            )
        )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "input_type":
                "voice",

            "filename":
                original_filename,

            "transcription":
                transcription,

            "activities":
                processed_activities
        }


    except HTTPException:

        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    finally:

        if (
            temporary_path
            and os.path.exists(
                temporary_path
            )
        ):

            os.remove(
                temporary_path
            )