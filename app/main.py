from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, BackgroundTasks

from app.config import settings
from app.db import init_db
from app.flashcards import create_and_send_daily_flashcard, list_flashcards, seed_beginner_terms_if_empty

app = FastAPI(title="Italian Flashcard Service")
scheduler = BackgroundScheduler(timezone=settings.timezone)


@app.on_event("startup")
def startup() -> None:
    init_db()
    seed_beginner_terms_if_empty()

    scheduler.add_job(
        create_and_send_daily_flashcard,
        CronTrigger(hour=settings.schedule_hour, minute=settings.schedule_minute, timezone=settings.timezone),
        id="daily_italian_flashcard",
        replace_existing=True,
    )
    scheduler.start()


@app.on_event("shutdown")
def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/")
def read_root():
    return {
        "message": "Italian Flashcard Service is running!",
        "endpoints": {
            "health": "/health",
            "diagnostics": "/diagnostics (Test each component)",
            "generate_now_get": "/flashcards/generate-now (GET)",
            "list_flashcards": "/flashcards"
        },
        "config_debug": {
            "is_vercel": settings.is_vercel,
            "db_path": settings.db_path,
            "has_openai": bool(settings.openai_api_key),
            "has_telegram_token": bool(settings.telegram_bot_token),
            "chat_id": settings.telegram_chat_id[:5] + "..." if settings.telegram_chat_id else None
        }
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/flashcards/generate-now")
@app.post("/flashcards/generate-now")
def generate_now(background_tasks: BackgroundTasks) -> dict:
    """Trigger a flashcard generation. Text is sent immediately, image in background."""
    from app.flashcards import create_and_send_daily_flashcard, background_image_task
    
    print("Manual trigger: Starting Generation...")
    try:
        # Phase 1: Text generation and sending (This is fast)
        result = create_and_send_daily_flashcard()
        
        # Phase 2: Schedule image generation (This is slow, runs after request returns)
        background_tasks.add_task(
            background_image_task, 
            term=result['italian_text'], 
            flashcard_id=result['flashcard_id']
        )
        
        print(f"Success: Text sent for {result['italian_text']}. Image task scheduled.")
        return {
            "status": "success", 
            "message": "Flashcard text sent! Image will follow in 20-30 seconds.",
            "data": result
        }
    except Exception as exc:
        print(f"Error during manual trigger: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/flashcards")
def get_flashcards(limit: int = 100) -> dict:
    return {"items": list_flashcards(limit=limit)}


@app.get("/diagnostics")
def diagnostics() -> dict:
    """Run diagnostic tests on all components."""
    from app.diagnostics import run_all_diagnostics
    return run_all_diagnostics()
