import csv
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from groq import Groq
from openpyxl import load_workbook
from pydantic import BaseModel, Field
from pypdf import PdfReader


# ---------------------------------------------------------
# PROJECT / ENVIRONMENT SETUP
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Allows us to change model later from .env without editing code.
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY was not found in the project .env file"
    )

client = Groq(api_key=GROQ_API_KEY)


# ---------------------------------------------------------
# DATA MODELS
# ---------------------------------------------------------

DPRStatus = Literal[
    "Completed",
    "Started",
    "In Progress",
    "Delayed",
    "Not Started"
]


class DPRData(BaseModel):

    activity_description: str | None = None

    discipline: str | None = None

    status: DPRStatus | None = None

    tag: str | None = None

    date: str | None = None


class DPRExtractionResult(BaseModel):

    activities: list[DPRData] = Field(
        default_factory=list
    )


# ---------------------------------------------------------
# FILE TEXT EXTRACTION
# ---------------------------------------------------------

def extract_text_from_pdf(
    pdf_path: str | Path
) -> str:

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF file not found: {pdf_path}"
        )

    reader = PdfReader(pdf_path)

    text_parts = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):

        page_text = page.extract_text()

        if page_text:
            text_parts.append(
                f"\n--- Page {page_number} ---\n"
                f"{page_text}"
            )

    return "\n".join(text_parts)


def extract_text_from_excel(
    excel_path: str | Path
) -> str:

    excel_path = Path(excel_path)

    if not excel_path.exists():
        raise FileNotFoundError(
            f"Excel file not found: {excel_path}"
        )

    workbook = load_workbook(
        excel_path,
        data_only=True,
        read_only=True
    )

    text_parts = []

    for sheet in workbook.worksheets:

        text_parts.append(
            f"\n--- Sheet: {sheet.title} ---"
        )

        for row in sheet.iter_rows(
            values_only=True
        ):

            values = [
                str(cell).strip()
                for cell in row
                if cell is not None
                and str(cell).strip()
            ]

            if values:
                text_parts.append(
                    " | ".join(values)
                )

    return "\n".join(text_parts)


def extract_text_from_csv(
    csv_path: str | Path
) -> str:

    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {csv_path}"
        )

    text_parts = []

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.reader(file)

        for row in reader:

            values = [
                str(cell).strip()
                for cell in row
                if str(cell).strip()
            ]

            if values:
                text_parts.append(
                    " | ".join(values)
                )

    return "\n".join(text_parts)


# ---------------------------------------------------------
# AI DPR EXTRACTION
# ---------------------------------------------------------

def extract_dpr(
    dpr_text: str,
    reference_date: str | None = None
) -> DPRExtractionResult:

    if not dpr_text or not dpr_text.strip():
        raise ValueError(
            "DPR text cannot be empty"
        )

    reference_date_instruction = ""

    if reference_date:

        reference_date_instruction = f"""
REFERENCE DATE:

{reference_date}

If the DPR contains expressions such as
"today" or "yesterday", interpret them
relative to this reference date.
"""

    else:

        reference_date_instruction = """
No reference date has been supplied.

If the DPR only says "today", "yesterday",
or another relative date and the actual
calendar date cannot be determined,
return null for date.
"""

    prompt = f"""
You are an engineering Daily Progress Report
(DPR) extraction assistant for a large
infrastructure project.

The DPR may contain progress information from:

- Civil
- Piping
- Mechanical
- Electrical
- Instrumentation
- HSE
- Other engineering disciplines

The input may be:

- Plain text
- A paragraph
- Poorly formatted text
- Abbreviated site language
- PDF extracted text
- Excel extracted text
- CSV extracted text


IMPORTANT:

A DPR may contain MULTIPLE activities.

Create a SEPARATE activity object for every
distinct progress activity.

Do NOT combine separate activities into
one activity.


For every activity extract EXACTLY:

1. activity_description
2. discipline
3. status
4. tag
5. date


RULES:

- Read the complete DPR before extracting.
- Never invent information.
- If information is genuinely unavailable,
  use null.
- Keep activity_description short but meaningful.
- Preserve equipment numbers, foundation numbers,
  line numbers, structure IDs and similar identifiers.
- Use these identifiers as tag when appropriate.
- Discipline may be inferred only when strongly
  supported by engineering terminology.
- Otherwise discipline must be null.


STATUS RULES:

Use only:

Completed
Started
In Progress
Delayed
Not Started


Examples:

"finished"
"completed"
"work done"

→ Completed


"started"
"commenced"
"began"

→ Started


"work underway"
"ongoing"
"currently being executed"

→ In Progress


"delayed"
"held up"
"stopped due to..."

→ Delayed


Do not confuse percentage or quantity progress
with status.


DATE RULES:

- Convert explicit dates to YYYY-MM-DD.
- Do not invent dates.
- Follow the reference-date instruction below.

{reference_date_instruction}


TAG EXAMPLES:

Foundation F101
→ F101

Line L24
→ L24

Equipment P-104
→ P-104


RETURN FORMAT:

Return ONLY valid JSON in exactly this structure:

{{
    "activities": [
        {{
            "activity_description": "...",
            "discipline": "...",
            "status": "...",
            "tag": "...",
            "date": "YYYY-MM-DD"
        }}
    ]
}}


DPR TEXT:

{dpr_text}
"""

    try:

        response = client.chat.completions.create(

            model=GROQ_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract structured "
                        "engineering construction DPR data. "
                        "Return only valid JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            response_format={
                "type": "json_object"
            },

            temperature=0
        )

    except Exception as exc:

        raise RuntimeError(
            f"Groq DPR extraction failed: {exc}"
        ) from exc


    result = response.choices[0].message.content

    if not result:
        raise RuntimeError(
            "Groq returned an empty response"
        )


    try:

        return DPRExtractionResult.model_validate_json(
            result
        )

    except Exception as exc:

        raise RuntimeError(
            "AI response could not be validated "
            f"as DPR data. Raw response: {result}"
        ) from exc


# ---------------------------------------------------------
# FILE DPR EXTRACTION
# ---------------------------------------------------------

def extract_dpr_from_file(
    file_path: str | Path,
    reference_date: str | None = None
) -> DPRExtractionResult:

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    extension = file_path.suffix.lower()


    if extension == ".pdf":

        text = extract_text_from_pdf(
            file_path
        )


    elif extension in [
        ".xlsx",
        ".xlsm"
    ]:

        text = extract_text_from_excel(
            file_path
        )


    elif extension == ".csv":

        text = extract_text_from_csv(
            file_path
        )


    elif extension == ".txt":

        text = file_path.read_text(
            encoding="utf-8",
            errors="replace"
        )


    else:

        raise ValueError(
            "Unsupported file type: "
            f"{extension}. "
            "Supported formats are PDF, "
            "XLSX, XLSM, CSV and TXT."
        )


    if not text.strip():

        raise ValueError(
            "No readable text was found "
            "inside the file."
        )


    return extract_dpr(
        text,
        reference_date=reference_date
    )


# ---------------------------------------------------------
# LOCAL TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    sample_dpr = """
    F101 concreting completed today.
    Reinforcement for F102 started today.
    Cable tray installation in Area A is in progress.
    """

    result = extract_dpr(
        sample_dpr
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )