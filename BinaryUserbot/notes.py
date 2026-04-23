import os
import json
from datetime import datetime
from config import NOTES_FILE


def load_notes() -> list:
    if os.path.exists(NOTES_FILE):
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_notes(notes: list):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


def add_note(text: str) -> int:
    notes = load_notes()
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    notes.append({"time": now, "text": text})
    save_notes(notes)
    return len(notes)
