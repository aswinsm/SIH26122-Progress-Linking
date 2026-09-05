import pandas as pd
import re
from rapidfuzz import process, fuzz


# Construction domain synonyms
SYNONYMS = {
    "steel fixing": "reinforcement",
    "steel work": "reinforcement",
    "steel reinforcement": "reinforcement",

    "concrete poured": "concreting",
    "concrete pouring": "concreting",
    "concrete work": "concreting",

    "brick wall construction": "brick masonry",
    "brick construction": "brick masonry",

    "wall plastering": "plastering",

    "electrical wiring": "electrical installation",

    "site cleaning and preparation": "site preparation",
    "building painting": "painting"
}


def normalize_text(text):
    """Clean and normalize activity text."""

    text = str(text).lower()

    # Remove punctuation
    text = re.sub(r"[^a-z\s]", "", text)

    # Replace construction synonyms
    for phrase, replacement in SYNONYMS.items():
        text = re.sub(
            r"\b" + re.escape(phrase) + r"\b",
            replacement,
            text
        )

    # Stop words
    stop_words = {
        "completed",
        "started",
        "progress",
        "work",
        "for",
        "of",
        "and",
        "the",
        "area",
        "in"
    }

    # Remove stop words safely
    words = text.split()

    words = [
        word for word in words
        if word not in stop_words
    ]

    # Remove duplicate words
    cleaned_words = []

    for word in words:
        if word not in cleaned_words:
            cleaned_words.append(word)

    return " ".join(cleaned_words)


def get_status(confidence):
    """Determine matching status."""

    if confidence >= 80:
        return "MATCHED"

    elif confidence >= 60:
        return "REVIEW"

    else:
        return "UNMATCHED"


def match_activities():

    # Load data
    schedule = pd.read_csv("data/schedule.csv")
    dpr = pd.read_csv("data/dpr.csv")

    # Normalize schedule activities
    schedule["Normalized_Name"] = (
        schedule["Activity_Name"]
        .apply(normalize_text)
    )

    normalized_schedule = (
        schedule["Normalized_Name"]
        .tolist()
    )

    results = []

    print("\n========== ACTIVITY MATCHING ==========\n")

    # Process every DPR activity
    for _, row in dpr.iterrows():

        original_activity = row["Reported_Activity"]

        # Normalize DPR activity
        normalized_activity = normalize_text(
            original_activity
        )

        # Get TOP 3 matches
        matches = process.extract(
            normalized_activity,
            normalized_schedule,
            scorer=fuzz.token_set_ratio,
            limit=3
        )

        # Best match
        best_match = matches[0]

        matched_name = best_match[0]
        confidence = best_match[1]

        # Find original schedule activity
        matched_row = schedule[
            schedule["Normalized_Name"] == matched_name
        ].iloc[0]

        original_schedule_name = (
            matched_row["Activity_Name"]
        )

        # Determine status
        status = get_status(confidence)

        # Store Top 3 matches
        top_matches = []

        for match in matches:

            normalized_match = match[0]
            score = match[1]

            schedule_row = schedule[
                schedule["Normalized_Name"]
                == normalized_match
            ].iloc[0]

            top_matches.append({
                "activity": schedule_row["Activity_Name"],
                "confidence": round(score, 2)
            })

        # Save result
        results.append({
            "DPR_Date": row["Date"],
            "DPR_Activity": original_activity,
            "Normalized_DPR_Activity": normalized_activity,
            "Matched_Schedule_Activity": original_schedule_name,
            "Confidence_Score": round(confidence, 2),
            "Status": status,
            "Top_3_Matches": str(top_matches)
        })

        # Print result
        print(f"DPR Activity: {original_activity}")
        print(f"Normalized: {normalized_activity}")

        print("\nTop 3 Matches:")

        for i, candidate in enumerate(
            top_matches,
            start=1
        ):
            print(
                f"{i}. "
                f"{candidate['activity']} "
                f"({candidate['confidence']}%)"
            )

        print(f"\nFinal Match: {original_schedule_name}")
        print(f"Confidence: {confidence:.2f}%")
        print(f"Status: {status}")

        print("-" * 55)

    # Convert results to DataFrame
    results_df = pd.DataFrame(results)

    # Save results
    results_df.to_csv(
        "data/matched_activities.csv",
        index=False
    )

    print(
        "\nResults saved to "
        "data/matched_activities.csv"
    )


if __name__ == "__main__":
    match_activities()