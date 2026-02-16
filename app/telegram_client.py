from typing import Optional
from pathlib import Path

import requests

from app.config import settings


class TelegramDeliveryError(Exception):
    pass


def send_telegram_message(
    text: str, image_url: Optional[str] = None, image_path: Optional[str | Path] = None
) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise TelegramDeliveryError("Telegram is not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")

    base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    if image_path:
        # Uploading local file
        path = Path(image_path)
        if not path.exists():
            raise TelegramDeliveryError(f"Image file not found at: {image_path}")
        
        with open(path, "rb") as photo:
            response = requests.post(
                f"{base_url}/sendPhoto",
                data={
                    "chat_id": settings.telegram_chat_id,
                    "caption": text,
                },
                files={"photo": photo},
                timeout=30,
            )
    elif image_url:
        # Sending via remote URL
        response = requests.post(
            f"{base_url}/sendPhoto",
            json={
                "chat_id": settings.telegram_chat_id,
                "photo": image_url,
                "caption": text,
            },
            timeout=20,
        )
    else:
        # Plain text message
        response = requests.post(
            f"{base_url}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": text},
            timeout=20,
        )

    if response.status_code >= 400:
        raise TelegramDeliveryError(f"Telegram API error: {response.status_code} {response.text}")
    
    return response.json()
