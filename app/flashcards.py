import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.config import settings
from app.db import get_conn
from app.telegram_client import send_telegram_message


def seed_beginner_terms_if_empty() -> None:
    terms_path = Path(settings.beginner_terms_file)
    if not terms_path.exists():
        return

    with get_conn() as conn:
        existing_count = conn.execute("SELECT COUNT(*) AS count FROM source_terms").fetchone()["count"]
        if existing_count > 0:
            return

        terms = json.loads(terms_path.read_text(encoding="utf-8"))
        for term in terms:
            conn.execute(
                """
                INSERT OR IGNORE INTO source_terms (italian_text, category, difficulty)
                VALUES (?, ?, ?)
                """,
                (term["italian_text"], term.get("category", "general"), "beginner"),
            )


def get_next_beginner_term() -> str:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, italian_text
            FROM source_terms
            WHERE difficulty = 'beginner' AND used = 0
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()

        if row:
            conn.execute(
                "UPDATE source_terms SET used = 1, used_at = ? WHERE id = ?",
                (_utc_now_iso(), row["id"]),
            )
            return row["italian_text"]

        conn.execute("UPDATE source_terms SET used = 0, used_at = NULL WHERE difficulty = 'beginner'")
        recycled = conn.execute(
            """
            SELECT id, italian_text
            FROM source_terms
            WHERE difficulty = 'beginner'
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()

        if not recycled:
            raise ValueError("No beginner terms found. Populate data/beginner_terms.json.")

        conn.execute(
            "UPDATE source_terms SET used = 1, used_at = ? WHERE id = ?",
            (_utc_now_iso(), recycled["id"]),
        )
        return recycled["italian_text"]


def build_linguistic_content(term: str) -> dict[str, str]:
    if not settings.openai_api_key:
        return {
            "italian_text": term,
            "phonetic": "Pronunciation unavailable (set OPENAI_API_KEY).",
            "english_translation": "Translation unavailable (set OPENAI_API_KEY).",
        }

    prompt = (
        "You are helping beginners learn Italian. "
        "Return strict JSON with keys italian_text, phonetic, english_translation. "
        f"Use this Italian word/phrase: {term}."
    )
    # Create client with specific timeout and NO retries to avoid Vercel timeout loop
    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=8.0,
        max_retries=0
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    content = response.choices[0].message.content or "{}"
    parsed: dict[str, Any] = json.loads(content)

    return {
        "italian_text": parsed.get("italian_text", term),
        "phonetic": parsed.get("phonetic", "N/A"),
        "english_translation": parsed.get("english_translation", "N/A"),
    }


def generate_image_for_term(term: str) -> tuple[str | None, str | None, str]:
    prompt = (
        "Create a clean, friendly educational illustration suitable for a language flashcard. "
        f"Represent this Italian term visually: '{term}'. No text in image."
    )

    if not settings.openai_api_key:
        return None, None, prompt

    # This part takes 15-30 seconds
    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=30.0,
        max_retries=0
    )
    try:
        result = client.images.generate(
            model=settings.image_model,
            prompt=prompt,
            size=settings.image_size,
            response_format="b64_json"
        )
    except Exception as e:
        print(f"Error with model {settings.image_model}: {e}. Falling back to dall-e-3.")
        result = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=settings.image_size,
            response_format="b64_json"
        )

    img_b64 = result.data[0].b64_json if result.data else None
    if not img_b64:
        return None, None, prompt

    output_dir = Path(settings.images_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{_slugify(term)}.png"
    file_path = output_dir / filename
    file_path.write_bytes(base64.b64decode(img_b64))

    return None, str(file_path), prompt


def create_and_send_daily_flashcard(background_image: bool = True) -> dict[str, Any]:
    """Generates text first (fast), then optionally schedules image generation (slow)."""
    print("--- Phase 1: Text Generation (Fast) ---")
    term = get_next_beginner_term()
    content = build_linguistic_content(term)
    
    message = (
        "🇮🇹 Daily Italian Flashcard\n\n"
        f"🟩 Italian: {content['italian_text']}\n"
        f"🔊 Pronunciation: {content['phonetic']}\n"
        f"🇬🇧 English: {content['english_translation']}\n\n"
        "🎨 Generating illustration... please wait."
    )

    print("Sending text message to Telegram...")
    send_telegram_message(message)

    # Database part
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO flashcards (
                italian_text, phonetic, english_translation, difficulty, sent_channel, sent_at, created_at
            ) VALUES (?, ?, ?, 'beginner', 'telegram', ?, ?)
            """,
            (
                content["italian_text"],
                content["phonetic"],
                content["english_translation"],
                _utc_now_iso(),
                _utc_now_iso(),
            ),
        )
        flashcard_id = cursor.lastrowid

    print("Phase 1 Complete.")
    return {
        "status": "text_sent",
        "flashcard_id": flashcard_id,
        **content
    }


def background_image_task(term: str, flashcard_id: int):
    """Heavy lifting for image generation. Runs outside the main request timeout."""
    print(f"--- Phase 2: Image Generation Task for '{term}' ---")
    try:
        image_url, image_path, image_prompt = generate_image_for_term(term)
        
        if image_path:
            print("Sending image to Telegram...")
            send_telegram_message(
                f"🎨 Visual for: {term}",
                image_path=image_path
            )
            
            # Update DB with image path
            with get_conn() as conn:
                conn.execute(
                    "UPDATE flashcards SET image_url = ?, prompt_used = ? WHERE id = ?",
                    (image_path, image_prompt, flashcard_id)
                )
            print("Phase 2 Complete.")
        else:
            print("Image generation failed or returned no result.")
    except Exception as e:
        print(f"Background image task failed: {e}")


def list_flashcards(limit: int = 100) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, italian_text, phonetic, english_translation, image_url,
                   difficulty, sent_channel, sent_at, created_at
            FROM flashcards
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")[:40]
