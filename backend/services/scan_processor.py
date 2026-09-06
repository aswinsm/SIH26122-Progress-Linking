import base64
import os
from pathlib import Path

import fitz
from dotenv import load_dotenv
from groq import Groq


# ============================================================
# ENVIRONMENT SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

GROQ_VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL",
    "qwen/qwen3.6-27b"
)


if not GROQ_API_KEY:

    raise ValueError(
        "GROQ_API_KEY was not found in .env"
    )


client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# SUPPORTED FILES
# ============================================================

SUPPORTED_SCAN_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".pdf",
}


IMAGE_MIME_TYPES = {

    ".jpg":
        "image/jpeg",

    ".jpeg":
        "image/jpeg",

    ".png":
        "image/png",

    ".webp":
        "image/webp",
}


# ============================================================
# OCR USING GROQ VISION
# ============================================================

def extract_text_from_image_bytes(
    image_bytes: bytes,
    mime_type: str
) -> str:

    if not image_bytes:

        raise ValueError(
            "Image is empty"
        )


    base64_image = (
        base64.b64encode(
            image_bytes
        )
        .decode("utf-8")
    )


    try:

        response = (
            client.chat.completions.create(

                model=GROQ_VISION_MODEL,

                messages=[
                    {
                        "role": "user",

                        "content": [

                            {
                                "type": "text",

                                "text": (
                                    "This image is a construction "
                                    "site Daily Progress Report, "
                                    "site diary, handwritten note, "
                                    "scanned supervisor note, or "
                                    "engineering progress record. "

                                    "Read and transcribe all useful "
                                    "construction progress text from "
                                    "the image. "

                                    "Preserve activity names, "
                                    "foundation numbers, equipment "
                                    "numbers, line numbers, dates, "
                                    "discipline names, status words, "
                                    "percentages and location tags. "

                                    "Do not invent missing text. "

                                    "Return only the readable "
                                    "transcribed text."
                                )
                            },

                            {
                                "type": "image_url",

                                "image_url": {

                                    "url": (
                                        f"data:{mime_type};"
                                        f"base64,{base64_image}"
                                    )
                                }
                            }
                        ]
                    }
                ],

                temperature=0,

                max_completion_tokens=3000
            )
        )


    except Exception as exc:

        raise RuntimeError(
            "Groq scan OCR failed: "
            f"{exc}"
        ) from exc


    text = (
        response
        .choices[0]
        .message
        .content
    )


    if (
        not text
        or not text.strip()
    ):

        raise RuntimeError(
            "No readable text was detected "
            "in the scanned image."
        )


    return text.strip()


# ============================================================
# NORMAL IMAGE FILE
# ============================================================

def extract_text_from_image(
    image_path: str | Path
) -> str:

    image_path = Path(
        image_path
    )


    if not image_path.exists():

        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )


    extension = (
        image_path
        .suffix
        .lower()
    )


    if extension not in IMAGE_MIME_TYPES:

        raise ValueError(
            f"Unsupported image format: {extension}"
        )


    image_bytes = (
        image_path.read_bytes()
    )


    mime_type = (
        IMAGE_MIME_TYPES[
            extension
        ]
    )


    return extract_text_from_image_bytes(
        image_bytes,
        mime_type
    )


# ============================================================
# SCANNED PDF OCR
# ============================================================

def extract_text_from_scanned_pdf(
    pdf_path: str | Path,
    max_pages: int = 5
) -> str:

    pdf_path = Path(
        pdf_path
    )


    if not pdf_path.exists():

        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )


    document = fitz.open(
        pdf_path
    )


    extracted_pages = []


    try:

        pages_to_process = min(
            len(document),
            max_pages
        )


        for page_number in range(
            pages_to_process
        ):

            page = document[
                page_number
            ]


            # Render PDF page clearly enough
            # for handwritten/scanned OCR
            matrix = fitz.Matrix(
                2,
                2
            )


            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False
            )


            image_bytes = (
                pixmap.tobytes(
                    "png"
                )
            )


            page_text = (
                extract_text_from_image_bytes(
                    image_bytes,
                    "image/png"
                )
            )


            if page_text:

                extracted_pages.append(

                    f"--- Page {page_number + 1} ---\n"
                    f"{page_text}"
                )


    finally:

        document.close()


    if not extracted_pages:

        raise RuntimeError(
            "No readable text was found "
            "in the scanned PDF."
        )


    return "\n\n".join(
        extracted_pages
    )


# ============================================================
# GENERAL SCAN PROCESSOR
# ============================================================

def extract_text_from_scan(
    file_path: str | Path
) -> str:

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


    if extension in IMAGE_MIME_TYPES:

        return extract_text_from_image(
            file_path
        )


    elif extension == ".pdf":

        return extract_text_from_scanned_pdf(
            file_path
        )


    else:

        raise ValueError(
            "Unsupported scan format. "
            "Supported formats: "
            "JPG, JPEG, PNG, WEBP and PDF."
        )


# ============================================================
# LOCAL TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Scan processor loaded successfully."
    )

    print(
        f"Vision model: {GROQ_VISION_MODEL}"
    )