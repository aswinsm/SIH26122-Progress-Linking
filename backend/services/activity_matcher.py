import pandas as pd
import numpy as np
import re

from sentence_transformers import SentenceTransformer
from rapidfuzz import fuzz


# ============================================================
# CONFIGURATION
# ============================================================

DPR_FILE = "data/dpr.csv"
SCHEDULE_FILE = "data/master_schedule.csv"
OUTPUT_FILE = "data/matched_activities.csv"

MODEL_NAME = "all-MiniLM-L6-v2"


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    text = str(text).lower()

    replacements = {

        # Site preparation
        "site cleaning and preparation": "site preparation",
        "site cleaning": "site preparation",
        "site clearing": "site preparation",
        "cleaning and preparation": "site preparation",

        # Excavation
        "excavation of foundation area": "foundation excavation",

        # Reinforcement
        "steel reinforcement work": "reinforcement",
        "steel reinforcement": "reinforcement",
        "steel fixing": "reinforcement",
        "steel work": "reinforcement",
        "rebar": "reinforcement",

        # Foundation
        "reinforcement work for foundation": "foundation reinforcement",
        "reinforcement foundation": "foundation reinforcement",

        # Concreting
        "concrete poured": "concreting",
        "concrete pouring": "concreting",
        "concrete work": "concreting",
        "poured concrete": "concreting",

        # Column
        "column steel fixing": "column reinforcement",
        "column steel": "column reinforcement",
        "steel fixing work": "reinforcement",

        # Masonry
        "brick wall construction": "brick masonry",
        "brick wall": "brick masonry",
        "brickwork": "brick masonry",
        "block wall": "blockwork",

        # Electrical
        "electrical wiring installation": "electrical installation",
        "electrical wiring": "electrical installation",
        "wiring installation": "electrical installation",

        # Finishing
        "wall plastering": "plastering",
        "plastering work": "plastering",

        "building painting": "painting",
        "painting work": "painting"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove special characters
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ============================================================
# CATEGORY DETECTION
# ============================================================

def detect_category(text):

    text = normalize_text(text)

    categories = {

        "site_preparation": [
            "site preparation",
            "site cleaning",
            "site clearing"
        ],

        "foundation_excavation": [
            "foundation excavation",
            "foundation digging"
        ],

        "excavation": [
            "excavation",
            "earthwork",
            "digging"
        ],

        "foundation_reinforcement": [
            "foundation reinforcement"
        ],

        "column_reinforcement": [
            "column reinforcement"
        ],

        "reinforcement": [
            "reinforcement",
            "steel fixing"
        ],

        "foundation_concreting": [
            "foundation concreting",
            "foundation concrete",
            "concreting foundation"
        ],

        "column_concreting": [
            "column concreting",
            "column concrete",
            "concreting columns"
        ],

        "concreting": [
            "concreting",
            "concrete"
        ],

        "foundation_formwork": [
            "foundation formwork",
            "formwork foundation",
            "shuttering foundation"
        ],

        "masonry": [
            "brick masonry",
            "masonry",
            "brickwork",
            "blockwork"
        ],

        "plastering": [
            "plastering",
            "plaster"
        ],

        "electrical": [
            "electrical installation",
            "electrical wiring",
            "electrical",
            "wiring",
            "conduit",
            "earthing"
        ],

        "painting": [
            "painting",
            "paint"
        ]
    }

    best_category = "unknown"
    best_score = 0

    for category, keywords in categories.items():

        score = 0

        for keyword in keywords:

            if keyword in text:
                score += len(keyword.split())

        if score > best_score:
            best_score = score
            best_category = category

    return best_category


# ============================================================
# CATEGORY SIMILARITY
# ============================================================

def category_similarity(dpr_category, schedule_category):

    if dpr_category == "unknown":
        return 0.0

    if schedule_category == "unknown":
        return 0.0

    # Exact category match
    if dpr_category == schedule_category:
        return 1.0

    related_categories = {

        "foundation_excavation": [
            "excavation"
        ],

        "excavation": [
            "foundation_excavation"
        ],

        "foundation_reinforcement": [
            "reinforcement"
        ],

        "column_reinforcement": [
            "reinforcement"
        ],

        "reinforcement": [
            "foundation_reinforcement",
            "column_reinforcement"
        ],

        "foundation_concreting": [
            "concreting"
        ],

        "column_concreting": [
            "concreting"
        ],

        "concreting": [
            "foundation_concreting",
            "column_concreting"
        ]
    }

    if dpr_category in related_categories:

        if schedule_category in related_categories[dpr_category]:
            return 0.60

    return 0.0


# ============================================================
# MATCH STATUS
# ============================================================

def get_status(confidence, confidence_gap):

    if confidence >= 75 and confidence_gap >= 3:
        return "MATCHED"

    elif confidence >= 60:
        return "REVIEW"

    elif confidence >= 50 and confidence_gap >= 3:
        return "REVIEW"

    else:
        return "UNMATCHED"


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print("\n========== AI ACTIVITY MATCHER ==========\n")


    # --------------------------------------------------------
    # LOAD DPR DATA
    # --------------------------------------------------------

    print("Loading DPR data...")

    dpr_data = pd.read_csv(DPR_FILE)

    print(f"Loaded DPR records: {len(dpr_data)}")


    # --------------------------------------------------------
    # LOAD SCHEDULE DATA
    # --------------------------------------------------------

    print("Loading schedule data...")

    schedule_data = pd.read_csv(SCHEDULE_FILE)

    print(f"Loaded schedule activities: {len(schedule_data)}")


    # --------------------------------------------------------
    # FIND DPR ACTIVITY COLUMN
    # --------------------------------------------------------

    possible_columns = [

        "Reported_Activity",
        "reported_activity",
        "activity",
        "Activity",
        "activity_name"
    ]

    dpr_activity_column = None

    for column in possible_columns:

        if column in dpr_data.columns:

            dpr_activity_column = column
            break


    if dpr_activity_column is None:

        print("\nERROR!")

        print(
            "Could not find the DPR activity column."
        )

        print(
            f"Available columns: {dpr_data.columns.tolist()}"
        )

        return


    print(
        f"DPR Activity Column: {dpr_activity_column}"
    )


    # --------------------------------------------------------
    # VALIDATE SCHEDULE DATA
    # --------------------------------------------------------

    if "activity_name" not in schedule_data.columns:

        print("\nERROR!")

        print(
            "Schedule file does not contain activity_name."
        )

        print(
            f"Available columns: "
            f"{schedule_data.columns.tolist()}"
        )

        return


    # Remove empty activities
    schedule_data = schedule_data.dropna(
        subset=["activity_name"]
    ).copy()

    # Reset index to avoid indexing problems
    schedule_data = schedule_data.reset_index(
        drop=True
    )


    # --------------------------------------------------------
    # NORMALIZE SCHEDULE ACTIVITIES
    # --------------------------------------------------------

    print("\nPreparing schedule activities...")

    schedule_data["normalized_activity"] = (

        schedule_data["activity_name"]
        .apply(normalize_text)
    )

    schedule_data["detected_category"] = (

        schedule_data["activity_name"]
        .apply(detect_category)
    )


    # --------------------------------------------------------
    # LOAD AI MODEL
    # --------------------------------------------------------

    print("\nLoading AI semantic model...")

    model = SentenceTransformer(MODEL_NAME)

    print("AI model loaded successfully!")


    # --------------------------------------------------------
    # CREATE SCHEDULE EMBEDDINGS
    # --------------------------------------------------------

    print("\nCreating schedule embeddings...")

    schedule_embeddings = model.encode(

        schedule_data[
            "normalized_activity"
        ].tolist(),

        convert_to_numpy=True,

        normalize_embeddings=True,

        show_progress_bar=True
    )

    print("Schedule embeddings created!")


    # --------------------------------------------------------
    # RESULTS STORAGE
    # --------------------------------------------------------

    matched_results = []

    matched_count = 0
    review_count = 0
    unmatched_count = 0


    print(
        "\n========== MATCHING RESULTS ==========\n"
    )


    # --------------------------------------------------------
    # PROCESS EACH DPR ACTIVITY
    # --------------------------------------------------------

    for _, dpr_row in dpr_data.iterrows():

        dpr_activity = str(
            dpr_row[dpr_activity_column]
        )


        # ----------------------------------------------------
        # NORMALIZE DPR ACTIVITY
        # ----------------------------------------------------

        normalized_dpr = normalize_text(
            dpr_activity
        )

        dpr_category = detect_category(
            dpr_activity
        )


        # ----------------------------------------------------
        # CREATE DPR EMBEDDING
        # ----------------------------------------------------

        dpr_embedding = model.encode(

            normalized_dpr,

            convert_to_numpy=True,

            normalize_embeddings=True
        )


        # ----------------------------------------------------
        # SEMANTIC SIMILARITY
        # ----------------------------------------------------

        semantic_scores = np.dot(

            schedule_embeddings,

            dpr_embedding
        )


        # ----------------------------------------------------
        # CALCULATE ALL MATCH SCORES
        # ----------------------------------------------------

        results = []


        for position in range(len(schedule_data)):

            schedule_row = schedule_data.iloc[
                position
            ]


            # Semantic similarity
            semantic_score = float(
                semantic_scores[position] * 100
            )


            # Fuzzy similarity
            fuzzy_score = fuzz.token_set_ratio(

                normalized_dpr,

                schedule_row[
                    "normalized_activity"
                ]
            )


            # Category similarity
            category_score = (

                category_similarity(

                    dpr_category,

                    schedule_row[
                        "detected_category"
                    ]

                )

                * 100
            )


            # ------------------------------------------------
            # HYBRID SCORE
            # ------------------------------------------------

            hybrid_score = (

                semantic_score * 0.60

                +

                fuzzy_score * 0.25

                +

                category_score * 0.15
            )


            results.append({

                "activity_name":

                    schedule_row[
                        "activity_name"
                    ],


                "activity_id":

                    schedule_row.get(
                        "activity_id",
                        ""
                    ),


                "project_id":

                    schedule_row.get(
                        "project_id",
                        ""
                    ),


                "schedule_category":

                    schedule_row.get(
                        "category",
                        ""
                    ),


                "detected_category":

                    schedule_row[
                        "detected_category"
                    ],


                "semantic_score":

                    semantic_score,


                "fuzzy_score":

                    fuzzy_score,


                "category_score":

                    category_score,


                "hybrid_score":

                    hybrid_score
            })


        # ----------------------------------------------------
        # SORT RESULTS
        # ----------------------------------------------------

        results.sort(

            key=lambda item:
            item["hybrid_score"],

            reverse=True
        )


        # ----------------------------------------------------
        # BEST MATCH
        # ----------------------------------------------------

        best_match = results[0]

        second_match = results[1]


        confidence = best_match[
            "hybrid_score"
        ]


        confidence_gap = (

            best_match[
                "hybrid_score"
            ]

            -

            second_match[
                "hybrid_score"
            ]
        )


        status = get_status(

            confidence,

            confidence_gap
        )


        # ----------------------------------------------------
        # PRINT RESULTS
        # ----------------------------------------------------

        print(
            f"DPR Activity: {dpr_activity}"
        )


        print(
            f"Normalized: {normalized_dpr}"
        )


        print(
            f"Detected Category: {dpr_category}"
        )


        print("\nTop 3 AI Matches:")


        for rank, result in enumerate(
            results[:3],
            start=1
        ):

            print(

                f"{rank}. "

                f"{result['activity_name']} "

                f"[{result['project_id']}]"
            )


            print(

                f"   Semantic: "

                f"{result['semantic_score']:.2f}% "

                f"| Fuzzy: "

                f"{result['fuzzy_score']:.2f}% "

                f"| Category: "

                f"{result['category_score']:.2f}% "

                f"| Hybrid: "

                f"{result['hybrid_score']:.2f}%"
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
            f"Confidence Gap: "
            f"{confidence_gap:.2f}%"
        )


        print(
            f"Status: {status}"
        )


        print("-" * 65)


        # ----------------------------------------------------
        # COUNT RESULTS
        # ----------------------------------------------------

        if status == "MATCHED":

            matched_count += 1


        elif status == "REVIEW":

            review_count += 1


        else:

            unmatched_count += 1


        # ----------------------------------------------------
        # CREATE OUTPUT RECORD
        # ----------------------------------------------------

        result_record = {

            "dpr_activity":

                dpr_activity,


            "normalized_activity":

                normalized_dpr,


            "detected_dpr_category":

                dpr_category,


            "matched_activity":

                best_match[
                    "activity_name"
                ],


            "activity_id":

                best_match[
                    "activity_id"
                ],


            "project_id":

                best_match[
                    "project_id"
                ],


            "schedule_category":

                best_match[
                    "schedule_category"
                ],


            "semantic_score":

                round(

                    best_match[
                        "semantic_score"
                    ],

                    2
                ),


            "fuzzy_score":

                round(

                    best_match[
                        "fuzzy_score"
                    ],

                    2
                ),


            "category_score":

                round(

                    best_match[
                        "category_score"
                    ],

                    2
                ),


            "confidence":

                round(

                    confidence,

                    2
                ),


            "confidence_gap":

                round(

                    confidence_gap,

                    2
                ),


            "status":

                status
        }


        # ----------------------------------------------------
        # ADD ORIGINAL DPR DATA
        # ----------------------------------------------------

        for column in dpr_data.columns:

            result_record[
                f"dpr_{column}"
            ] = dpr_row[column]


        matched_results.append(
            result_record
        )


    # --------------------------------------------------------
    # SAVE RESULTS
    # --------------------------------------------------------

    results_df = pd.DataFrame(
        matched_results
    )


    results_df.to_csv(

        OUTPUT_FILE,

        index=False
    )


    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print(
        "\n========== MATCHING COMPLETE ==========\n"
    )


    print(
        f"Total DPR Activities: {len(results_df)}"
    )


    print(
        f"Matched: {matched_count}"
    )


    print(
        f"Review Required: {review_count}"
    )


    print(
        f"Unmatched: {unmatched_count}"
    )


    print(
        f"\nResults saved to:\n{OUTPUT_FILE}"
    )


# ============================================================
# RUN PROGRAM
# ============================================================

if __name__ == "__main__":

    main()