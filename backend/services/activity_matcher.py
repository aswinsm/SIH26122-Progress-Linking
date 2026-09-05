import pandas as pd
import re

from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ==========================================
# TEXT NORMALIZATION
# ==========================================

def normalize_text(text):
    """Clean activity text for fuzzy matching."""

    text = str(text).lower()

    # Remove punctuation
    text = re.sub(r"[^a-z\s]", " ", text)

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ==========================================
# MATCH STATUS
# ==========================================

def get_status(confidence):

    if confidence >= 80:
        return "MATCHED"

    elif confidence >= 60:
        return "REVIEW"

    else:
        return "UNMATCHED"


# ==========================================
# MAIN ACTIVITY MATCHING
# ==========================================

def match_activities():

    print("\n========== AI ACTIVITY MATCHING ==========\n")

    # ------------------------------------------
    # LOAD DATA
    # ------------------------------------------

    dpr = pd.read_csv(
        "data/dpr.csv"
    )

    schedule = pd.read_csv(
        "data/master_schedule.csv"
    )

    print(
        f"Loaded DPR records: {len(dpr)}"
    )

    print(
        f"Loaded schedule activities: {len(schedule)}"
    )


    # ------------------------------------------
    # NORMALIZE SCHEDULE ACTIVITIES
    # ------------------------------------------

    schedule["normalized_activity"] = (
        schedule["activity_name"]
        .apply(normalize_text)
    )

    schedule_activities = (
        schedule["normalized_activity"]
        .tolist()
    )


    # ------------------------------------------
    # LOAD NLP MODEL
    # ------------------------------------------

    print(
        "\nLoading AI semantic model..."
    )

    model = SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

    print(
        "AI model loaded successfully!"
    )


    # ------------------------------------------
    # CREATE SCHEDULE EMBEDDINGS
    # ------------------------------------------

    print(
        "\nCreating schedule embeddings..."
    )

    schedule_embeddings = model.encode(
        schedule_activities,
        convert_to_numpy=True
    )

    print(
        "Schedule embeddings created!"
    )


    results = []

    print(
        "\n========== MATCHING RESULTS ==========\n"
    )


    # ==========================================
    # MATCH EACH DPR ACTIVITY
    # ==========================================

    for _, row in dpr.iterrows():

        original_activity = row[
            "Reported_Activity"
        ]

        normalized_activity = normalize_text(
            original_activity
        )


        # ------------------------------------------
        # NLP SEMANTIC EMBEDDING
        # ------------------------------------------

        dpr_embedding = model.encode(
            [normalized_activity],
            convert_to_numpy=True
        )


        # ------------------------------------------
        # SEMANTIC SIMILARITY
        # ------------------------------------------

        semantic_scores = cosine_similarity(
            dpr_embedding,
            schedule_embeddings
        )[0]

        # Convert to percentage
        semantic_scores = (
            semantic_scores * 100
        )


        # ------------------------------------------
        # FUZZY SCORES
        # ------------------------------------------

        fuzzy_scores = []

        for schedule_activity in schedule_activities:

            score = fuzz.token_set_ratio(
                normalized_activity,
                schedule_activity
            )

            fuzzy_scores.append(score)

        fuzzy_scores = pd.Series(
            fuzzy_scores
        ).to_numpy()


        # ------------------------------------------
        # HYBRID SCORE
        # ------------------------------------------

        semantic_weight = 0.70
        fuzzy_weight = 0.30

        hybrid_scores = (
            semantic_weight * semantic_scores
            +
            fuzzy_weight * fuzzy_scores
        )


        # ------------------------------------------
        # TOP 3 MATCHES
        # ------------------------------------------

        top_indices = (
            hybrid_scores.argsort()[-3:][::-1]
        )


        top_matches = []

        for index in top_indices:

            top_matches.append({

                "activity_id":
                    schedule.iloc[index][
                        "activity_id"
                    ],

                "activity_name":
                    schedule.iloc[index][
                        "activity_name"
                    ],

                "project_id":
                    schedule.iloc[index][
                        "project_id"
                    ],

                "semantic_score":
                    round(
                        semantic_scores[index],
                        2
                    ),

                "fuzzy_score":
                    round(
                        fuzzy_scores[index],
                        2
                    ),

                "hybrid_score":
                    round(
                        hybrid_scores[index],
                        2
                    )
            })


        # ------------------------------------------
        # BEST MATCH
        # ------------------------------------------

        best_index = top_indices[0]

        best_match = schedule.iloc[
            best_index
        ]

        confidence = hybrid_scores[
            best_index
        ]

        status = get_status(
            confidence
        )


        # ------------------------------------------
        # SAVE RESULT
        # ------------------------------------------

        results.append({

            "DPR_Date":
                row.get("Date", ""),

            "DPR_Activity":
                original_activity,

            "Normalized_DPR_Activity":
                normalized_activity,

            "Matched_Activity_ID":
                best_match["activity_id"],

            "Matched_Schedule_Activity":
                best_match["activity_name"],

            "Matched_Project_ID":
                best_match["project_id"],

            "Semantic_Score":
                round(
                    semantic_scores[
                        best_index
                    ],
                    2
                ),

            "Fuzzy_Score":
                round(
                    fuzzy_scores[
                        best_index
                    ],
                    2
                ),

            "Hybrid_Score":
                round(
                    confidence,
                    2
                ),

            "Status":
                status,

            "Top_3_Matches":
                str(top_matches)
        })


        # ------------------------------------------
        # PRINT RESULTS
        # ------------------------------------------

        print(
            f"DPR Activity: {original_activity}"
        )

        print(
            f"Normalized: {normalized_activity}"
        )

        print(
            "\nTop 3 AI Matches:"
        )

        for i, match in enumerate(
            top_matches,
            start=1
        ):

            print(
                f"{i}. "
                f"{match['activity_name']} "
                f"[{match['project_id']}]"
            )

            print(
                f"   Semantic: "
                f"{match['semantic_score']}% | "
                f"Fuzzy: "
                f"{match['fuzzy_score']}% | "
                f"Hybrid: "
                f"{match['hybrid_score']}%"
            )


        print(
            f"\nFinal Match: "
            f"{best_match['activity_name']}"
        )

        print(
            f"Activity ID: "
            f"{best_match['activity_id']}"
        )

        print(
            f"Project ID: "
            f"{best_match['project_id']}"
        )

        print(
            f"Confidence: "
            f"{confidence:.2f}%"
        )

        print(
            f"Status: {status}"
        )

        print(
            "-" * 65
        )


    # ==========================================
    # SAVE RESULTS
    # ==========================================

    results_df = pd.DataFrame(
        results
    )

    output_file = (
        "data/matched_activities.csv"
    )

    results_df.to_csv(
        output_file,
        index=False
    )


    # ==========================================
    # SUMMARY
    # ==========================================

    print(
        "\n========== MATCHING COMPLETE ==========\n"
    )

    print(
        f"Total DPR Activities: {len(dpr)}"
    )

    print(
        f"Matched: "
        f"{len(results_df[results_df['Status'] == 'MATCHED'])}"
    )

    print(
        f"Review Required: "
        f"{len(results_df[results_df['Status'] == 'REVIEW'])}"
    )

    print(
        f"Unmatched: "
        f"{len(results_df[results_df['Status'] == 'UNMATCHED'])}"
    )

    print(
        f"\nResults saved to:"
    )

    print(
        output_file
    )


if __name__ == "__main__":
    match_activities()