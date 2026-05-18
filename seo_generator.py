BASE_TAGS = [
    "nursery rhymes", "kids songs", "children songs", "baby songs", "toddler songs",
    "kids music", "preschool songs", "animated nursery rhymes", "nursery rhymes for babies",
    "nursery rhymes for toddlers", "nursery rhymes for kids", "kids youtube",
    "children music", "learning songs for kids", "bedtime songs", "baby rhymes",
    "classic nursery rhymes", "youtube shorts", "shorts", "viral shorts",
    "kids shorts", "lullaby", "abc song", "phonics", "alphabet song",
    "baby learning", "fun for kids", "educational kids video", "toddler learning",
    "baby development", "kids entertainment", "nursery rhyme 2024", "nursery rhyme 2025",
]

SLOT_DESCRIPTORS = {
    "dawn": ("Sunrise", "early morning"),
    "morning": ("Morning", "morning"),
    "afternoon": ("Afternoon", "afternoon"),
    "afterschool": ("Playtime", "after school"),
    "evening": ("Bedtime", "evening"),
}

SLOT_AUDIENCE = {
    "dawn": "Early Risers 🌅",
    "morning": "Good Morning Babies ☀️",
    "afternoon": "Playtime Fun 🎈",
    "afterschool": "After School Fun 🎒",
    "evening": "Lullaby & Bedtime 🌙",
}


def generate_title(rhyme: dict, slot: str) -> str:
    name = rhyme["title"]
    emoji = rhyme.get("emoji", "🎵")
    audience = SLOT_AUDIENCE.get(slot, "Kids 🎵")
    title = f"{name} {emoji} | {audience} | Nursery Rhymes #Shorts"
    return title[:100]


def generate_description(rhyme: dict, slot: str) -> str:
    name = rhyme["title"]
    emoji = rhyme.get("emoji", "🎵")
    lyrics = "\n".join(line["text"] for line in rhyme["lines"])
    rhyme_tag = name.replace(" ", "")

    return f"""{name} {emoji} | Nursery Rhymes for Kids

{lyrics}

🌟 New nursery rhyme every single day — Subscribe so you never miss one! 🔔

👶 Perfect for:
✅ Babies & Toddlers (0–5 years)
✅ Preschool & Kindergarten
✅ Learning through songs and music
✅ Bedtime, playtime & car rides
✅ Parents & caregivers at home

📌 About this video:
{name} is a beloved classic nursery rhyme enjoyed by children worldwide.
This colorful animated version features bright visuals designed to engage
and delight babies, toddlers, and young children!

🎵 Watch more nursery rhymes on our channel for daily new videos!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#NurseryRhymes #KidsSongs #{rhyme_tag} #BabySongs #ToddlerSongs
#ChildrenSongs #LearningForKids #KidsMusic #PreschoolSongs
#BabyRhymes #AnimatedNurseryRhymes #KidsYouTube #Lullaby
#KidsShorts #YouTubeShorts #Shorts #ViralKidsVideo
#BabyLearning #FunForKids #EducationalKids #NurseryRhyme2025
#ToddlerActivities #BabyDevelopment #KidsEntertainment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""


def _clean_tag(tag: str) -> str:
    """Keep ASCII letters/digits/spaces only, cap at 30 chars."""
    import re
    tag = re.sub(r'[^A-Za-z0-9 ]', '', tag)
    tag = re.sub(r'\s+', ' ', tag).strip().lower()
    return tag[:30]


def generate_tags(rhyme: dict) -> list:
    name = rhyme["title"]
    name_lower = name.lower()
    seo_keywords = rhyme.get("seo_keywords", [])

    rhyme_tags = [
        name_lower,
        f"{name_lower} nursery rhyme",
        f"{name_lower} for kids",
        f"{name_lower} animated",
        f"{name_lower} song",
        f"{name_lower} for babies",
        f"{name_lower} for toddlers",
    ] + seo_keywords

    all_tags = list(dict.fromkeys(rhyme_tags + BASE_TAGS))

    # Clean each tag, drop empties
    all_tags = [_clean_tag(t) for t in all_tags if _clean_tag(t)]

    # YouTube counts tags-with-spaces as len+2 (quotes wrap them).
    # Keep a safety budget of 400 chars to avoid the 500 limit.
    result = []
    total_chars = 0
    for tag in all_tags:
        cost = len(tag) + (2 if " " in tag else 0) + 1
        if total_chars + cost > 400:
            break
        result.append(tag)
        total_chars += cost

    return result


def generate_seo(rhyme: dict, slot: str) -> dict:
    return {
        "title": generate_title(rhyme, slot),
        "description": generate_description(rhyme, slot),
        "tags": generate_tags(rhyme),
        "category_id": "22",
    }
