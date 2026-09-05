import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel
from pypdf import PdfReader
from openpyxl import load_workbook


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

    reader = PdfReader(pdf_path)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text

def extract_text_from_excel(excel_path):

    workbook = load_workbook(
        excel_path,
        data_only=True
    )

    text = ""

    for sheet in workbook.worksheets:

        text += f"\n--- Sheet: {sheet.title} ---\n"

        for row in sheet.iter_rows(values_only=True):

            row_values = []

            for cell in row:

                if cell is not None:
                    row_values.append(str(cell))

            if row_values:
                text += " | ".join(row_values) + "\n"

    return text

def extract_dpr(dpr_text):

    prompt = f"""
You are an engineering Daily Progress Report (DPR) extraction assistant.

Your job is to read a DPR and extract structured information.

The DPR may be:

- Cleanly formatted
- Poorly formatted
- Messy
- Abbreviated
- Written as paragraphs
- Extracted from a PDF
- Extracted from an Excel spreadsheet

Understand the meaning of the DPR rather than depending only on
exact field names.


Extract EXACTLY these five fields:

1. activity_description
2. discipline
3. status
4. tag
5. date


IMPORTANT RULES:

- Read the entire DPR before extracting information.
- Extract information only when it is supported by the DPR.
- NEVER invent or guess missing information.
- If a field is genuinely missing, return null.
- Keep activity_description concise and meaningful.
- Convert the date to YYYY-MM-DD whenever possible.
- Preserve line numbers, equipment numbers, foundation numbers,
  structure numbers, or other identifiers when they are clearly
  used as the tag.
- Use simple status values such as:
  Completed
  In Progress
  Started
  Delayed
  Not Started

- If the DPR clearly says:
  finished, completed, work done, completed successfully
  then use "Completed".

- If the DPR clearly indicates that work is currently happening,
  use "In Progress".

- Do not confuse progress quantity with status.

- Do not invent information that is not present.


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

    return DPRData.model_validate_json(
        interaction.output_text
    )

def extract_dpr_from_file(file_path):

    file_path = Path(file_path)

    extension = file_path.suffix.lower()

    if extension == ".pdf":

        text = extract_text_from_pdf(file_path)

    elif extension in [".xlsx", ".xlsm"]:

        text = extract_text_from_excel(file_path)

    elif extension == ".txt":

        text = file_path.read_text(
            encoding="utf-8"
        )

    else:

        raise ValueError(
            f"Unsupported file type: {extension}"
        )

    if not text.strip():

        raise ValueError(
            "No readable text found in the file."
        )

    return extract_dpr(text)


if __name__ == "__main__":

    excel_path = r"data/Infrastructure_Schedule_01.xlsx"

    text = extract_text_from_excel(excel_path)

    print("\nEXTRACTED EXCEL TEXT:")
    print(text)