from pathlib import Path

import pandas as pd

from backend.services.database import supabase


# ============================================================
# PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MASTER_SCHEDULE_FILE = (
    PROJECT_ROOT
    / "data"
    / "master_schedule.csv"
)


# ============================================================
# CLEAN VALUE
# ============================================================

def clean_value(value):

    if pd.isna(value):
        return None

    return value


# ============================================================
# CLEAN DATE
# ============================================================

def clean_date(value):

    if pd.isna(value):
        return None

    try:

        return (
            pd.to_datetime(value)
            .date()
            .isoformat()
        )

    except Exception:

        return None


# ============================================================
# SYNC MASTER SCHEDULE
# ============================================================

def sync_schedule():

    print(
        "\n========== SCHEDULE → SUPABASE ==========\n"
    )


    if not MASTER_SCHEDULE_FILE.exists():

        raise FileNotFoundError(
            f"Master schedule not found: "
            f"{MASTER_SCHEDULE_FILE}"
        )


    # --------------------------------------------------------
    # LOAD CSV
    # --------------------------------------------------------

    schedule = pd.read_csv(
        MASTER_SCHEDULE_FILE
    )


    print(
        f"Activities found: {len(schedule)}"
    )


    # --------------------------------------------------------
    # REQUIRED COLUMNS
    # --------------------------------------------------------

    required_columns = [
        "activity_id",
        "activity_name"
    ]


    for column in required_columns:

        if column not in schedule.columns:

            raise ValueError(
                f"Missing required column: {column}"
            )


    # --------------------------------------------------------
    # REMOVE EMPTY ACTIVITIES
    # --------------------------------------------------------

    schedule = schedule.dropna(
        subset=[
            "activity_id",
            "activity_name"
        ]
    )


    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    schedule = schedule.drop_duplicates(
        subset=[
            "activity_id"
        ]
    )


    records = []


    # --------------------------------------------------------
    # PREPARE RECORDS
    # --------------------------------------------------------

    for _, row in schedule.iterrows():

        record = {

            "activity_id":
                str(
                    row["activity_id"]
                ).strip(),

            "activity_name":
                str(
                    row["activity_name"]
                ).strip(),

            "discipline":
                clean_value(
                    row.get(
                        "discipline"
                    )
                ),

            "wbs":
                clean_value(
                    row.get(
                        "wbs"
                    )
                ),

            "planned_start":
                clean_date(
                    row.get(
                        "planned_start"
                    )
                ),

            "planned_finish":
                clean_date(
                    row.get(
                        "planned_finish"
                    )
                ),

            "actual_start":
                None,

            "actual_finish":
                None,

            "progress_percent":
                0
        }


        records.append(
            record
        )


    print(
        f"Valid activities: {len(records)}"
    )


    # --------------------------------------------------------
    # REMOVE CURRENT SAMPLE DATA
    # --------------------------------------------------------

    print(
        "\nClearing old schedule activities..."
    )


    supabase.table(
        "schedule_activities"
    ).delete().neq(
        "id",
        -1
    ).execute()


    # --------------------------------------------------------
    # INSERT IN BATCHES
    # --------------------------------------------------------

    batch_size = 100


    for start in range(
        0,
        len(records),
        batch_size
    ):

        batch = records[
            start:
            start + batch_size
        ]


        supabase.table(
            "schedule_activities"
        ).insert(
            batch
        ).execute()


        print(
            f"Inserted "
            f"{min(start + batch_size, len(records))}"
            f"/{len(records)}"
        )


    print(
        "\n========== SYNC COMPLETE ==========\n"
    )


    print(
        f"Total schedule activities uploaded: "
        f"{len(records)}"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    sync_schedule()