from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from backend.services.dpr_extractor import extract_dpr

app = FastAPI(
    title="SIH26122 Progress Linking API",
    version="0.1.0"
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

    extraction = extract_dpr(
        request.text
    )

    return {
        "received_text": request.text,
        "extracted": extraction.model_dump()
    }