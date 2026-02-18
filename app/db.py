from supabase import create_client, Client
from app.config import settings

def get_supabase() -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    # Debug print for length to help identify truncated/malformed keys
    print(f"Initializing Supabase client. URL length: {len(settings.supabase_url)}, Key length: {len(settings.supabase_key)}")
    
    return create_client(settings.supabase_url, settings.supabase_key)

def init_db() -> None:
    # No-op for Supabase, as tables should be created in the dashboard
    pass
