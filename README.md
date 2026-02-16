# Italian Flashcard Service (Telegram-first MVP)

This service auto-generates and auto-sends **one beginner Italian flashcard daily at 08:00 Cape Town time** (`Africa/Johannesburg`) to Telegram.

## Features

- Daily scheduled job at 08:00 (Cape Town timezone)
- One shared daily card (single-user/single-audience setup)
- Beginner term source list stored locally in JSON and persisted in SQLite
- Flashcard content includes:
  - Italian word/phrase
  - Phonetic pronunciation
  - English translation
  - Image prompt (and optional generated image via GPT Image model)
- Telegram delivery
- API endpoint to view previously generated cards (for website/archive integration)

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp .env.example .env
# then fill TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, OPENAI_API_KEY
```

4. Run server:

```bash
uvicorn app.main:app --reload
```

## API endpoints

- `GET /health` — health check
- `POST /flashcards/generate-now` — generate+send immediately (manual trigger)
- `GET /flashcards?limit=100` — list historical cards for website display

## Notes

- Timezone is set to `Africa/Johannesburg` (used by Cape Town).
- If `OPENAI_API_KEY` is missing, the app still runs but inserts placeholder pronunciation/translation and skips image generation.
- Telegram currently sends remote image URLs only; local image upload can be added later.

## Website integration

You can build a simple frontend page that calls `GET /flashcards` and renders each saved card.
That gives you a complete archive of all previously generated content.
