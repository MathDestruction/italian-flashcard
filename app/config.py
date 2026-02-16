from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    db_path: str = os.getenv("DB_PATH", "flashcards.db")
    timezone: str = os.getenv("TIMEZONE", "Africa/Johannesburg")  # Cape Town timezone
    schedule_hour: int = int(os.getenv("SCHEDULE_HOUR", "8"))
    schedule_minute: int = int(os.getenv("SCHEDULE_MINUTE", "0"))
    beginner_terms_file: str = os.getenv("BEGINNER_TERMS_FILE", "data/beginner_terms.json")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    image_model: str = os.getenv("IMAGE_MODEL", "gpt-image-1")
    image_size: str = os.getenv("IMAGE_SIZE", "1024x1024")

    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")


settings = Settings()
