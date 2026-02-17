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

## Image Customization

The generated flashcard images use a guided prompt from `imagePrompt.txt`. This prompt is combined with the Italian term, English translation, and pronunciation to create complete flashcard graphics.

To customize the image style:
1. Edit `imagePrompt.txt` with your desired visual style
2. The prompt should describe the overall design, layout, typography, and aesthetic
3. Each flashcard will combine your base prompt with the specific term details

## Vercel Deployment & Automation

### Important: Vercel Serverless Limitations

Vercel serverless functions don't stay running between requests, so the `BackgroundScheduler` in `main.py` **will not work** for daily automation on Vercel. You have two options:

### Option 1: Vercel Cron Jobs (Recommended)

Add to your `vercel.json`:

```json
{
  "crons": [{
    "path": "/api/cron",
    "schedule": "0 6 * * *"
  }]
}
```

Note: Vercel cron uses UTC time. For 8am Cape Town time (UTC+2), use `0 6 * * *` (6am UTC).

### Option 2: External Cron Service

Use a service like [cron-job.org](https://cron-job.org) or [EasyCron](https://www.easycron.com) to trigger:

```
GET https://italian-flashcard.vercel.app/flashcards/generate-now
```

Schedule it for 8:00am Cape Town time.

## Troubleshooting

### Duplicate Messages/Images

If you're receiving duplicate messages and images:

1. **Check if multiple triggers are active**: Ensure you're not running both the local scheduler AND calling the endpoint manually
2. **Vercel cron conflicts**: If using Vercel cron, make sure the local `BackgroundScheduler` is disabled (it won't work on Vercel anyway)
3. **Multiple endpoint calls**: Check your logs to see if `/flashcards/generate-now` is being called multiple times

The intended flow is:
- 1 text message with Italian/English/Pronunciation
- 1 image message with the complete flashcard graphic (sent 20-30 seconds later)

If you see 2 text messages and 2 images, the endpoint is likely being triggered twice.
