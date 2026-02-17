"""Diagnostic endpoints to test each component individually."""
import traceback
from openai import OpenAI
from app.config import settings
from app.db import get_conn, init_db
from app.telegram_client import send_telegram_message


def test_database() -> dict:
    """Test database connection and initialization."""
    try:
        init_db()
        with get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) as count FROM source_terms").fetchone()["count"]
        return {"status": "✅ SUCCESS", "terms_count": count}
    except Exception as e:
        return {"status": "❌ FAILED", "error": str(e), "traceback": traceback.format_exc()}


def test_openai_text() -> dict:
    """Test OpenAI text generation."""
    try:
        if not settings.openai_api_key:
            return {"status": "⚠️ SKIPPED", "reason": "No API key configured"}
        
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'test successful' in Italian"}],
            max_tokens=20
        )
        result = response.choices[0].message.content
        return {"status": "✅ SUCCESS", "response": result}
    except Exception as e:
        return {"status": "❌ FAILED", "error": str(e), "traceback": traceback.format_exc()}


def test_telegram() -> dict:
    """Test Telegram message sending."""
    try:
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return {"status": "⚠️ SKIPPED", "reason": "Telegram not configured"}
        
        send_telegram_message("🧪 Test message from Italian Flashcard Service")
        return {"status": "✅ SUCCESS", "message": "Check your Telegram!"}
    except Exception as e:
        return {"status": "❌ FAILED", "error": str(e), "traceback": traceback.format_exc()}


def test_image_generation() -> dict:
    """Test OpenAI image generation with configured model."""
    try:
        if not settings.openai_api_key:
            return {"status": "⚠️ SKIPPED", "reason": "No API key configured"}
        
        client = OpenAI(api_key=settings.openai_api_key, timeout=30.0)
        print(f"Testing image model: {settings.image_model}")
        
        # Small test prompt
        response = client.images.generate(
            model=settings.image_model,
            prompt="A small red apple on a white background, minimalist flat 2D style.",
            size=settings.image_size,
            n=1
        )
        return {
            "status": "✅ SUCCESS",
            "model_used": settings.image_model,
            "image_url": response.data[0].url if response.data else "No URL"
        }
    except Exception as e:
        return {
            "status": "❌ FAILED",
            "model_tried": settings.image_model,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


def run_all_diagnostics() -> dict:
    """Run all diagnostic tests."""
    return {
        "environment": {
            "is_vercel": settings.is_vercel,
            "db_path": settings.db_path,
            "has_openai_key": bool(settings.openai_api_key),
            "image_model": settings.image_model,
            "has_telegram_token": bool(settings.telegram_bot_token),
            "has_telegram_chat_id": bool(settings.telegram_chat_id),
        },
        "tests": {
            "1_database": test_database(),
            "2_openai_text": test_openai_text(),
            "3_telegram": test_telegram(),
            "4_image_gen": test_image_generation(),
        }
    }
