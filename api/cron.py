from fastapi import FastAPI, BackgroundTasks
from app.flashcards import create_and_send_daily_flashcard, background_image_task

app = FastAPI()

@app.get("/api/cron")
async def cron_handler(background_tasks: BackgroundTasks):
    try:
        # Phase 1: Prepare data
        result = create_and_send_daily_flashcard()
        
        # Phase 2: Schedule image generation
        background_tasks.add_task(
            background_image_task, 
            term=result['italian_text'], 
            flashcard_id=result['flashcard_id'],
            phonetic=result.get('phonetic', ''),
            translation=result.get('english_translation', ''),
            example_sentence=result.get('example_sentence', '')
        )
        
        return {"status": "success", "message": "Automation triggered successfully."}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
