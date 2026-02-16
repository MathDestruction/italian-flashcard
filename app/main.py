from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/flashcards/generate-now")
def generate_now() -> dict:
    try:
        return create_and_send_daily_flashcard()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/flashcards")
def get_flashcards(limit: int = 100) -> dict:
    return {"items": list_flashcards(limit=limit)}
