import os
from dotenv import load_dotenv
from pathlib import Path
import json

# Load env vars
load_dotenv()

from app.db import init_db
from app.flashcards import create_and_send_daily_flashcard, seed_beginner_terms_if_empty

def run_test():
    print("🚀 Starting Italian Flashcard Test...")
    
    # 1. Initialize DB and Seed
    print("📦 Initializing database...")
    init_db()
    seed_beginner_terms_if_empty()
    
    # 2. Trigger Flashcard Generation
    print("🎨 Generating flashcard and sending to Telegram...")
    try:
        result = create_and_send_daily_flashcard()
        print("✅ Success!")
        print(json.dumps(result, indent=2))
        print(f"\nCheck your Telegram channel for the '{result['italian_text']}' flashcard!")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    run_test()
