from fastapi import FastAPI, UploadFile, File
from backend.services.dpr_extractor import (
    extract_text_from_pdf,
    extract_text_from_excel,
    extract_dpr
)
import tempfile
import os


app = FastAPI()


@app.get("/")
def home():
    return {
        "message": "DPR Extractor API is running"
    }


@app.post("/extract-dpr")
async def extract_dpr_api(file: UploadFile = File(...)):

    # Get the uploaded filename
    filename = file.filename

    # Get the file extension
    extension = os.path.splitext(filename)[1].lower()

    # Check supported file types
    if extension == ".pdf":

        suffix = ".pdf"

    elif extension in [".xlsx", ".xlsm"]:

        suffix = extension

    else:

        return {
            "error": "Unsupported file type. Please upload PDF or Excel."
        }

    # Create a temporary file
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    ) as temp_file:

        temp_file.write(await file.read())
        temp_path = temp_file.name

    try:

        # Extract text from PDF
        if extension == ".pdf":

            text = extract_text_from_pdf(temp_path)

        # Extract text from Excel
        elif extension in [".xlsx", ".xlsm"]:

            text = extract_text_from_excel(temp_path)

        # Send extracted text to Gemini
        result = extract_dpr(text)

        # Return structured DPR data
        return {
            "filename": filename,
            "file_type": extension,
            "dpr_data": result.model_dump()
        }

    finally:

        # Delete temporary file
        if os.path.exists(temp_path):

            os.remove(temp_path)