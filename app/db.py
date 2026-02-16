import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS source_terms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  italian_text TEXT NOT NULL UNIQUE,
  category TEXT,
  difficulty TEXT NOT NULL DEFAULT 'beginner',
  used INTEGER NOT NULL DEFAULT 0,
  used_at TEXT
);

CREATE TABLE IF NOT EXISTS flashcards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  italian_text TEXT NOT NULL,
  phonetic TEXT NOT NULL,
  english_translation TEXT NOT NULL,
  image_url TEXT,
  prompt_used TEXT,
  difficulty TEXT NOT NULL DEFAULT 'beginner',
  sent_channel TEXT,
  sent_at TEXT,
  created_at TEXT NOT NULL
);
"""


def init_db() -> None:
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.touch(exist_ok=True)
    with sqlite3.connect(settings.db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
