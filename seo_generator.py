"""
seo_generator.py — Sleep-niche YouTube SEO (title, description, tags).
"""

import random

BASE_TAGS = [
    "sleep sounds", "sleeping sounds", "relaxing sounds", "sleep music",
    "deep sleep", "insomnia relief", "fall asleep fast", "calming sounds",
    "relaxation", "ambient sounds", "sounds for sleeping", "study sounds",
    "focus sounds", "meditation sounds", "stress relief", "sleep aid",
    "white noise", "soothing sounds", "nature sounds", "black screen sleep",
    "sleep sounds black screen", "relaxing music", "sleep therapy",
    "calm sleep", "night sounds", "background sounds", "anti stress",
]

BENEFITS = [
    "Deep Sleep & Relaxation",
    "Fall Asleep Fast",
    "Insomnia Relief",
    "Sleep, Study & Focus",
    "Calm Your Mind",
    "Stress Relief & Deep Sleep",
]


def _clean_tag(tag):
    """Keep ASCII letters/digits/spaces only, cap at 30 chars."""
    import re
    tag = re.sub(r"[^A-Za-z0-9 ]", "", tag)
    tag = re.sub(r"\s+", " ", tag).strip().lower()
    return tag[:30]


def generate_title(theme, duration_hours):
    name = theme["name"]
    emoji = theme.get("emoji", "🌙")
    benefit = random.choice(BENEFITS)
    title = f"{name} {emoji} {benefit} | {duration_hours} Hours"
    return title[:100]


def generate_description(theme, duration_hours):
    name = theme["name"]
    emoji = theme.get("emoji", "🌙")
    kw = ", ".join(theme.get("seo_keywords", [])[:4])

    return f"""{name} {emoji} — {duration_hours} hours of calming sounds for deep, restful sleep.

Press play, dim the lights, and let these soothing sounds carry you into a peaceful night's sleep. This {duration_hours}-hour soundscape loops gently and consistently — perfect to leave playing all night long.

🌙 Great for:
✅ Falling asleep faster & sleeping through the night
✅ Insomnia, anxiety & stress relief
✅ Studying, reading & deep focus
✅ Relaxation, meditation & calming a busy mind
✅ Soothing babies & creating a peaceful home

🎧 For the best experience, use headphones or a speaker at a low, comfortable volume and let it play in the background.

🔔 Subscribe for new {duration_hours}-hour sleep soundscapes — rain, ocean, fireplace, forest, white noise and more.

Keywords: {kw}

#sleepsounds #relaxing #deepsleep #insomnia #sleepmusic #whitenoise #relaxation #studymusic"""


def generate_tags(theme):
    keywords = theme.get("seo_keywords", [])
    all_tags = list(dict.fromkeys(keywords + BASE_TAGS))
    all_tags = [_clean_tag(t) for t in all_tags if _clean_tag(t)]

    # YouTube counts space-containing tags as len+2 (quote-wrapped); budget 400.
    result, total = [], 0
    for tag in all_tags:
        cost = len(tag) + (2 if " " in tag else 0) + 1
        if total + cost > 400:
            break
        result.append(tag)
        total += cost
    return result


def generate_seo(theme, duration_hours):
    return {
        "title": generate_title(theme, duration_hours),
        "description": generate_description(theme, duration_hours),
        "tags": generate_tags(theme),
        "category_id": "10",   # Music — standard for sleep/ambient channels
    }
