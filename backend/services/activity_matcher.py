import pandas as pd
from rapidfuzz import process, fuzz


def match_activities():

    # Load data
    schedule = pd.read_csv("data/schedule.csv")
    dpr = pd.read_csv("data/dpr.csv")

    # Get all schedule activity names
    schedule_activities = schedule["Activity_Name"].tolist()

    print("\n========== ACTIVITY MATCHING ==========\n")

    # Match every DPR activity
    for _, row in dpr.iterrows():

        dpr_activity = row["Reported_Activity"]

        # Find best matching schedule activity
        match = process.extractOne(
            dpr_activity,
            schedule_activities,
            scorer=fuzz.token_set_ratio
        )

        matched_activity = match[0]
        confidence = match[1]

        print(f"DPR Activity: {dpr_activity}")
        print(f"Matched Schedule Activity: {matched_activity}")
        print(f"Confidence Score: {confidence:.2f}%")
        print("-" * 50)


if __name__ == "__main__":
    match_activities()