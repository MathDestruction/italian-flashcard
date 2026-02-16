from fastapi import FastAPI, HTTPException
from app.flashcards import create_and_send_daily_flashcard

app = FastAPI()

@app.get("/api/cron")
async def cron_handler():
    try:
        result = create_and_send_daily_flashcard()
        return {"status": "success", "data": result}
    except Exception as e:
        # In a real app, you might want to log this to a service
        return {"status": "error", "detail": str(e)}
