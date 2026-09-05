import re
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer


# ============================================================
# PROJECT PATHS / CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MASTER_SCHEDULE_FILE = (
    PROJECT_ROOT / "data" / "master_schedule.csv"
)

MODEL_NAME = "all-MiniLM-L6-v2"


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):

    if text is None:
        return ""

    text = str(text).lower()

    replacements = {

        # Site preparation
        "site cleaning and preparation": "site preparation",
        "site cleaning": "site preparation",
        "site clearing": "site preparation",
        "cleaning and preparation": "site preparation",

        # Excavation
        "excavation of foundation area":
            "foundation excavation",

        # Reinforcement
        "steel reinforcement work": "reinforcement",
        "steel reinforcement": "reinforcement",
        "steel fixing": "reinforcement",
        "steel work": "reinforcement",
        "rebar": "reinforcement",

        # Foundation reinforcement
        "reinforcement work for foundation":
            "foundation reinforcement",

        "reinforcement foundation":
            "foundation reinforcement",

        # Concreting
        "concrete poured": "concreting",
        "concrete pouring": "concreting",
        "concrete work": "concreting",
        "poured concrete": "concreting",

        # Column
        "column steel fixing":
            "column reinforcement",

        "column steel":
            "column reinforcement",

        # Masonry
        "brick wall construction":
            "brick masonry",

        "brick wall":
            "brick masonry",

        "brickwork":
            "brick masonry",

        "block wall":
            "blockwork",

        # Electrical
        "electrical wiring installation":
            "electrical installation",

        "electrical wiring":
            "electrical installation",

        "wiring installation":
            "electrical installation",

        # Finishing
        "wall plastering":
            "plastering",

        "plastering work":
            "plastering",

        "building painting":
            "painting",

        "painting work":
            "painting",

        # Piping
        "spool erected":
            "pipe erection",

        "spool erection":
            "pipe erection",

        "pipe spool erection":
            "pipe erection",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"[^a-zA-Z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# CATEGORY DETECTION
# ============================================================

def detect_category(text):

    text = normalize_text(text)

    categories = {

        "site_preparation": [
            "site preparation"
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
            "earthing",
            "cable tray",
            "cable pulling"
        ],

        "piping": [
            "pipe erection",
            "piping",
            "pipeline",
            "spool",
            "welding"
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
                score += len(
                    keyword.split()
                )

        if score > best_score:

            best_score = score
            best_category = category

    return best_category


# ============================================================
# CATEGORY SIMILARITY
# ============================================================

def category_similarity(
    dpr_category,
    schedule_category
):

    if (
        dpr_category == "unknown"
        or schedule_category == "unknown"
    ):
        return 0.0

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

    related = related_categories.get(
        dpr_category,
        []
    )

    if schedule_category in related:
        return 0.60

    return 0.0


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_tag(tag):

    if tag is None:
        return ""

    return re.sub(
        r"[^A-Z0-9]",
        "",
        str(tag).upper()
    )


def tag_similarity(
    dpr_tag,
    schedule_row
):

    dpr_tag = normalize_tag(
        dpr_tag
    )

    if not dpr_tag:
        return None

    searchable_parts = [

        schedule_row.get(
            "activity_id",
            ""
        ),

        schedule_row.get(
            "activity_name",
            ""
        ),

        schedule_row.get(
            "wbs",
            ""
        ),
    ]

    searchable_text = normalize_tag(
        " ".join(
            str(part)
            for part in searchable_parts
        )
    )

    if dpr_tag in searchable_text:
        return 100.0

    return 0.0


def discipline_similarity(
    dpr_discipline,
    schedule_discipline
):

    if not dpr_discipline:
        return None

    if not schedule_discipline:
        return None

    if (
        str(dpr_discipline)
        .strip()
        .lower()
        ==
        str(schedule_discipline)
        .strip()
        .lower()
    ):

        return 100.0

    return 0.0


# ============================================================
# MATCH STATUS
# ============================================================

def get_status(
    confidence,
    confidence_gap
):

    if (
        confidence >= 75
        and confidence_gap >= 3
    ):

        return "MATCHED"

    if confidence >= 55:

        return "REVIEW"

    return "UNMATCHED"


# ============================================================
# ACTIVITY MATCHER
# ============================================================

class ActivityMatcher:

    def __init__(
        self,
        schedule_file=MASTER_SCHEDULE_FILE
    ):

        self.schedule_file = Path(
            schedule_file
        )

        if not self.schedule_file.exists():

            raise FileNotFoundError(
                "Master schedule was not found at: "
                f"{self.schedule_file}"
            )

        self.schedule_data = pd.read_csv(
            self.schedule_file
        )

        if "activity_name" not in (
            self.schedule_data.columns
        ):

            raise ValueError(
                "Master schedule must contain "
                "'activity_name'."
            )

        self.schedule_data = (
            self.schedule_data
            .dropna(
                subset=[
                    "activity_name"
                ]
            )
            .reset_index(
                drop=True
            )
        )

        # Ensure useful optional fields exist
        for column in [
            "activity_id",
            "discipline",
            "project_id",
            "category",
            "wbs"
        ]:

            if (
                column
                not in self.schedule_data.columns
            ):

                self.schedule_data[
                    column
                ] = ""

        self.schedule_data[
            "normalized_activity"
        ] = (

            self.schedule_data[
                "activity_name"
            ]
            .apply(
                normalize_text
            )
        )

        self.schedule_data[
            "detected_category"
        ] = (

            self.schedule_data[
                "activity_name"
            ]
            .apply(
                detect_category
            )
        )

        print(
            "Loading semantic matching model..."
        )

        self.model = SentenceTransformer(
            MODEL_NAME
        )

        print(
            "Creating schedule embeddings..."
        )

        self.schedule_embeddings = (
            self.model.encode(

                self.schedule_data[
                    "normalized_activity"
                ].tolist(),

                convert_to_numpy=True,

                normalize_embeddings=True
            )
        )

        print(
            "Activity matcher ready."
        )


    # ========================================================
    # MATCH ONE DPR ACTIVITY
    # ========================================================

    def match_activity(
        self,
        activity_description,
        discipline=None,
        tag=None,
        top_k=3
    ):

        if (
            not activity_description
            or not str(
                activity_description
            ).strip()
        ):

            raise ValueError(
                "activity_description "
                "cannot be empty."
            )

        normalized_dpr = normalize_text(
            activity_description
        )

        dpr_category = detect_category(
            activity_description
        )

        dpr_embedding = (
            self.model.encode(

                normalized_dpr,

                convert_to_numpy=True,

                normalize_embeddings=True
            )
        )

        semantic_scores = np.dot(

            self.schedule_embeddings,

            dpr_embedding
        )

        results = []


        for position in range(
            len(
                self.schedule_data
            )
        ):

            schedule_row = (
                self.schedule_data.iloc[
                    position
                ]
            )

            semantic_score = float(
                semantic_scores[
                    position
                ] * 100
            )

            fuzzy_score = (
                fuzz.token_set_ratio(

                    normalized_dpr,

                    schedule_row[
                        "normalized_activity"
                    ]
                )
            )

            category_score = (

                category_similarity(

                    dpr_category,

                    schedule_row[
                        "detected_category"
                    ]
                )

                * 100
            )

            tag_score = (
                tag_similarity(
                    tag,
                    schedule_row
                )
            )

            discipline_score = (
                discipline_similarity(

                    discipline,

                    schedule_row.get(
                        "discipline",
                        ""
                    )
                )
            )


            # -----------------------------------------------
            # DYNAMIC WEIGHTING
            # -----------------------------------------------

            scores = [

                (
                    semantic_score,
                    0.50
                ),

                (
                    fuzzy_score,
                    0.25
                ),

                (
                    category_score,
                    0.10
                )
            ]


            if tag_score is not None:

                scores.append(
                    (
                        tag_score,
                        0.10
                    )
                )


            if (
                discipline_score
                is not None
            ):

                scores.append(
                    (
                        discipline_score,
                        0.05
                    )
                )


            total_weight = sum(
                weight
                for _, weight
                in scores
            )


            hybrid_score = sum(

                score * weight
                for score, weight
                in scores

            ) / total_weight


            results.append({

                "activity_id":
                    schedule_row.get(
                        "activity_id",
                        ""
                    ),

                "activity_name":
                    schedule_row[
                        "activity_name"
                    ],

                "discipline":
                    schedule_row.get(
                        "discipline",
                        ""
                    ),

                "project_id":
                    schedule_row.get(
                        "project_id",
                        ""
                    ),

                "wbs":
                    schedule_row.get(
                        "wbs",
                        ""
                    ),

                "semantic_score":
                    round(
                        semantic_score,
                        2
                    ),

                "fuzzy_score":
                    round(
                        fuzzy_score,
                        2
                    ),

                "category_score":
                    round(
                        category_score,
                        2
                    ),

                "tag_score":
                    (
                        round(
                            tag_score,
                            2
                        )
                        if tag_score
                        is not None
                        else None
                    ),

                "discipline_score":
                    (
                        round(
                            discipline_score,
                            2
                        )
                        if discipline_score
                        is not None
                        else None
                    ),

                "confidence":
                    round(
                        hybrid_score,
                        2
                    )
            })


        results.sort(

            key=lambda item:
            item["confidence"],

            reverse=True
        )


        top_results = results[
            :top_k
        ]


        if not top_results:

            return {
                "status":
                    "UNMATCHED",

                "confidence":
                    0,

                "confidence_gap":
                    0,

                "matches":
                    []
            }


        best_score = (
            top_results[0][
                "confidence"
            ]
        )


        if len(
            top_results
        ) > 1:

            second_score = (
                top_results[1][
                    "confidence"
                ]
            )

        else:

            second_score = 0


        confidence_gap = round(

            best_score
            -
            second_score,

            2
        )


        status = get_status(

            best_score,

            confidence_gap
        )


        return {

            "status":
                status,

            "confidence":
                best_score,

            "confidence_gap":
                confidence_gap,

            "detected_category":
                dpr_category,

            "matches":
                top_results
        }


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    matcher = ActivityMatcher()

    result = matcher.match_activity(

        activity_description=
            "F101 concreting",

        discipline=
            "Civil",

        tag=
            "F101"
    )

    import json

    print(
        json.dumps(
            result,
            indent=2
        )
    )