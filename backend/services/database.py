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

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")


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
        report_date = date.today().isoformat()

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

    best_match = (
        matches[0]
        if matches
        else None
    )

    progress_percent = extracted_activity.get(
        "progress_percent"
    )

    if progress_percent is not None:

        progress_percent = max(
            0.0,
            min(
                100.0,
                float(progress_percent)
            )
        )

    payload = {

        "report_id":
            report_id,

        "activity_id":
            (
                best_match.get("activity_id")
                if best_match
                else None
            ),

        "activity_description":
            extracted_activity.get(
                "activity_description"
            ),

        "matched_activity_name":
            (
                best_match.get("activity_name")
                if best_match
                else None
            ),

        "status":
            extracted_activity.get(
                "status"
            ),

        "progress_percent":
            progress_percent,

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
            "id",
            desc=True
        )
        .execute()
    )

    return cast(
        list[dict[str, Any]],
        response.data or []
    )


# ============================================================
# GET PENDING MATCHES
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
            "id",
            desc=True
        )
        .execute()
    )

    return cast(
        list[dict[str, Any]],
        response.data or []
    )


# ============================================================
# GET ACTIVITY MATCH
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
# GET PROGRESS REPORT
# ============================================================

def get_progress_report(
    report_id: int
) -> dict[str, Any]:

    response = (
        supabase
        .table("progress_reports")
        .select("*")
        .eq(
            "id",
            report_id
        )
        .limit(1)
        .execute()
    )

    if not response.data:

        raise ValueError(
            f"Progress report {report_id} was not found."
        )

    return cast(
        dict[str, Any],
        response.data[0]
    )


# ============================================================
# GET REPORT DATE
# ============================================================

def get_report_date(
    report_id: int | None
) -> str | None:

    if not report_id:
        return None

    response = (
        supabase
        .table("progress_reports")
        .select("report_date")
        .eq(
            "id",
            report_id
        )
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    report = cast(
        dict[str, Any],
        response.data[0]
    )

    return report.get(
        "report_date"
    )


# ============================================================
# APPLY APPROVED DPR TO SCHEDULE
# ============================================================

def apply_match_to_schedule(
    match: dict[str, Any]
) -> dict[str, Any] | None:

    activity_id = match.get(
        "activity_id"
    )

    report_id = match.get(
        "report_id"
    )

    status = match.get(
        "status"
    )

    reported_progress = match.get(
        "progress_percent"
    )


    if not activity_id:
        return None


    # --------------------------------------------------------
    # GET CURRENT SCHEDULE ACTIVITY
    # --------------------------------------------------------

    schedule_response = (
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


    if not schedule_response.data:

        raise ValueError(
            "Schedule activity not found: "
            f"{activity_id}"
        )


    schedule_activity = cast(
        dict[str, Any],
        schedule_response.data[0]
    )


    report_date = get_report_date(
        report_id
    )


    update_data: dict[str, Any] = {}


    # ========================================================
    # NUMERIC PROGRESS FROM DPR
    # ========================================================

    if reported_progress is not None:

        progress_value = max(
            0.0,
            min(
                100.0,
                float(reported_progress)
            )
        )


        update_data[
            "progress_percent"
        ] = progress_value


        # Any positive physical progress means
        # the activity has actually started.
        if (
            progress_value > 0
            and not schedule_activity.get(
                "actual_start"
            )
            and report_date
        ):

            update_data[
                "actual_start"
            ] = report_date


        # 100% means activity finished.
        if (
            progress_value >= 100
            and report_date
        ):

            update_data[
                "actual_finish"
            ] = report_date


    # ========================================================
    # COMPLETED WITHOUT EXPLICIT %
    # ========================================================

    elif status == "Completed":

        update_data[
            "progress_percent"
        ] = 100


        if (
            not schedule_activity.get(
                "actual_start"
            )
            and report_date
        ):

            update_data[
                "actual_start"
            ] = report_date


        if report_date:

            update_data[
                "actual_finish"
            ] = report_date


    # ========================================================
    # NOT STARTED
    # ========================================================

    elif status == "Not Started":

        update_data[
            "progress_percent"
        ] = 0


    # ========================================================
    # STARTED
    # ========================================================

    if status == "Started":

        if (
            not schedule_activity.get(
                "actual_start"
            )
            and report_date
        ):

            update_data[
                "actual_start"
            ] = report_date


    # ========================================================
    # IN PROGRESS
    # ========================================================

    if status == "In Progress":

        if (
            not schedule_activity.get(
                "actual_start"
            )
            and report_date
        ):

            update_data[
                "actual_start"
            ] = report_date

        # No fake percentage is added.
        # If DPR doesn't quantify progress,
        # existing progress stays unchanged.


    # ========================================================
    # DELAYED
    # ========================================================

    # Delayed also does not automatically
    # alter physical progress.


    if not update_data:

        return schedule_activity


    # --------------------------------------------------------
    # UPDATE SCHEDULE
    # --------------------------------------------------------

    response = (
        supabase
        .table("schedule_activities")
        .update(
            update_data
        )
        .eq(
            "activity_id",
            activity_id
        )
        .execute()
    )


    return get_first_row(
        response.data,
        "Could not update schedule activity."
    )


# ============================================================
# ACCEPT MATCH
# ============================================================

def accept_activity_match(
    match_id: int
) -> dict[str, Any]:

    get_activity_match(
        match_id
    )


    response = (
        supabase
        .table("activity_matches")
        .update({
            "review_status":
                "ACCEPTED"
        })
        .eq(
            "id",
            match_id
        )
        .execute()
    )


    accepted_match = get_first_row(
        response.data,
        "Could not accept activity match."
    )


    apply_match_to_schedule(
        accepted_match
    )


    return accepted_match


# ============================================================
# REJECT MATCH
# ============================================================

def reject_activity_match(
    match_id: int
) -> dict[str, Any]:

    get_activity_match(
        match_id
    )


    response = (
        supabase
        .table("activity_matches")
        .update({
            "review_status":
                "REJECTED"
        })
        .eq(
            "id",
            match_id
        )
        .execute()
    )


    # Rejected data does NOT affect schedule.

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

    get_activity_match(
        match_id
    )


    # --------------------------------------------------------
    # FIND PLANNER-SELECTED SCHEDULE ACTIVITY
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
    # CHANGE LINK
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


    changed_match = get_first_row(
        response.data,
        "Could not change activity match."
    )


    apply_match_to_schedule(
        changed_match
    )


    return changed_match


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
# GET LATEST PROCESSED RESULT
# ============================================================

def get_latest_processing_result() -> dict[str, Any] | None:

    # --------------------------------------------------------
    # GET LATEST REPORT
    # --------------------------------------------------------

    report_response = (
        supabase
        .table("progress_reports")
        .select("*")
        .order(
            "id",
            desc=True
        )
        .limit(1)
        .execute()
    )


    if not report_response.data:

        return None


    report = cast(
        dict[str, Any],
        report_response.data[0]
    )


    report_id = report.get(
        "id"
    )


    if report_id is None:

        return None


    # --------------------------------------------------------
    # GET MATCHES FOR THIS REPORT
    # --------------------------------------------------------

    match_response = (
        supabase
        .table("activity_matches")
        .select("*")
        .eq(
            "report_id",
            report_id
        )
        .order(
            "id"
        )
        .execute()
    )


    match_rows = (
        match_response.data
        or []
    )


    activities = []


    for row in match_rows:

        match = cast(
            dict[str, Any],
            row
        )


        candidates = []


        if match.get(
            "activity_id"
        ):

            candidates.append({

                "activity_id":
                    match.get(
                        "activity_id"
                    ),

                "activity_name":
                    match.get(
                        "matched_activity_name"
                    ),

                "confidence":
                    match.get(
                        "confidence"
                    )
            })


        activities.append({

            "extracted_activity": {

                "activity_description":
                    match.get(
                        "activity_description"
                    ),

                "discipline":
                    report.get(
                        "discipline"
                    ),

                "status":
                    match.get(
                        "status"
                    ),

                "tag":
                    None,

                "date":
                    report.get(
                        "report_date"
                    ),

                "progress_percent":
                    match.get(
                        "progress_percent"
                    )
            },


            "matching": {

                "status":
                    match.get(
                        "review_status"
                    ),

                "confidence":
                    match.get(
                        "confidence"
                    ),

                "matches":
                    candidates
            },


            "review": {

                "match_id":
                    match.get(
                        "id"
                    ),

                "review_status":
                    match.get(
                        "review_status"
                    )
            }
        })


    return {

        "input_type":
            report.get(
                "source_type"
            ),

        "report_id":
            report_id,

        "database_saved":
            True,

        "received_text":
            report.get(
                "raw_text"
            ),

        "activities":
            activities
    }


# ============================================================
# BACKFILL OLD APPROVED REVIEWS
# ============================================================

def sync_reviewed_matches_to_schedule() -> dict[str, int]:

    response = (
        supabase
        .table("activity_matches")
        .select("*")
        .execute()
    )


    matches = (
        response.data
        or []
    )


    reviewed = 0
    updated = 0
    skipped = 0


    for row in matches:

        match = cast(
            dict[str, Any],
            row
        )


        review_status = match.get(
            "review_status"
        )


        if review_status not in {
            "ACCEPTED",
            "CHANGED"
        }:

            continue


        reviewed += 1


        try:

            result = (
                apply_match_to_schedule(
                    match
                )
            )


            if result:

                updated += 1


        except Exception as error:

            skipped += 1


            print(
                "Could not apply match "
                f"{match.get('id')}: "
                f"{error}"
            )


    return {

        "reviewed_matches":
            reviewed,

        "schedule_updates":
            updated,

        "skipped":
            skipped
    }


# ============================================================
# CLEAR ALL USER-ENTERED / PROCESSED DATA
# ============================================================

def clear_all_entered_data() -> dict[str, Any]:

    print(
        "\n========== CLEARING ENTERED DATA ==========\n"
    )


    # --------------------------------------------------------
    # DELETE ACTIVITY MATCHES FIRST
    #
    # These reference progress_reports, so they must be
    # removed before deleting progress reports.
    # --------------------------------------------------------

    match_response = (
        supabase
        .table("activity_matches")
        .delete()
        .neq(
            "id",
            -1
        )
        .execute()
    )


    matches_deleted = len(
        match_response.data
        or []
    )


    # --------------------------------------------------------
    # DELETE ALL PROGRESS REPORTS
    # --------------------------------------------------------

    report_response = (
        supabase
        .table("progress_reports")
        .delete()
        .neq(
            "id",
            -1
        )
        .execute()
    )


    reports_deleted = len(
        report_response.data
        or []
    )


    # --------------------------------------------------------
    # RESET ACTUAL DATA IN MASTER SCHEDULE
    #
    # IMPORTANT:
    # We DO NOT delete schedule_activities.
    # The 300 planned activities remain.
    # --------------------------------------------------------

    schedule_response = (
        supabase
        .table("schedule_activities")
        .update({

            "actual_start":
                None,

            "actual_finish":
                None,

            "progress_percent":
                0
        })
        .neq(
            "id",
            -1
        )
        .execute()
    )


    schedules_reset = len(
        schedule_response.data
        or []
    )


    print(
        f"Activity matches deleted: "
        f"{matches_deleted}"
    )

    print(
        f"Progress reports deleted: "
        f"{reports_deleted}"
    )

    print(
        f"Schedule activities reset: "
        f"{schedules_reset}"
    )

    print(
        "\n========== CLEAR COMPLETE ==========\n"
    )


    return {

        "activity_matches_deleted":
            matches_deleted,

        "progress_reports_deleted":
            reports_deleted,

        "schedule_activities_reset":
            schedules_reset,

        "master_schedule_preserved":
            True
    }


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