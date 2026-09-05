from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCHEDULE_DIR = PROJECT_ROOT / "data" / "schedules"

MASTER_SCHEDULE_PATH = PROJECT_ROOT / "data" / "master_schedule.csv"


# ---------------------------------------------------------
# REQUIRED / STANDARD COLUMNS
# ---------------------------------------------------------

REQUIRED_COLUMNS = [
    "activity_id",
    "activity_name",
]

OPTIONAL_COLUMNS = [
    "discipline",
    "category",
    "project_id",
    "wbs",
    "planned_start",
    "planned_finish",
]


# ---------------------------------------------------------
# COLUMN NORMALIZATION
# ---------------------------------------------------------

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:

    df.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        for column in df.columns
    ]

    # Support alternate names from different schedules
    rename_map = {
        "planned_end": "planned_finish",
        "start_date": "planned_start",
        "finish_date": "planned_finish",
        "activity_description": "activity_name",
    }

    df = df.rename(columns=rename_map)

    return df


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------

def validate_schedule(
    schedule: pd.DataFrame,
    filename: str
) -> bool:

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in schedule.columns
    ]

    if missing_columns:

        print(
            f"Skipping {filename}. "
            f"Missing required columns: {missing_columns}"
        )

        return False

    return True


# ---------------------------------------------------------
# READ ONE EXCEL FILE
# ---------------------------------------------------------

def read_schedule_file(
    file_path: Path
) -> pd.DataFrame | None:

    filename = file_path.name

    try:

        excel_file = pd.ExcelFile(file_path)

        # Prefer a sheet called "Schedule"
        if "Schedule" in excel_file.sheet_names:

            sheet_name = "Schedule"

        else:

            # Otherwise use the first sheet
            sheet_name = excel_file.sheet_names[0]

        schedule = pd.read_excel(
            file_path,
            sheet_name=sheet_name
        )

        if schedule.empty:

            print(
                f"Skipping empty schedule: {filename}"
            )

            return None

        schedule = normalize_columns(schedule)

        if not validate_schedule(
            schedule,
            filename
        ):
            return None

        # Add missing optional columns
        for column in OPTIONAL_COLUMNS:

            if column not in schedule.columns:

                schedule[column] = None

        schedule["source_file"] = filename

        return schedule

    except Exception as error:

        print(
            f"Error processing {filename}: {error}"
        )

        return None


# ---------------------------------------------------------
# LOAD ALL SCHEDULE FILES
# ---------------------------------------------------------

def load_schedules(
    schedule_directory: Path | None = None,
    save_master: bool = True
) -> pd.DataFrame:

    if schedule_directory is None:

        schedule_directory = SCHEDULE_DIR

    schedule_directory = Path(schedule_directory)

    schedule_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    files = list(
        schedule_directory.glob(
            "Infrastructure_Schedule_*.xlsx"
        )
    )

    all_schedules = []

    print(
        "\n========== SCHEDULE PROCESSING ==========\n"
    )

    for file_path in files:

        filename = file_path.name

        # Ignore obvious duplicate downloaded files
        if "(1)" in filename:
            continue

        print(
            f"Processing: {filename}"
        )

        schedule = read_schedule_file(
            file_path
        )

        if schedule is not None:

            all_schedules.append(schedule)

            print(
                f"Loaded {len(schedule)} activities"
            )

    if not all_schedules:

        print(
            "\nNo schedule files were loaded."
        )

        return pd.DataFrame()

    master_schedule = pd.concat(
        all_schedules,
        ignore_index=True
    )

    # Convert dates safely
    master_schedule["planned_start"] = (
        pd.to_datetime(
            master_schedule["planned_start"],
            errors="coerce"
        )
    )

    master_schedule["planned_finish"] = (
        pd.to_datetime(
            master_schedule["planned_finish"],
            errors="coerce"
        )
    )

    # Remove duplicate activities
    if "project_id" in master_schedule.columns:

        master_schedule = (
            master_schedule.drop_duplicates(
                subset=[
                    "project_id",
                    "activity_id"
                ]
            )
        )

    else:

        master_schedule = (
            master_schedule.drop_duplicates(
                subset=[
                    "activity_id"
                ]
            )
        )

    # Sort safely
    sort_columns = []

    if "project_id" in master_schedule.columns:
        sort_columns.append(
            "project_id"
        )

    sort_columns.append(
        "planned_start"
    )

    master_schedule = (
        master_schedule.sort_values(
            by=sort_columns,
            na_position="last"
        )
    )

    master_schedule = (
        master_schedule.reset_index(
            drop=True
        )
    )

    if save_master:

        master_schedule.to_csv(
            MASTER_SCHEDULE_PATH,
            index=False
        )

        print(
            f"\nMaster schedule saved to:\n"
            f"{MASTER_SCHEDULE_PATH}"
        )

    print(
        "\n========== PROCESSING COMPLETE ==========\n"
    )

    if "project_id" in master_schedule.columns:

        print(
            "Total Projects: "
            f"{master_schedule['project_id'].nunique()}"
        )

    print(
        f"Total Activities: {len(master_schedule)}"
    )

    return master_schedule


# ---------------------------------------------------------
# LOCAL TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    master_schedule = load_schedules()

    if not master_schedule.empty:

        display_columns = [
            column
            for column in [
                "activity_id",
                "activity_name",
                "discipline",
                "category",
                "project_id",
                "planned_start",
                "planned_finish"
            ]
            if column in master_schedule.columns
        ]

        print(
            "\n========== SAMPLE DATA ==========\n"
        )

        print(
            master_schedule[
                display_columns
            ].head(10)
        )