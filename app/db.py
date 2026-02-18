from supabase import create_client, Client
from app.config import settings

def get_supabase() -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    return create_client(settings.supabase_url, settings.supabase_key)

def init_db() -> None:
    # No-op for Supabase, as tables should be created in the dashboard
    pass
