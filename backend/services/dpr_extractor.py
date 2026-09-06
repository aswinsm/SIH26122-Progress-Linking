import csv
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from groq import Groq
from openpyxl import load_workbook
from pydantic import BaseModel, Field
from pypdf import PdfReader


# ============================================================
# PROJECT / ENVIRONMENT SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)


if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY was not found in the project .env file"
    )


client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# DATA MODELS
# ============================================================

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

    progress_percent: float | None = None


class DPRExtractionResult(BaseModel):

    activities: list[DPRData] = Field(
        default_factory=list
    )


# ============================================================
# GROQ STRUCTURED OUTPUT SCHEMA
# ============================================================

DPR_RESPONSE_SCHEMA = {

    "type": "object",

    "properties": {

        "activities": {

            "type": "array",

            "items": {

                "type": "object",

                "properties": {

                    "activity_description": {
                        "type": [
                            "string",
                            "null"
                        ]
                    },

                    "discipline": {
                        "type": [
                            "string",
                            "null"
                        ]
                    },

                    "status": {

                        "anyOf": [

                            {
                                "type": "string",

                                "enum": [
                                    "Completed",
                                    "Started",
                                    "In Progress",
                                    "Delayed",
                                    "Not Started"
                                ]
                            },

                            {
                                "type": "null"
                            }
                        ]
                    },

                    "tag": {
                        "type": [
                            "string",
                            "null"
                        ]
                    },

                    "date": {
                        "type": [
                            "string",
                            "null"
                        ]
                    },

                    "progress_percent": {
                        "type": [
                            "number",
                            "null"
                        ]
                    }
                },

                "required": [
                    "activity_description",
                    "discipline",
                    "status",
                    "tag",
                    "date",
                    "progress_percent"
                ],

                "additionalProperties": False
            }
        }
    },

    "required": [
        "activities"
    ],

    "additionalProperties": False
}


# ============================================================
# SMALL HELPERS
# ============================================================

def clean_cell_value(
    value
) -> str | None:

    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    return text


def normalize_header(
    value
) -> str:

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace("/", "_")
        .replace(" ", "_")
    )


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_text_from_pdf(
    pdf_path: str | Path
) -> str:

    pdf_path = Path(
        pdf_path
    )


    if not pdf_path.exists():

        raise FileNotFoundError(
            f"PDF file not found: {pdf_path}"
        )


    reader = PdfReader(
        pdf_path
    )


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


    return "\n".join(
        text_parts
    )


# ============================================================
# EXCEL TEXT EXTRACTION
# ============================================================

def extract_text_from_excel(
    excel_path: str | Path
) -> str:

    excel_path = Path(
        excel_path
    )


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


    try:

        for sheet in workbook.worksheets:

            text_parts.append(
                f"\n--- Sheet: {sheet.title} ---"
            )


            for row in sheet.iter_rows(
                values_only=True
            ):

                values = []


                for cell in row:

                    value = clean_cell_value(
                        cell
                    )


                    if value is not None:

                        values.append(
                            value
                        )


                if values:

                    text_parts.append(
                        " | ".join(
                            values
                        )
                    )


    finally:

        workbook.close()


    return "\n".join(
        text_parts
    )


# ============================================================
# CSV TEXT EXTRACTION
# ============================================================

def extract_text_from_csv(
    csv_path: str | Path
) -> str:

    csv_path = Path(
        csv_path
    )


    if not csv_path.exists():

        raise FileNotFoundError(
            f"CSV file not found: {csv_path}"
        )


    text_parts = []


    with csv_path.open(

        "r",

        encoding="utf-8-sig",

        errors="replace",

        newline=""

    ) as file:

        reader = csv.reader(
            file
        )


        for row in reader:

            values = []


            for cell in row:

                value = clean_cell_value(
                    cell
                )


                if value is not None:

                    values.append(
                        value
                    )


            if values:

                text_parts.append(
                    " | ".join(
                        values
                    )
                )


    return "\n".join(
        text_parts
    )


# ============================================================
# DETECT PLANNED SCHEDULE EXCEL
# ============================================================

def is_schedule_excel(
    excel_path: str | Path
) -> bool:

    """
    Detect whether an uploaded workbook looks like
    the PLANNED MASTER SCHEDULE rather than a DPR.

    Example planned schedule columns:

    activity_id
    activity_name
    project_id
    planned_start
    planned_end / planned_finish

    A planned schedule should NOT be sent into the
    DPR extraction pipeline.
    """

    excel_path = Path(
        excel_path
    )


    workbook = load_workbook(

        excel_path,

        data_only=True,

        read_only=True
    )


    try:

        for sheet in workbook.worksheets:

            checked_rows = 0


            for row in sheet.iter_rows(
                values_only=True
            ):

                values = [
                    value

                    for value in row

                    if value is not None
                ]


                if not values:

                    continue


                headers = {

                    normalize_header(
                        value
                    )

                    for value in values
                }


                checked_rows += 1


                has_activity_id = (
                    "activity_id"
                    in headers
                )


                has_activity_name = (
                    "activity_name"
                    in headers
                )


                has_planned_start = (
                    "planned_start"
                    in headers
                )


                has_planned_finish = (
                    "planned_finish"
                    in headers
                    or
                    "planned_end"
                    in headers
                )


                # Very strong indication of a
                # planned schedule workbook.
                if (
                    has_activity_id
                    and has_activity_name
                    and has_planned_start
                    and has_planned_finish
                ):

                    return True


                # Only inspect the first few
                # meaningful rows of each sheet.
                if checked_rows >= 5:

                    break


    finally:

        workbook.close()


    return False


# ============================================================
# AI DPR EXTRACTION
# ============================================================

def extract_dpr(
    dpr_text: str,
    reference_date: str | None = None
) -> DPRExtractionResult:


    if (
        not dpr_text
        or not dpr_text.strip()
    ):

        raise ValueError(
            "DPR text cannot be empty"
        )


    # --------------------------------------------------------
    # DATE INSTRUCTION
    # --------------------------------------------------------

    if reference_date:

        reference_date_instruction = f"""
Reference date: {reference_date}

If expressions such as "today" or "yesterday"
appear, interpret them relative to this date.
"""


    else:

        reference_date_instruction = """
No reference date is available.

If only a relative date such as "today" or
"yesterday" appears and the actual date cannot
be determined, return null.
"""


    # --------------------------------------------------------
    # PROMPT
    # --------------------------------------------------------

    prompt = f"""
You are an engineering Daily Progress Report
(DPR) extraction system for infrastructure
construction projects.

Your input contains ACTUAL SITE PROGRESS.

Extract construction progress activities from
the supplied DPR content.


The report may contain:

- Civil
- Piping
- Mechanical
- Electrical
- Instrumentation
- HSE
- Other engineering construction disciplines


The input may come from:

- Typed site updates
- Daily Progress Report Excel sheets
- CSV
- PDF
- Site diaries
- Voice transcription
- Scanned notes


============================================================
IMPORTANT
============================================================

1. A DPR may contain MULTIPLE activities.

2. Create ONE separate activity object for
   every distinct construction activity.

3. Never invent information.

4. Ignore headings and administrative text.

5. Ignore spreadsheet column headings.

6. Do NOT treat planned schedule dates alone as
   actual progress.

7. An activity must represent something that
   happened, started, progressed, completed,
   became delayed, or is explicitly not started.

8. If an Excel row contains an activity name but
   provides no actual progress information,
   do not invent progress.


For every actual-progress activity identify:

- activity_description
- discipline
- status
- tag
- date
- progress_percent


============================================================
ACTIVITY DESCRIPTION
============================================================

Keep the activity description concise but preserve
important engineering context.

Examples:

"F101 foundation concreting"

"Reinforcement for F102"

"Cable tray installation Area A"

"Pipeline welding Line L24"


============================================================
DISCIPLINE
============================================================

Infer engineering discipline from terminology
when reasonably clear.

Examples:


Excavation
Foundation
Concrete
Reinforcement
Formwork
Road work
Drainage

→ Civil


Pipeline
Pipe welding
Spool erection
Hydrotest

→ Piping


Cable tray
Electrical cable
Lighting
Transformer
Switchgear
Earthing

→ Electrical


Pump
Compressor
Equipment erection
Mechanical alignment

→ Mechanical


Instrument calibration
Transmitter
Loop checking
Control instrument

→ Instrumentation


Safety inspection
Toolbox talk
HSE audit

→ HSE


If discipline genuinely cannot be inferred,
return null.


============================================================
STATUS
============================================================

Use ONLY:

Completed
Started
In Progress
Delayed
Not Started


Examples:


finished
completed
work done
100% completed

→ Completed


started
commenced
began

→ Started


ongoing
underway
currently being executed
40% complete
70% complete

→ In Progress


delayed
held up
stopped due to

→ Delayed


not started
yet to start

→ Not Started


============================================================
PROGRESS PERCENT
============================================================

Extract ACTUAL PHYSICAL PROGRESS.

The number must be between:

0 and 100


Examples:


"Foundation work is 65% complete"

→ progress_percent = 65


"Road resurfacing reached 42%"

→ progress_percent = 42


"Pipeline installation progress is 78.5%"

→ progress_percent = 78.5


"75 metres completed out of 100 metres"

→ progress_percent = 75


"40 columns completed out of 50"

→ progress_percent = 80


"25 units installed out of total 100"

→ progress_percent = 25


If completed quantity AND total quantity
are explicitly provided:

progress_percent =
(completed quantity / total quantity) * 100


If explicitly Completed:

progress_percent = 100


If explicitly Not Started:

progress_percent = 0


IMPORTANT:

If the report only says:

Started

or:

In Progress

or:

Ongoing

WITHOUT quantitative progress information,

return:

progress_percent = null


NEVER assume:

Started = 10

In Progress = 50

Delayed = any percentage


============================================================
TAG
============================================================

Preserve engineering identifiers such as:

F101
F102
L24
P-104
ST-03
Area-A
Zone-B

Do not invent a tag.


============================================================
DATE
============================================================

Convert explicit dates to:

YYYY-MM-DD


Never invent dates.


{reference_date_instruction}


============================================================
FINAL VALIDATION
============================================================

For each extracted activity:

- It must describe actual site progress.
- Keep activities separate.
- Do not duplicate the same activity.
- Do not invent percentages.
- Completed = 100.
- Not Started = 0.
- Started / In Progress without quantitative
  evidence = null progress_percent.


DPR CONTENT:

---------------- START ----------------

{dpr_text}

---------------- END ----------------
"""


    # --------------------------------------------------------
    # GROQ REQUEST
    # --------------------------------------------------------

    try:

        response = (
            client.chat.completions.create(

                model=GROQ_MODEL,

                messages=[

                    {
                        "role": "system",

                        "content": (
                            "Extract structured engineering "
                            "actual-progress DPR activities. "
                            "Return only schema-compliant data. "
                            "Never invent physical progress."
                        )
                    },

                    {
                        "role": "user",

                        "content": prompt
                    }
                ],


                response_format={

                    "type":
                        "json_schema",

                    "json_schema": {

                        "name":
                            "dpr_extraction",

                        "strict":
                            True,

                        "schema":
                            DPR_RESPONSE_SCHEMA
                    }
                },


                temperature=0
            )
        )


    except Exception as exc:

        raise RuntimeError(

            "Groq DPR extraction failed: "
            f"{exc}"

        ) from exc


    # --------------------------------------------------------
    # READ RESPONSE
    # --------------------------------------------------------

    result = (
        response
        .choices[0]
        .message
        .content
    )


    if not result:

        raise RuntimeError(
            "Groq returned an empty response"
        )


    # --------------------------------------------------------
    # VALIDATE RESPONSE
    # --------------------------------------------------------

    try:

        extraction = (
            DPRExtractionResult
            .model_validate_json(
                result
            )
        )


    except Exception as exc:

        raise RuntimeError(

            "Groq response could not be "
            "validated as DPR data. "
            f"Raw response: {result}"

        ) from exc


    # --------------------------------------------------------
    # NORMALIZE PROGRESS / STATUS
    # --------------------------------------------------------

    for activity in extraction.activities:

        if (
            activity.progress_percent
            is not None
        ):

            activity.progress_percent = max(

                0.0,

                min(
                    100.0,
                    float(
                        activity.progress_percent
                    )
                )
            )


        # 100% must always be Completed
        if (
            activity.progress_percent
            is not None
            and activity.progress_percent >= 100
        ):

            activity.status = (
                "Completed"
            )


        # 0% with explicit Not Started
        if (
            activity.status
            == "Not Started"
        ):

            activity.progress_percent = (
                0.0
            )


    return extraction


# ============================================================
# SAFE CHUNK EXTRACTION
# ============================================================

def extract_chunk_safely(
    lines: list[str],
    sheet_name: str,
    reference_date: str | None = None,
    header_line: str | None = None
) -> list[DPRData]:


    if not lines:

        return []


    text_parts = [
        f"Excel Sheet: {sheet_name}"
    ]


    if header_line:

        text_parts.append(
            f"Columns: {header_line}"
        )


    text_parts.extend(
        lines
    )


    chunk_text = "\n".join(
        text_parts
    )


    try:

        result = extract_dpr(

            chunk_text,

            reference_date=reference_date
        )


        return result.activities


    except Exception as error:

        # ----------------------------------------------------
        # SINGLE BAD ROW
        #
        # Skip only this row instead of failing
        # the entire Excel DPR.
        # ----------------------------------------------------

        if len(lines) == 1:

            print(
                "\n========== DPR ROW SKIPPED =========="
            )

            print(
                f"Sheet: {sheet_name}"
            )

            print(
                f"Row: {lines[0]}"
            )

            print(
                f"Reason: {error}"
            )

            print(
                "=====================================\n"
            )


            return []


        # ----------------------------------------------------
        # SPLIT FAILED CHUNK INTO SMALLER PARTS
        # ----------------------------------------------------

        middle = (
            len(lines) // 2
        )


        first_half = (
            lines[:middle]
        )


        second_half = (
            lines[middle:]
        )


        activities = []


        activities.extend(

            extract_chunk_safely(

                lines=first_half,

                sheet_name=sheet_name,

                reference_date=reference_date,

                header_line=header_line
            )
        )


        activities.extend(

            extract_chunk_safely(

                lines=second_half,

                sheet_name=sheet_name,

                reference_date=reference_date,

                header_line=header_line
            )
        )


        return activities


# ============================================================
# EXCEL DPR CHUNK PROCESSING
# ============================================================

def extract_dpr_from_excel_chunks(
    excel_path: str | Path,
    reference_date: str | None = None,
    chunk_size: int = 15
) -> DPRExtractionResult:


    excel_path = Path(
        excel_path
    )


    if not excel_path.exists():

        raise FileNotFoundError(
            f"Excel file not found: {excel_path}"
        )


    # --------------------------------------------------------
    # REJECT MASTER SCHEDULE FILE
    # --------------------------------------------------------

    if is_schedule_excel(
        excel_path
    ):

        raise ValueError(
            "This Excel workbook appears to be a "
            "planned project schedule rather than "
            "a Daily Progress Report. "
            "Please upload a DPR containing actual "
            "site progress, status or completed quantities."
        )


    workbook = load_workbook(

        excel_path,

        data_only=True,

        read_only=True
    )


    all_activities: list[DPRData] = []


    try:

        for sheet in workbook.worksheets:

            rows: list[str] = []


            for excel_row_number, row in enumerate(

                sheet.iter_rows(
                    values_only=True
                ),

                start=1
            ):

                values = []


                for cell in row:

                    value = clean_cell_value(
                        cell
                    )


                    if value is not None:

                        values.append(
                            value
                        )


                if values:

                    row_text = (
                        f"Row {excel_row_number}: "
                        + " | ".join(
                            values
                        )
                    )


                    rows.append(
                        row_text
                    )


            if not rows:

                continue


            # ------------------------------------------------
            # KEEP FIRST MEANINGFUL ROW AS HEADER CONTEXT
            # ------------------------------------------------

            header_line = rows[0]


            # Actual data rows after header.
            # If workbook is unstructured, keeping the first
            # row only as header context is still harmless.
            data_rows = rows[1:]


            if not data_rows:

                data_rows = rows

                header_line = None


            print(
                f"\nProcessing Excel sheet: "
                f"{sheet.title}"
            )

            print(
                f"Rows found: "
                f"{len(data_rows)}"
            )


            # ------------------------------------------------
            # PROCESS IN CHUNKS
            # ------------------------------------------------

            total_chunks = (

                len(data_rows)
                + chunk_size
                - 1

            ) // chunk_size


            for chunk_number, start in enumerate(

                range(
                    0,
                    len(data_rows),
                    chunk_size
                ),

                start=1
            ):

                chunk = data_rows[
                    start:
                    start + chunk_size
                ]


                print(
                    f"Processing chunk "
                    f"{chunk_number}/{total_chunks}"
                )


                activities = (
                    extract_chunk_safely(

                        lines=chunk,

                        sheet_name=sheet.title,

                        reference_date=reference_date,

                        header_line=header_line
                    )
                )


                all_activities.extend(
                    activities
                )


    finally:

        workbook.close()


    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    unique_activities: list[DPRData] = []

    seen = set()


    for activity in all_activities:

        key = (

            (
                activity.activity_description
                or ""
            )
            .lower()
            .strip(),

            (
                activity.discipline
                or ""
            )
            .lower()
            .strip(),

            (
                activity.status
                or ""
            )
            .lower()
            .strip(),

            (
                activity.tag
                or ""
            )
            .lower()
            .strip(),

            (
                activity.date
                or ""
            )
            .lower()
            .strip(),

            activity.progress_percent
        )


        if key in seen:

            continue


        seen.add(
            key
        )


        unique_activities.append(
            activity
        )


    if not unique_activities:

        raise ValueError(
            "The Excel file was read successfully, "
            "but no actual construction progress "
            "activities were found. "
            "Please upload a DPR containing status, "
            "progress percentage, completed quantities "
            "or actual site updates."
        )


    print(
        f"\nExcel DPR extraction complete. "
        f"Activities extracted: "
        f"{len(unique_activities)}\n"
    )


    return DPRExtractionResult(
        activities=unique_activities
    )


# ============================================================
# FILE DPR EXTRACTION
# ============================================================

def extract_dpr_from_file(
    file_path: str | Path,
    reference_date: str | None = None
) -> DPRExtractionResult:


    file_path = Path(
        file_path
    )


    if not file_path.exists():

        raise FileNotFoundError(
            f"File not found: {file_path}"
        )


    extension = (
        file_path
        .suffix
        .lower()
    )


    # ========================================================
    # EXCEL
    # ========================================================

    if extension in {
        ".xlsx",
        ".xlsm"
    }:

        return extract_dpr_from_excel_chunks(

            file_path,

            reference_date=reference_date
        )


    # ========================================================
    # PDF
    # ========================================================

    if extension == ".pdf":

        text = extract_text_from_pdf(
            file_path
        )


    # ========================================================
    # CSV
    # ========================================================

    elif extension == ".csv":

        text = extract_text_from_csv(
            file_path
        )


    # ========================================================
    # TXT
    # ========================================================

    elif extension == ".txt":

        text = (
            file_path
            .read_text(

                encoding="utf-8",

                errors="replace"
            )
        )


    # ========================================================
    # UNSUPPORTED
    # ========================================================

    else:

        raise ValueError(

            "Unsupported file type: "
            f"{extension}. "

            "Supported formats are "
            "PDF, XLSX, XLSM, CSV and TXT."
        )


    if not text.strip():

        raise ValueError(

            "No readable text was found "
            "inside the uploaded file."
        )


    result = extract_dpr(

        text,

        reference_date=reference_date
    )


    if not result.activities:

        raise ValueError(
            "The file was read successfully, "
            "but no actual construction progress "
            "activities were detected."
        )


    return result


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    sample_dpr = """
    Waterproofing membrane work in Zone B is 67% complete.
    Concrete rehabilitation in Zone B has reached 42%.
    Road signboard installation at East Section is completed.
    Cable tray installation in Area A is currently in progress.
    """


    result = extract_dpr(
        sample_dpr
    )


    print(
        "\n========== DPR EXTRACTION RESULT ==========\n"
    )


    print(
        result.model_dump_json(
            indent=2
        )
    )