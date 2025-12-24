import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "bygone-images")

def client():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def upload_file_bytes(*, storage_key: str, content: bytes, content_type: str | None):
    sb = client()
    # upsert=False so you don't overwrite existing files
    sb.storage.from_(SUPABASE_BUCKET).upload(
        path=storage_key,
        file=content,
        file_options={"content-type": content_type} if content_type else None,
    )

def public_url(storage_key: str) -> str:
    # Public bucket URL pattern:
    # https://<project>.supabase.co/storage/v1/object/public/<bucket>/<path>
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{storage_key}"

def delete_file(storage_key: str):
    sb = client()
    sb.storage.from_(SUPABASE_BUCKET).remove([storage_key])

    