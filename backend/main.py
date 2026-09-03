from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="SIH26122 Progress Linking API",
    version="0.1.0"
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
    return {
        "received_text": request.text,
        "message": "DPR received successfully"
    }