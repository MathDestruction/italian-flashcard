import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.config import settings
from app.db import get_supabase
from app.telegram_client import send_telegram_message


def seed_beginner_terms_if_empty() -> None:
    terms_path = Path(settings.beginner_terms_file)
    if not terms_path.exists():
        return

    if not settings.supabase_url or not settings.supabase_key:
        print("⚠️ Supabase credentials not found. Skipping seeding.")
        return

    try:
        supabase = get_supabase()
        # Check if any source_terms exist
        response = supabase.table("source_terms").select("id", count="exact").limit(1).execute()
        if response.count is not None and response.count > 0:
            return
    except Exception as e:
        print(f"⚠️ Supabase check failed (maybe table doesn't exist yet?): {e}")
        # If it's a real connection error, we stop here
        if "apikey" in str(e).lower() or "url" in str(e).lower():
             return

    terms = json.loads(terms_path.read_text(encoding="utf-8"))
    data_to_insert = [
        {
            "italian_text": term["italian_text"],
            "category": term.get("category", "general"),
            "difficulty": "beginner",
            "used": False
        }
        for term in terms
    ]
    if data_to_insert:
        try:
            supabase.table("source_terms").insert(data_to_insert).execute()
            print(f"Seeded {len(data_to_insert)} terms to Supabase.")
        except Exception as e:
            print(f"Error seeding terms: {e}")


def get_next_beginner_term() -> str:
    supabase = get_supabase()
    
    # Find one unused term
    response = supabase.table("source_terms") \
        .select("id, italian_text") \
        .eq("difficulty", "beginner") \
        .eq("used", False) \
        .order("id") \
        .limit(1) \
        .execute()
    
    row = response.data[0] if response.data else None

    if row:
        supabase.table("source_terms") \
            .update({"used": True, "used_at": _utc_now_iso()}) \
            .eq("id", row["id"]) \
            .execute()
        return row["italian_text"]

    # Recycle if none left
    print("No unused beginner terms left. Recycling...")
    supabase.table("source_terms") \
        .update({"used": False, "used_at": None}) \
        .eq("difficulty", "beginner") \
        .execute()
        
    response = supabase.table("source_terms") \
        .select("id, italian_text") \
        .eq("difficulty", "beginner") \
        .order("id") \
        .limit(1) \
        .execute()
    
    recycled = response.data[0] if response.data else None

    if not recycled:
        raise ValueError("No beginner terms found in source_terms table.")

    supabase.table("source_terms") \
        .update({"used": True, "used_at": _utc_now_iso()}) \
        .eq("id", recycled["id"]) \
        .execute()
    return recycled["italian_text"]


def build_linguistic_content(term: str) -> dict[str, str]:
    if not settings.openai_api_key:
        return {
            "italian_text": term,
            "phonetic": "Pronunciation unavailable.",
            "english_translation": "Translation unavailable.",
            "example_sentence": "Example sentence unavailable."
        }

    prompt = (
        "You are helping beginners learn Italian. "
        "Return strict JSON with keys: italian_text, phonetic, english_translation, example_sentence. "
        "The example_sentence should be a simple beginner-friendly sentence using the term. "
        f"Use this Italian word/phrase: {term}."
    )
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
        "example_sentence": parsed.get("example_sentence", "N/A"),
    }


def generate_image_for_term(term: str, phonetic: str = "", translation: str = "") -> tuple[str | None, str | None, str, str]:
    """Generate image using guided prompt from imagePrompt.txt combined with term details."""
    prompt_path = Path(settings.image_prompt_file)
    if prompt_path.exists():
        base_prompt = prompt_path.read_text(encoding="utf-8").strip()
    else:
        base_prompt = (
            "Create a clean, friendly educational illustration suitable for a language flashcard. "
            "No text in image."
        )
    
    prompt = (
        f"### DESIGN SYSTEM & LAYOUT INSTRUCTIONS:\n{base_prompt}\n\n"
        f"### TEXT CONTENT TO RENDER IN THE GRAPHIC (CRITICAL):\n"
        f"- Italian Phrase: {term}\n"
        f"- English Translation: {translation}\n"
        f"- Pronunciation: {phonetic}\n\n"
        f"### FINAL CHECK:\n"
        f"- The background must be SOLID WHITE.\n"
        f"- Ensure the illustration is simple, flat, 2D, and represents '{term}'.\n"
        f"- Render all text elements clearly as specified in the layout instructions."
    )

    if not settings.openai_api_key:
        return None, None, prompt, "none"

    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=120.0,
        max_retries=0
    )
    
    model_used = settings.image_model
    try:
        print(f"Attempting image generation with model: {model_used}")
        result = client.images.generate(
            model=model_used,
            prompt=prompt,
            size=settings.image_size
        )
    except Exception as e:
        error_msg = f"Error with model {model_used}: {e}. Falling back to dall-e-3."
        print(error_msg)
        try:
            send_telegram_message(f"⚠️ Image generation fallback:\n`{error_msg}`")
        except:
            pass
            
        model_used = "dall-e-3"
        result = client.images.generate(
            model=model_used,
            prompt=prompt,
            size=settings.image_size,
            response_format="b64_json"
        )

    img_data = None
    if result.data:
        if hasattr(result.data[0], 'b64_json') and result.data[0].b64_json:
            img_data = base64.b64decode(result.data[0].b64_json)
        elif hasattr(result.data[0], 'url') and result.data[0].url:
            import requests
            img_response = requests.get(result.data[0].url, timeout=30)
            if img_response.status_code == 200:
                img_data = img_response.content

    if not img_data:
        return None, None, prompt, model_used

    output_dir = Path(settings.images_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{_slugify(term)}.png"
    file_path = output_dir / filename
    file_path.write_bytes(img_data)

    return None, str(file_path), prompt, model_used


def create_and_send_daily_flashcard() -> dict[str, Any]:
    """Generates linguistic content and saves to DB."""
    print("--- Phase 1: Text Generation (Fast) ---")
    term = get_next_beginner_term()
    content = build_linguistic_content(term)
    
    print(f"Linguistic content for '{term}' prepared.")

    # Supabase insert
    supabase = get_supabase()
    response = supabase.table("flashcards").insert({
        "italian_text": content["italian_text"],
        "phonetic": content["phonetic"],
        "english_translation": content["english_translation"],
        "example_sentence": content["example_sentence"],
        "difficulty": "beginner",
        "sent_channel": "telegram",
        "sent_at": _utc_now_iso(),
        "created_at": _utc_now_iso(),
    }).execute()
    
    flashcard_id = response.data[0]["id"] if response.data else 0

    print("Phase 1 Complete.")
    return {
        "status": "data_prepared",
        "flashcard_id": flashcard_id,
        "italian_text": content["italian_text"],
        "phonetic": content["phonetic"],
        "english_translation": content["english_translation"],
        "example_sentence": content["example_sentence"]
    }


def background_image_task(term: str, flashcard_id: int, phonetic: str = "", translation: str = "", example_sentence: str = ""):
    """Heavy lifting for image generation. Sends ONE consolidated message with the image + text."""
    print(f"--- Phase 2: Image Generation Task for '{term}' ---")
    try:
        image_url, image_path, image_prompt, model_used = generate_image_for_term(term, phonetic, translation)
        
        caption = (
            f"🇮🇹 Daily Italian Flashcard\n\n"
            f"🟩 Italian: {term}\n"
            f"🔊 Pronunciation: {phonetic}\n"
            f"🇬🇧 English: {translation}\n\n"
            f"📝 Example:\n_{example_sentence}_"
        )

        if image_path:
            print(f"Sending consolidated message to Telegram (Model: {model_used})")
            send_telegram_message(
                caption,
                image_path=image_path
            )
            
            # Update Supabase
            supabase = get_supabase()
            supabase.table("flashcards") \
                .update({"image_url": image_path, "prompt_used": f"[{model_used}] {image_prompt}"}) \
                .eq("id", flashcard_id) \
                .execute()
            print("Phase 2 Complete.")
        else:
            print("Image generation failed. Sending text-only fallback.")
            send_telegram_message(caption)
    except Exception as e:
        print(f"Background image task failed: {e}")
        try:
            fallback_text = f"🇮🇹 Daily Italian Flashcard\n\nItalian: {term}\nEnglish: {translation}"
            send_telegram_message(fallback_text)
        except:
            pass


def list_flashcards(limit: int = 100) -> list[dict[str, Any]]:
    supabase = get_supabase()
    response = supabase.table("flashcards") \
        .select("*") \
        .order("created_at", descending=True) \
        .limit(limit) \
        .execute()
    return response.data if response.data else []


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")[:40]
