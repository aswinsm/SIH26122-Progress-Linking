import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from pypdf import PdfReader

project_root = Path(__file__).resolve().parents[2]

env_file = project_root / ".env"

load_dotenv(env_file)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in .env")

client = genai.Client(api_key=api_key)

class DPRData(BaseModel):
    activity_description: Optional[str] = None
    discipline: Optional[str] = None
    status: Optional[str] = None
    tag: Optional[str] = None
    date: Optional[str] = None

def extract_text_from_pdf(pdf_path):
    reader=PdfReader(pdf_path)
    text=""
    for page in reader.pages:
        page_text=page.extract_text()
        if page_text:
            text+=page_text + "\n"

        return text

def extract_dpr(dpr_text):

    prompt = f"""
You are an engineering Daily Progress Report (DPR) extraction assistant.

Your job is to read a DPR, even if the text is messy, poorly formatted,
abbreviated, or written in an informal way, and extract the required
information.

Extract EXACTLY these five fields:

1. activity_description
2. discipline
3. status
4. tag
5. date


IMPORTANT RULES:

- Read the entire DPR before extracting information.
- The DPR may be clean, messy, abbreviated, or poorly formatted.
- Understand the meaning of the text instead of depending only on exact labels.
- Extract information only when it is supported by the DPR.
- NEVER invent or guess missing information.
- If a field is genuinely missing, return null.
- Keep activity_description concise and meaningful.
- Convert the date to YYYY-MM-DD whenever possible.
- Preserve equipment, line, foundation, structure, or work identifiers
  when they are clearly given as the tag.
- For status, use simple values such as:
  Completed
  In Progress
  Started
  Delayed
  Not Started
- If the DPR clearly indicates completion using phrases such as
  "finished", "completed", "work done", or "completed successfully",
  use "Completed".
- If the DPR says work is currently happening, use "In Progress".
- Do not confuse progress quantity with status.
- Do not include explanations outside the required structured output.


DPR TEXT:

{dpr_text}
"""

    interaction = client.interactions.create(
        model="gemini-3.8-flash",
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": DPRData.model_json_schema(),
        },
    )

    return DPRData.model_validate_json(interaction.output_text)

if __name__ == "__main__":

    test_dpr = """
    DAILY PROGRESS REPORT

    Project: Oil India Infrastructure Project

    04/09/2026

    Piping work - Line 24-XX.

    Today three spools were erected during the shift.
    Work was completed successfully.

    Supervisor says piping erection activities for 24-XX
    were completed without any major issues.
    """

    result = extract_dpr(test_dpr)

    print("\nDPR EXTRACTION RESULT:")
    print(result.model_dump_json(indent=2)) 

   
if __name__ == "__main__":

    pdf_path = r"data/sample_DPR.pdf"

    text = extract_text_from_pdf(pdf_path)

    print("\nEXTRACTED PDF TEXT:")
    print(text)
   