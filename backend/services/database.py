import os
from datetime import date
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from supabase import Client, create_client


# ============================================================
# ENVIRONMENT SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_SECRET_KEY = os.getenv(
    "SUPABASE_SECRET_KEY"
)


if not SUPABASE_URL:
    raise ValueError(
        "SUPABASE_URL is missing from .env"
    )


if not SUPABASE_SECRET_KEY:
    raise ValueError(
        "SUPABASE_SECRET_KEY is missing from .env"
    )


supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


# ============================================================
# HELPER
# ============================================================

def get_first_row(
    data: Any,
    error_message: str
) -> dict[str, Any]:

    if not data:
        raise RuntimeError(
            error_message
        )

    return cast(
        dict[str, Any],
        data[0]
    )


# ============================================================
# CREATE PROGRESS REPORT
# ============================================================

def create_progress_report(
    raw_text: str,
    source_type: str,
    discipline: str | None = None,
    report_date: str | None = None
) -> dict[str, Any]:

    if not raw_text.strip():
        raise ValueError(
            "Progress report text cannot be empty."
        )


    if report_date is None:
        report_date = (
            date.today().isoformat()
        )


    payload = {
        "raw_text": raw_text,
        "discipline": discipline,
        "report_date": report_date,
        "source_type": source_type,
    }


    response = (
        supabase
        .table("progress_reports")
        .insert(payload)
        .execute()
    )


    return get_first_row(
        response.data,
        "Could not save progress report to Supabase."
    )


# ============================================================
# CREATE ACTIVITY MATCH
# ============================================================

def create_activity_match(
    report_id: int,
    extracted_activity: dict[str, Any],
    matching: dict[str, Any]
) -> dict[str, Any]:

    matches = matching.get(
        "matches",
        []
    )


    best_match = None

    if matches:
        best_match = matches[0]


    payload = {

        "report_id":
            report_id,

        "activity_id":
            (
                best_match.get(
                    "activity_id"
                )
                if best_match
                else None
            ),

        "activity_description":
            extracted_activity.get(
                "activity_description"
            ),

        "matched_activity_name":
            (
                best_match.get(
                    "activity_name"
                )
                if best_match
                else None
            ),

        "status":
            extracted_activity.get(
                "status"
            ),

        "confidence":
            matching.get(
                "confidence",
                0
            ),

        "review_status":
            "PENDING"
    }


    response = (
        supabase
        .table("activity_matches")
        .insert(payload)
        .execute()
    )


    return get_first_row(
        response.data,
        "Could not save activity match to Supabase."
    )


# ============================================================
# GET ALL MATCHES
# ============================================================

def get_all_matches() -> list[dict[str, Any]]:

    response = (
        supabase
        .table("activity_matches")
        .select("*")
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )


    return cast(
        list[dict[str, Any]],
        response.data or []
    )


# ============================================================
# GET PENDING REVIEWS
# ============================================================

def get_pending_matches() -> list[dict[str, Any]]:

    response = (
        supabase
        .table("activity_matches")
        .select("*")
        .eq(
            "review_status",
            "PENDING"
        )
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )


    return cast(
        list[dict[str, Any]],
        response.data or []
    )


# ============================================================
# GET ONE MATCH
# ============================================================

def get_activity_match(
    match_id: int
) -> dict[str, Any]:

    response = (
        supabase
        .table("activity_matches")
        .select("*")
        .eq(
            "id",
            match_id
        )
        .limit(1)
        .execute()
    )


    if not response.data:

        raise ValueError(
            f"Activity match {match_id} was not found."
        )


    return cast(
        dict[str, Any],
        response.data[0]
    )


# ============================================================
# ACCEPT MATCH
# ============================================================

def accept_activity_match(
    match_id: int
) -> dict[str, Any]:

    # Check that record exists
    get_activity_match(
        match_id
    )


    response = (
        supabase
        .table("activity_matches")
        .update({
            "review_status": "ACCEPTED"
        })
        .eq(
            "id",
            match_id
        )
        .execute()
    )


    return get_first_row(
        response.data,
        "Could not accept activity match."
    )


# ============================================================
# REJECT MATCH
# ============================================================

def reject_activity_match(
    match_id: int
) -> dict[str, Any]:

    # Check that record exists
    get_activity_match(
        match_id
    )


    response = (
        supabase
        .table("activity_matches")
        .update({
            "review_status": "REJECTED"
        })
        .eq(
            "id",
            match_id
        )
        .execute()
    )


    return get_first_row(
        response.data,
        "Could not reject activity match."
    )


# ============================================================
# CHANGE MATCH
# ============================================================

def change_activity_match(
    match_id: int,
    new_activity_id: str
) -> dict[str, Any]:

    # --------------------------------------------------------
    # CHECK EXISTING MATCH
    # --------------------------------------------------------

    get_activity_match(
        match_id
    )


    # --------------------------------------------------------
    # FIND NEW SCHEDULE ACTIVITY
    # --------------------------------------------------------

    schedule_response = (
        supabase
        .table("schedule_activities")
        .select("*")
        .eq(
            "activity_id",
            new_activity_id
        )
        .limit(1)
        .execute()
    )


    if not schedule_response.data:

        raise ValueError(
            "Schedule activity not found: "
            f"{new_activity_id}"
        )


    # Explicit type removes Pylance errors
    schedule_activity = cast(
        dict[str, Any],
        schedule_response.data[0]
    )


    new_id = schedule_activity.get(
        "activity_id"
    )

    new_name = schedule_activity.get(
        "activity_name"
    )


    if not new_id:

        raise ValueError(
            "Selected schedule activity "
            "does not contain activity_id."
        )


    # --------------------------------------------------------
    # UPDATE MATCH
    # --------------------------------------------------------

    response = (
        supabase
        .table("activity_matches")
        .update({

            "activity_id":
                new_id,

            "matched_activity_name":
                new_name,

            "review_status":
                "CHANGED"
        })
        .eq(
            "id",
            match_id
        )
        .execute()
    )


    return get_first_row(
        response.data,
        "Could not change activity match."
    )


# ============================================================
# GET SCHEDULE ACTIVITIES
# ============================================================

def get_schedule_activities() -> list[dict[str, Any]]:

    response = (
        supabase
        .table("schedule_activities")
        .select("*")
        .order(
            "activity_id"
        )
        .execute()
    )


    return cast(
        list[dict[str, Any]],
        response.data or []
    )


# ============================================================
# GET ONE SCHEDULE ACTIVITY
# ============================================================

def get_schedule_activity(
    activity_id: str
) -> dict[str, Any]:

    response = (
        supabase
        .table("schedule_activities")
        .select("*")
        .eq(
            "activity_id",
            activity_id
        )
        .limit(1)
        .execute()
    )


    if not response.data:

        raise ValueError(
            "Schedule activity not found: "
            f"{activity_id}"
        )


    return cast(
        dict[str, Any],
        response.data[0]
    )


# ============================================================
# CONNECTION TEST
# ============================================================

if __name__ == "__main__":

    response = (
        supabase
        .table("schedule_activities")
        .select("*")
        .limit(1)
        .execute()
    )


    print(
        "\n========== SUPABASE TEST ==========\n"
    )


    if response.data:

        print(
            "Supabase connection successful."
        )

        print(
            response.data[0]
        )


    else:

        print(
            "Connected successfully, "
            "but no schedule activities were found."
        )