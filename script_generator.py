import json
import random
from pathlib import Path

RHYMES_FILE = Path("data/rhymes.json")
UPLOADED_FILE = Path("data/uploaded.json")

SLOT_PREFERENCES = {
    "dawn": ["dawn", "morning"],
    "morning": ["morning", "dawn", "afternoon"],
    "afternoon": ["afternoon", "morning", "afterschool"],
    "afterschool": ["afterschool", "afternoon", "morning"],
    "evening": ["evening", "dawn"],
}


def load_rhymes():
    with open(RHYMES_FILE) as f:
        return json.load(f)


def load_uploaded():
    if not UPLOADED_FILE.exists():
        return []
    with open(UPLOADED_FILE) as f:
        return json.load(f)


def mark_uploaded(rhyme_id):
    uploaded = load_uploaded()
    uploaded.append(rhyme_id)
    with open(UPLOADED_FILE, "w") as f:
        json.dump(uploaded, f, indent=2)


def get_next_rhyme(slot: str) -> dict:
    rhymes = load_rhymes()
    uploaded = load_uploaded()

    remaining = [r for r in rhymes if r["id"] not in uploaded]

    if not remaining:
        # All rhymes used — reset cycle
        with open(UPLOADED_FILE, "w") as f:
            json.dump([], f)
        remaining = rhymes

    # Prefer slot-matched rhymes
    preferred_slots = SLOT_PREFERENCES.get(slot, [slot])
    for preferred in preferred_slots:
        slot_matches = [r for r in remaining if r.get("slot_preference") == preferred]
        if slot_matches:
            return random.choice(slot_matches)

    return random.choice(remaining)
