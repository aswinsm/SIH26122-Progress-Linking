from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.services.dpr_extractor import extract_dpr
from backend.services.activity_matcher import ActivityMatcher


app = FastAPI(
    title="SIH26122 Progress Linking API",
    version="0.2.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DPRRequest(BaseModel):
    text: str


# Load matcher once when backend starts
matcher = ActivityMatcher()


@app.get("/")
def root():
    return {
        "project": "SIH26122",
        "status": "Backend is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/process-dpr")
def process_dpr(request: DPRRequest):

    # Step 1: Rayhan's DPR extraction
    extraction = extract_dpr(
        request.text
    )

    processed_activities = []


    # Step 2: Match every extracted activity
    for activity in extraction.activities:

        match_result = matcher.match_activity(
            activity_description=activity.activity_description,
            discipline=activity.discipline,
            tag=activity.tag,
            top_k=3
        )


        processed_activities.append({
            "extracted_activity": activity.model_dump(),
            "matching": match_result
        })


    return {
        "received_text": request.text,
        "activities": processed_activities
    }