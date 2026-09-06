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
from backend.services.activity_matcher import ActivityMatcher


# ============================================================
# FASTAPI SETUP
# ============================================================

app = FastAPI(
    title="SIH26122 Progress Linking API",
    version="0.3.0"
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
# REQUEST MODELS
# ============================================================

class DPRRequest(BaseModel):
    text: str


# ============================================================
# ACTIVITY MATCHER
# ============================================================

# Load model + schedule once when backend starts
matcher = ActivityMatcher()


# ============================================================
# HELPER
# ============================================================

def match_extracted_activities(extraction):

    processed_activities = []

    for activity in extraction.activities:

        match_result = matcher.match_activity(
            activity_description=activity.activity_description,
            discipline=activity.discipline,
            tag=activity.tag,
            top_k=3
        )

        processed_activities.append({
            "extracted_activity": activity.model_dump(),
            "matching": match_result
        })

    return processed_activities


# ============================================================
# BASIC ROUTES
# ============================================================

@app.get("/")
def root():

    return {
        "project": "SIH26122",
        "status": "Backend is running"
    }


@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# ============================================================
# TEXT DPR
# ============================================================

@app.post("/process-dpr")
def process_dpr(request: DPRRequest):

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
            "input_type": "text",
            "received_text": request.text,
            "activities": processed_activities
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
        file.filename or "uploaded_file"
    )

    extension = Path(
        original_filename
    ).suffix.lower()


    # --------------------------------------------------------
    # VALIDATE FILE TYPE
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

        # ----------------------------------------------------
        # READ UPLOADED FILE
        # ----------------------------------------------------

        file_content = await file.read()

        if not file_content:

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )


        # ----------------------------------------------------
        # SAVE TEMPORARILY
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
        # RAYHAN DPR EXTRACTION
        # ----------------------------------------------------

        extraction = (
            extract_dpr_from_file(
                temporary_path
            )
        )


        # ----------------------------------------------------
        # SKANDAN MATCHING
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
            "input_type": "file",
            "filename": original_filename,
            "file_type": extension,
            "activities": processed_activities
        }


    except HTTPException:
        raise


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


    finally:

        # ----------------------------------------------------
        # DELETE TEMP FILE
        # ----------------------------------------------------

        if (
            temporary_path
            and os.path.exists(
                temporary_path
            )
        ):

            os.remove(
                temporary_path
            )