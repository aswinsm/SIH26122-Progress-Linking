import pandas as pd
import glob
import os


def load_schedules():

    # Find all schedule Excel files
    files = glob.glob(
        "data/Infrastructure_Schedule_*.xlsx"
    )

    all_schedules = []

    processed_projects = set()

    print("\n========== SCHEDULE PROCESSING ==========\n")

    for file in files:

        filename = os.path.basename(file)

        # Ignore duplicate files containing (1)
        if "(1)" in filename:
            continue

        print(f"Processing: {filename}")

        try:

            # Read Schedule sheet
            schedule = pd.read_excel(
                file,
                sheet_name="Schedule"
            )

            # Add source file information
            schedule["source_file"] = filename

            # Avoid duplicate projects
            project_id = schedule["project_id"].iloc[0]

            if project_id in processed_projects:

                print(
                    f"Skipping duplicate project: "
                    f"{project_id}"
                )

                continue

            processed_projects.add(project_id)

            all_schedules.append(schedule)

            print(
                f"Loaded {len(schedule)} activities"
            )

        except Exception as error:

            print(
                f"Error processing {filename}: "
                f"{error}"
            )

    # Combine all schedules
    master_schedule = pd.concat(
        all_schedules,
        ignore_index=True
    )

    # Convert date columns
    master_schedule["planned_start"] = pd.to_datetime(
        master_schedule["planned_start"]
    )

    master_schedule["planned_end"] = pd.to_datetime(
        master_schedule["planned_end"]
    )

    # Remove duplicate activities
    master_schedule = master_schedule.drop_duplicates(
        subset=[
            "project_id",
            "activity_id"
        ]
    )

    # Sort by project and start date
    master_schedule = master_schedule.sort_values(
        by=[
            "project_id",
            "planned_start"
        ]
    )

    # Save master schedule
    master_schedule.to_csv(
        "data/master_schedule.csv",
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
        "\nMaster schedule saved to:"
    )

    print(
        "data/master_schedule.csv"
    )

    return master_schedule


if __name__ == "__main__":

    master_schedule = load_schedules()

    print("\nSample Data:\n")

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