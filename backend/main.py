import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.services.dpr_extractor import (
    extract_dpr,
    extract_dpr_from_file,
    extract_text_from_excel,
    extract_text_from_csv,
    extract_text_from_pdf,
)

from backend.services.activity_matcher import ActivityMatcher

from backend.services.voice_processor import (
    transcribe_audio,
    SUPPORTED_AUDIO_EXTENSIONS,
)

from backend.services.scan_processor import (
    extract_text_from_scan,
    SUPPORTED_SCAN_EXTENSIONS,
)

from backend.services.database import (
    create_progress_report,
    create_activity_match,
    get_pending_matches,
    accept_activity_match,
    reject_activity_match,
    change_activity_match,
    get_schedule_activities,
)


# ============================================================
# FASTAPI SETUP
# ============================================================

app = FastAPI(
    title="SIH26122 Progress Linking API",
    version="0.6.0"
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


class ChangeMatchRequest(BaseModel):
    activity_id: str


# ============================================================
# ACTIVITY MATCHER
# ============================================================

matcher = ActivityMatcher()


# ============================================================
# MATCHING HELPER
# ============================================================

def match_extracted_activities(extraction):

    processed_activities = []

    for activity in extraction.activities:

        # Skip unusable extraction
        if not activity.activity_description:
            continue

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
# DATABASE SAVE HELPER
# ============================================================

def save_processing_result(
    raw_text: str,
    source_type: str,
    processed_activities: list
):

    # --------------------------------------------------------
    # DETERMINE DISCIPLINE
    # --------------------------------------------------------

    discipline = None

    for item in processed_activities:

        extracted = item.get(
            "extracted_activity",
            {}
        )

        if extracted.get("discipline"):

            discipline = extracted.get(
                "discipline"
            )

            break


    # --------------------------------------------------------
    # DETERMINE REPORT DATE
    # --------------------------------------------------------

    report_date = None

    for item in processed_activities:

        extracted = item.get(
            "extracted_activity",
            {}
        )

        if extracted.get("date"):

            report_date = extracted.get(
                "date"
            )

            break


    # --------------------------------------------------------
    # CREATE PROGRESS REPORT
    # --------------------------------------------------------

    report = create_progress_report(
        raw_text=raw_text,
        source_type=source_type,
        discipline=discipline,
        report_date=report_date
    )


    report_id = report.get(
        "id"
    )


    if report_id is None:

        raise RuntimeError(
            "Supabase did not return a report ID."
        )


    # --------------------------------------------------------
    # CREATE ACTIVITY MATCH RECORDS
    # --------------------------------------------------------

    for item in processed_activities:

        database_match = create_activity_match(
            report_id=report_id,
            extracted_activity=item[
                "extracted_activity"
            ],
            matching=item[
                "matching"
            ]
        )


        # Add database information to API response
        item["review"] = {
            "match_id": database_match.get(
                "id"
            ),
            "review_status": database_match.get(
                "review_status"
            )
        }


    return report


# ============================================================
# FILE SOURCE TEXT HELPER
# ============================================================

def get_file_source_text(
    file_path: str,
    extension: str
) -> str:

    if extension in {
        ".xlsx",
        ".xlsm"
    }:

        return extract_text_from_excel(
            file_path
        )


    elif extension == ".csv":

        return extract_text_from_csv(
            file_path
        )


    elif extension == ".pdf":

        return extract_text_from_pdf(
            file_path
        )


    elif extension == ".txt":

        return Path(
            file_path
        ).read_text(
            encoding="utf-8",
            errors="replace"
        )


    return ""


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "project": "SIH26122",
        "status": "Backend is running",
        "version": "0.6.0"
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

        if not request.text.strip():

            raise HTTPException(
                status_code=400,
                detail="DPR text cannot be empty."
            )


        # ----------------------------------------------------
        # DPR EXTRACTION
        # ----------------------------------------------------

        extraction = extract_dpr(
            request.text
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
        # SAVE TO SUPABASE
        # ----------------------------------------------------

        report = save_processing_result(
            raw_text=request.text,
            source_type="text",
            processed_activities=processed_activities
        )


        return {
            "input_type": "text",
            "report_id": report.get("id"),
            "database_saved": True,
            "received_text": request.text,
            "activities": processed_activities
        }


    except HTTPException:
        raise


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
        Path(original_filename)
        .suffix
        .lower()
    )


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
        # TEMP FILE
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
        # SAVE ORIGINAL SOURCE TEXT
        # ----------------------------------------------------

        source_text = get_file_source_text(
            temporary_path,
            extension
        )


        # ----------------------------------------------------
        # DPR EXTRACTION
        # ----------------------------------------------------

        extraction = extract_dpr_from_file(
            temporary_path
        )


        # ----------------------------------------------------
        # MATCHING
        # ----------------------------------------------------

        processed_activities = (
            match_extracted_activities(
                extraction
            )
        )


        # ----------------------------------------------------
        # SOURCE TYPE
        # ----------------------------------------------------

        source_type_map = {
            ".xlsx": "excel",
            ".xlsm": "excel",
            ".csv": "csv",
            ".pdf": "pdf",
            ".txt": "text_file"
        }


        source_type = source_type_map.get(
            extension,
            "file"
        )


        # ----------------------------------------------------
        # SAVE TO SUPABASE
        # ----------------------------------------------------

        report = save_processing_result(
            raw_text=source_text,
            source_type=source_type,
            processed_activities=processed_activities
        )


        return {
            "input_type": "file",
            "report_id": report.get("id"),
            "database_saved": True,
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
        Path(original_filename)
        .suffix
        .lower()
    )


    if extension not in SUPPORTED_AUDIO_EXTENSIONS:

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

        audio_content = await file.read()


        if not audio_content:

            raise HTTPException(
                status_code=400,
                detail="Uploaded audio file is empty."
            )


        max_size = (
            25
            * 1024
            * 1024
        )


        if len(audio_content) > max_size:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Audio file is too large. "
                    "Please upload a file below 25 MB."
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
        # TRANSCRIPTION
        # ----------------------------------------------------

        transcription = transcribe_audio(
            temporary_path
        )


        # ----------------------------------------------------
        # DPR EXTRACTION
        # ----------------------------------------------------

        extraction = extract_dpr(
            transcription
        )


        # ----------------------------------------------------
        # MATCHING
        # ----------------------------------------------------

        processed_activities = (
            match_extracted_activities(
                extraction
            )
        )


        # ----------------------------------------------------
        # SAVE TO SUPABASE
        # ----------------------------------------------------

        report = save_processing_result(
            raw_text=transcription,
            source_type="voice",
            processed_activities=processed_activities
        )


        return {
            "input_type": "voice",
            "report_id": report.get("id"),
            "database_saved": True,
            "filename": original_filename,
            "transcription": transcription,
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
# SCANNED NOTE / IMAGE DPR
# ============================================================

@app.post("/process-scan")
async def process_scan(
    file: UploadFile = File(...)
):

    original_filename = (
        file.filename
        or "scanned_note.jpg"
    )


    extension = (
        Path(original_filename)
        .suffix
        .lower()
    )


    if extension not in SUPPORTED_SCAN_EXTENSIONS:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported scanned-note format. "
                "Supported formats: "
                "JPG, JPEG, PNG, WEBP and PDF."
            )
        )


    temporary_path = None


    try:

        scan_content = await file.read()


        if not scan_content:

            raise HTTPException(
                status_code=400,
                detail="Uploaded scan is empty."
            )


        max_size = (
            20
            * 1024
            * 1024
        )


        if len(scan_content) > max_size:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Scanned file is too large. "
                    "Please upload a file below 20 MB."
                )
            )


        # ----------------------------------------------------
        # TEMP SCAN FILE
        # ----------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as temporary_file:

            temporary_file.write(
                scan_content
            )

            temporary_path = (
                temporary_file.name
            )


        # ----------------------------------------------------
        # OCR / VISION
        # ----------------------------------------------------

        scanned_text = extract_text_from_scan(
            temporary_path
        )


        # ----------------------------------------------------
        # DPR EXTRACTION
        # ----------------------------------------------------

        extraction = extract_dpr(
            scanned_text
        )


        # ----------------------------------------------------
        # MATCHING
        # ----------------------------------------------------

        processed_activities = (
            match_extracted_activities(
                extraction
            )
        )


        # ----------------------------------------------------
        # SAVE TO SUPABASE
        # ----------------------------------------------------

        report = save_processing_result(
            raw_text=scanned_text,
            source_type="scan",
            processed_activities=processed_activities
        )


        return {
            "input_type": "scan",
            "report_id": report.get("id"),
            "database_saved": True,
            "filename": original_filename,
            "ocr_text": scanned_text,
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
# GET PENDING REVIEWS
# ============================================================

@app.get("/reviews/pending")
def pending_reviews():

    try:

        reviews = get_pending_matches()


        return {
            "count": len(reviews),
            "reviews": reviews
        }


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# ACCEPT REVIEW
# ============================================================

@app.post("/reviews/{match_id}/accept")
def accept_review(
    match_id: int
):

    try:

        result = accept_activity_match(
            match_id
        )


        return {
            "message": "Match accepted.",
            "match": result
        }


    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# REJECT REVIEW
# ============================================================

@app.post("/reviews/{match_id}/reject")
def reject_review(
    match_id: int
):

    try:

        result = reject_activity_match(
            match_id
        )


        return {
            "message": "Match rejected.",
            "match": result
        }


    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# CHANGE REVIEW
# ============================================================

@app.post("/reviews/{match_id}/change")
def change_review(
    match_id: int,
    request: ChangeMatchRequest
):

    try:

        result = change_activity_match(
            match_id=match_id,
            new_activity_id=request.activity_id
        )


        return {
            "message": "Match changed.",
            "match": result
        }


    except ValueError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ============================================================
# SCHEDULE ACTIVITIES
# ============================================================

@app.get("/schedule-activities")
def schedule_activities():

    try:

        activities = (
            get_schedule_activities()
        )


        return {
            "count": len(activities),
            "activities": activities
        }


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )