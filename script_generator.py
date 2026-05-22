"""
script_generator.py — Soundscape theme selection with no-repeat tracking.
"""

import json
import random
from pathlib import Path

SOUNDSCAPES_FILE = Path("data/soundscapes.json")
UPLOADED_FILE = Path("data/uploaded.json")


def load_soundscapes():
    with open(SOUNDSCAPES_FILE) as f:
        return json.load(f)


def load_uploaded():
    if not UPLOADED_FILE.exists():
        return []
    with open(UPLOADED_FILE) as f:
        return json.load(f)


def mark_uploaded(theme_id):
    uploaded = load_uploaded()
    uploaded.append(theme_id)
    with open(UPLOADED_FILE, "w") as f:
        json.dump(uploaded, f, indent=2)


def get_next_theme(slot=None):
    """Pick a soundscape theme not yet uploaded. Auto-resets when all are used."""
    themes = load_soundscapes()
    uploaded = load_uploaded()

    remaining = [t for t in themes if t["id"] not in uploaded]
    if not remaining:
        # Every theme used — reset the cycle.
        with open(UPLOADED_FILE, "w") as f:
            json.dump([], f)
        remaining = themes

    return random.choice(remaining)
