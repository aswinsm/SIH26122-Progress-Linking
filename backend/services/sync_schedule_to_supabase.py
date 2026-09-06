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

    value = str(value).strip()

    if not value:
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
# DISCIPLINE INFERENCE
# ============================================================

def infer_discipline(row):

    # --------------------------------------------------------
    # USE EXISTING DISCIPLINE FIRST
    # --------------------------------------------------------

    existing = clean_value(
        row.get("discipline")
    )

    if existing:

        return existing


    # --------------------------------------------------------
    # COMBINE AVAILABLE TEXT
    # --------------------------------------------------------

    text_parts = [
        row.get("activity_name"),
        row.get("category"),
        row.get("wbs"),
    ]


    text = " ".join(

        str(value)

        for value in text_parts

        if value is not None
        and not pd.isna(value)

    ).lower()


    # ========================================================
    # ELECTRICAL
    # ========================================================

    electrical_keywords = [

        "electrical",
        "cable",
        "cabling",
        "cable tray",
        "lighting",
        "light fixture",
        "transformer",
        "switchgear",
        "panel board",
        "distribution board",
        "db installation",
        "earthing",
        "grounding",
        "power supply",
        "electrical panel",
        "electrical testing",
        "motor control",
        "mcc",
        "ups",
        "generator electrical",
    ]


    if any(
        keyword in text
        for keyword in electrical_keywords
    ):

        return "Electrical"


    # ========================================================
    # INSTRUMENTATION
    # ========================================================

    instrumentation_keywords = [

        "instrumentation",
        "instrument",
        "sensor",
        "transmitter",
        "control valve",
        "flow meter",
        "pressure gauge",
        "temperature gauge",
        "calibration",
        "loop checking",
        "loop test",
        "plc",
        "scada",
        "control system",
        "junction box",
        "instrument cable",
    ]


    if any(
        keyword in text
        for keyword in instrumentation_keywords
    ):

        return "Instrumentation"


    # ========================================================
    # PIPING
    # ========================================================

    piping_keywords = [

        "piping",
        "pipe",
        "pipeline",
        "pipe rack",
        "pipe support",
        "pipe spool",
        "spool",
        "welding",
        "hydrotest",
        "hydro test",
        "flange",
        "valve installation",
        "pipe installation",
        "pipeline installation",
        "pipe fabrication",
        "pipe erection",
    ]


    if any(
        keyword in text
        for keyword in piping_keywords
    ):

        return "Piping"


    # ========================================================
    # MECHANICAL
    # ========================================================

    mechanical_keywords = [

        "mechanical",
        "equipment",
        "pump",
        "compressor",
        "turbine",
        "motor installation",
        "machine",
        "machinery",
        "hvac",
        "duct",
        "ducting",
        "fan",
        "blower",
        "chiller",
        "boiler",
        "tank installation",
        "vessel",
        "equipment erection",
        "equipment installation",
        "alignment",
    ]


    if any(
        keyword in text
        for keyword in mechanical_keywords
    ):

        return "Mechanical"


    # ========================================================
    # HSE
    # ========================================================

    hse_keywords = [

        "hse",
        "safety",
        "health and safety",
        "toolbox talk",
        "safety inspection",
        "safety audit",
        "permit to work",
        "fire safety",
        "ppe",
        "environmental",
        "environment inspection",
        "safety training",
    ]


    if any(
        keyword in text
        for keyword in hse_keywords
    ):

        return "HSE"


    # ========================================================
    # CIVIL
    # ========================================================

    civil_keywords = [

        "civil",
        "excavation",
        "foundation",
        "concrete",
        "concreting",
        "reinforcement",
        "rebar",
        "formwork",
        "shuttering",
        "slab",
        "column",
        "beam",
        "footing",
        "pedestal",
        "retaining wall",
        "wall",
        "brickwork",
        "masonry",
        "plaster",
        "road",
        "roadwork",
        "resurfacing",
        "pavement",
        "drain",
        "drainage",
        "culvert",
        "earthwork",
        "grading",
        "backfilling",
        "backfill",
        "waterproofing",
        "structural",
        "steel reinforcement",
        "building",
        "site development",
        "survey",
        "surveying",
        "soil",
        "compaction",
        "pile",
        "piling",
    ]


    if any(
        keyword in text
        for keyword in civil_keywords
    ):

        return "Civil"


    # ========================================================
    # FALLBACK
    # ========================================================

    return "General"


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

        discipline = infer_discipline(
            row
        )


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
                discipline,

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
    # DISCIPLINE SUMMARY
    # --------------------------------------------------------

    discipline_counts = {}


    for record in records:

        discipline = record[
            "discipline"
        ]

        discipline_counts[
            discipline
        ] = (
            discipline_counts.get(
                discipline,
                0
            )
            + 1
        )


    print(
        "\nDiscipline classification:"
    )


    for discipline, count in sorted(
        discipline_counts.items()
    ):

        print(
            f"{discipline}: {count}"
        )


    # --------------------------------------------------------
    # CLEAR EXISTING SCHEDULE
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