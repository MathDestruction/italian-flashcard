from typing import Optional

import requests

from app.config import settings


class TelegramDeliveryError(Exception):
    pass


def send_telegram_message(text: str, image_url: Optional[str] = None) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise TelegramDeliveryError("Telegram is not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")

    base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    if image_url:
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
        response = requests.post(
            f"{base_url}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": text},
            timeout=20,
        )

    if response.status_code >= 400:
        raise TelegramDeliveryError(f"Telegram API error: {response.status_code} {response.text}")
