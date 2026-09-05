import pandas as pd
import glob
import os


def load_schedules():

    # Find all Infrastructure Schedule Excel files
    files = glob.glob(
        "data/Infrastructure_Schedule_*.xlsx"
    )

    all_schedules = []

    print("\n========== SCHEDULE PROCESSING ==========\n")

    # Process every Excel file
    for file in files:

        filename = os.path.basename(file)

        # Ignore duplicate uploaded files
        if "(1)" in filename:
            continue

        print(f"Processing: {filename}")

        try:

            # Read the Schedule sheet
            schedule = pd.read_excel(
                file,
                sheet_name="Schedule"
            )

            # Check if file contains data
            if schedule.empty:
                print("Skipping empty file")
                continue

            # Add source file column
            schedule["source_file"] = filename

            # Add schedule to list
            all_schedules.append(schedule)

            print(
                f"Loaded {len(schedule)} activities"
            )

        except Exception as error:

            print(
                f"Error processing {filename}: {error}"
            )

    # Check whether schedules were loaded
    if not all_schedules:

        print("\nNo schedule files were loaded.")

        return None

    # Combine all schedules
    master_schedule = pd.concat(
        all_schedules,
        ignore_index=True
    )

    # Convert date columns safely
    master_schedule["planned_start"] = pd.to_datetime(
        master_schedule["planned_start"],
        errors="coerce"
    )

    master_schedule["planned_end"] = pd.to_datetime(
        master_schedule["planned_end"],
        errors="coerce"
    )

    # Remove duplicate activities
    master_schedule = master_schedule.drop_duplicates(
        subset=[
            "project_id",
            "activity_id"
        ]
    )

    # Sort by project and planned start date
    master_schedule = master_schedule.sort_values(
        by=[
            "project_id",
            "planned_start"
        ]
    )

    # Reset index
    master_schedule = master_schedule.reset_index(
        drop=True
    )

    # Save master schedule
    output_file = "data/master_schedule.csv"

    master_schedule.to_csv(
        output_file,
        index=False
    )

    print("\n========== PROCESSING COMPLETE ==========\n")

    print(
        f"Total Projects: "
        f"{master_schedule['project_id'].nunique()}"
    )

    print(
        f"Total Activities: "
        f"{len(master_schedule)}"
    )

    print(
        f"\nMaster schedule saved to:"
    )

    print(output_file)

    return master_schedule


if __name__ == "__main__":

    master_schedule = load_schedules()

    # Display sample data
    if master_schedule is not None:

        print("\n========== SAMPLE DATA ==========\n")

        print(
            master_schedule[
                [
                    "activity_id",
                    "activity_name",
                    "category",
                    "project_id",
                    "planned_start",
                    "planned_end"
                ]
            ].head(10)
        )