import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Find project root
ROOT_DIR = Path(__file__).resolve().parents[2]

# Load .env from project root
load_dotenv(ROOT_DIR / ".env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SECRET_KEY")

if not url or not key:
    raise ValueError(
        "SUPABASE_URL or SUPABASE_SECRET_KEY is missing from .env"
    )

supabase: Client = create_client(url, key)

response = supabase.table("schedule_activities").select("*").execute()

print(response.data)