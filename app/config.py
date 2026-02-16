from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # On Vercel, we must write to /tmp
    is_vercel: bool = os.getenv("VERCEL") == "1"
    
    db_path: str = os.getenv("DB_PATH", "/tmp/data/flashcards.db" if os.getenv("VERCEL") == "1" else "flashcards.db")
    timezone: str = os.getenv("TIMEZONE", "Africa/Johannesburg")
    schedule_hour: int = int(os.getenv("SCHEDULE_HOUR", "8"))
    schedule_minute: int = int(os.getenv("SCHEDULE_MINUTE", "0"))
    beginner_terms_file: str = os.getenv("BEGINNER_TERMS_FILE", "data/beginner_terms.json")

    # We take splitlines()[0] to handle accidental multi-line pastes in Vercel
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY").splitlines()[0].strip() if os.getenv("OPENAI_API_KEY") else None
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY").splitlines()[0].strip() if os.getenv("GOOGLE_API_KEY") else None
    image_model: str = os.getenv("IMAGE_MODEL", "gpt-image-2").splitlines()[0].strip()
    image_size: str = os.getenv("IMAGE_SIZE", "1024x1024").splitlines()[0].strip()

    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN").splitlines()[0].strip() if os.getenv("TELEGRAM_BOT_TOKEN") else None
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID").splitlines()[0].strip() if os.getenv("TELEGRAM_CHAT_ID") else None

    @property
    def images_dir(self) -> str:
        return "/tmp/generated_images" if self.is_vercel else "generated_images"


settings = Settings()
