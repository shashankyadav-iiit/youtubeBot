import os
import random
import urllib.request
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    VideoClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, ImageClip
)

TARGET_W = 2160
TARGET_H = 3840
FPS = 30
TOTAL_DURATION = 30.0
INTRO_DURATION = 0.5
OUTRO_DURATION = 1.5
CONTENT_DURATION = TOTAL_DURATION - INTRO_DURATION - OUTRO_DURATION  # 28s

FONT_PATH = Path("assets/fonts/FredokaOne-Regular.ttf")
FONT_URLS = [
    "https://github.com/google/fonts/raw/refs/heads/main/ofl/fredokaone/FredokaOne-Regular.ttf",
    "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf",
]
# Mac system fonts as fallback (rounded, kid-friendly)
MAC_FALLBACK_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Rounded MT Bold.ttf",
    "/System/Library/Fonts/Supplemental/Chalkboard.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Arial.ttf",
]

SPARKLE_COLORS = [
    (255, 215, 0),   # gold
    (255, 182, 193), # pink
    (135, 206, 250), # sky blue
    (255, 255, 255), # white
    (180, 255, 180), # mint
]

BG_COLORS = [
    (255, 100, 150),
    (100, 150, 255),
    (100, 210, 100),
    (255, 180, 50),
    (180, 100, 255),
    (50, 200, 200),
]

EFFECTS = ["zoom_in", "zoom_out", "pan_right", "pan_left", "zoom_in", "zoom_out"]


def ensure_font():
    """Download Fredoka One font, or locate a Mac system font fallback."""
    if FONT_PATH.exists():
        return
    FONT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Try downloading from each URL
    for url in FONT_URLS:
        try:
            print(f"  Downloading font from {url[:60]}...")
            urllib.request.urlretrieve(url, str(FONT_PATH))
            if FONT_PATH.exists() and FONT_PATH.stat().st_size > 10000:
                print("  Font downloaded successfully.")
                return
        except Exception as e:
            print(f"  Font download failed: {e}")

    # Fall back to Mac system fonts — copy one into assets/fonts/
    for mac_font in MAC_FALLBACK_FONTS:
        if Path(mac_font).exists():
            import shutil
            print(f"  Using system font: {mac_font}")
            shutil.copy(mac_font, str(FONT_PATH))
            return

    print("  No font found — PIL default will be used.")


def load_font(size: int):
    """Load the project font at given size, with graceful fallback."""
    if FONT_PATH.exists():
        try:
            return ImageFont.truetype(str(FONT_PATH), size)
        except Exception:
            pass
    # Try Mac system fonts directly
    for mac_font in MAC_FALLBACK_FONTS:
        if Path(mac_font).exists():
            try:
                return ImageFont.truetype(mac_font, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _apply_ken_burns(base_img: np.ndarray, t: float, duration: float, effect: str) -> np.ndarray:
    """Apply Ken Burns zoom/pan + subtle breathing wobble for life."""
    h, w = base_img.shape[:2]
    progress = t / max(duration, 0.001)
    # Breathing wobble: gentle oscillation on top of base scale
    breathe = 0.015 * np.sin(t * 2.0 * np.pi * 0.6)
    scale = 1.0

    if effect == "zoom_in":
        scale = 1.0 + 0.12 * progress + breathe
    elif effect == "zoom_out":
        scale = 1.12 - 0.12 * progress + breathe
    elif effect == "pan_right":
        scale = 1.08 + breathe
    elif effect == "pan_left":
        scale = 1.08 + breathe

    crop_w = int(w / scale)
    crop_h = int(h / scale)

    if effect == "pan_right":
        x0 = int((w - crop_w) * progress)
    elif effect == "pan_left":
        x0 = int((w - crop_w) * (1.0 - progress))
    else:
        x0 = (w - crop_w) // 2

    y0 = (h - crop_h) // 2
    x0 = max(0, min(x0, w - crop_w))
    y0 = max(0, min(y0, h - crop_h))

    cropped = base_img[y0:y0 + crop_h, x0:x0 + crop_w]
    return np.array(Image.fromarray(cropped).resize((w, h), Image.LANCZOS))


def _draw_sparkles(draw: ImageDraw.ImageDraw, t: float, sparkle_data: list):
    """Draw rotating, fading sparkle stars."""
    for sp in sparkle_data:
        alpha_val = (np.sin(sp["freq"] * t * 2 * np.pi + sp["phase"]) + 1) / 2
        if alpha_val < 0.25:
            continue
        x, y = sp["x"], sp["y"]
        s = int(sp["size"] * alpha_val)
        if s < 2:
            continue
        color = sp["color"]
        # Rotation angle based on time
        angle = t * sp["freq"] * 2.0
        cos_a, sin_a = np.cos(angle), np.sin(angle)

        # 4-point star with rotation
        for arm_angle in [0, np.pi / 4, np.pi / 2, 3 * np.pi / 4]:
            a = arm_angle + angle
            dx, dy = s * np.cos(a), s * np.sin(a)
            draw.line([(x - dx, y - dy), (x + dx, y + dy)],
                      fill=color, width=max(2, s // 4))
        # Bright center
        draw.ellipse([x - s // 3, y - s // 3, x + s // 3, y + s // 3],
                     fill=(255, 255, 255))


# Floating emoji-like shapes that rise up the screen
FLOATING_SHAPES = ["heart", "musicnote", "star", "circle"]
FLOATING_COLORS = [
    (255, 100, 150), (255, 200, 80), (140, 220, 255),
    (180, 255, 140), (255, 150, 220), (255, 180, 80),
]


def _draw_heart_shape(draw, cx, cy, size, color):
    """Draw a heart at (cx, cy)."""
    s = size
    draw.ellipse([cx - s, cy - s, cx, cy], fill=color)
    draw.ellipse([cx, cy - s, cx + s, cy], fill=color)
    draw.polygon([(cx - s, cy - s // 6), (cx, cy + s * 1.3),
                  (cx + s, cy - s // 6)], fill=color)


def _draw_music_note(draw, cx, cy, size, color):
    """Draw a simple music note (eighth note)."""
    s = size
    # Note head (oval)
    draw.ellipse([cx - s, cy - int(s * 0.6), cx, cy], fill=color)
    # Stem
    draw.rectangle([cx - int(s * 0.18), cy - int(s * 3), cx, cy - int(s * 0.3)], fill=color)
    # Flag
    draw.polygon([
        (cx, cy - int(s * 3)),
        (cx + int(s * 1.2), cy - int(s * 2.2)),
        (cx + int(s * 0.4), cy - int(s * 1.5)),
        (cx, cy - int(s * 2)),
    ], fill=color)


def _draw_star_filled(draw, cx, cy, r, color):
    points = []
    for k in range(10):
        angle = np.pi / 5 * k - np.pi / 2
        radius = r if k % 2 == 0 else r * 0.45
        points.append((cx + radius * np.cos(angle), cy + radius * np.sin(angle)))
    draw.polygon(points, fill=color)


def _draw_floating_elements(draw, t: float, float_data: list):
    """Draw shapes that rise from bottom to top with gentle horizontal sway."""
    for fd in float_data:
        # Rise from below screen to above over a loop period
        period = fd["period"]
        phase = (t / period + fd["phase_offset"]) % 1.0
        y = int(TARGET_H + 100 - phase * (TARGET_H + 300))
        # Side-to-side sway
        sway = int(60 * np.sin(t * 1.5 * np.pi + fd["sway_phase"]))
        x = fd["x_base"] + sway

        # Fade in/out near edges
        if phase < 0.05:
            opacity = phase / 0.05
        elif phase > 0.92:
            opacity = (1.0 - phase) / 0.08
        else:
            opacity = 1.0
        if opacity < 0.1:
            continue

        size = fd["size"]
        color = fd["color"]
        # Dim color by opacity (approximation by blending toward dark)
        col = tuple(int(c * opacity) for c in color)

        shape = fd["shape"]
        if shape == "heart":
            _draw_heart_shape(draw, x, y, size, col)
        elif shape == "musicnote":
            _draw_music_note(draw, x, y, size, col)
        elif shape == "star":
            _draw_star_filled(draw, x, y, size, col)
        else:
            draw.ellipse([x - size, y - size, x + size, y + size], fill=col)


def _draw_rainbow_border(draw, t: float):
    """Animated rainbow color-cycling border around the frame."""
    border_w = 30
    # Hue cycle
    hue_offset = (t * 60) % 360  # 60 degrees per second

    # Draw segments of varying colors around the perimeter
    segments = 20
    perim = 2 * (TARGET_W + TARGET_H)
    for seg in range(segments):
        # Compute hue for this segment
        hue = (hue_offset + (seg * 360 / segments)) % 360
        rgb = _hsv_to_rgb(hue, 1.0, 1.0)

        # Position along perimeter
        start_dist = seg * perim / segments
        end_dist = (seg + 1) * perim / segments
        _draw_perim_segment(draw, start_dist, end_dist, rgb, border_w)


def _hsv_to_rgb(h, s, v):
    """Convert HSV (h in degrees) to RGB tuple."""
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if 0 <= h < 60: r, g, b = c, x, 0
    elif 60 <= h < 120: r, g, b = x, c, 0
    elif 120 <= h < 180: r, g, b = 0, c, x
    elif 180 <= h < 240: r, g, b = 0, x, c
    elif 240 <= h < 300: r, g, b = x, 0, c
    else: r, g, b = c, 0, x
    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


def _draw_perim_segment(draw, d_start, d_end, color, w):
    """Approximate the perimeter segment with rectangles at top/right/bottom/left."""
    # Just draw all 4 sides as a rectangle border, dividing the perimeter
    perim = 2 * (TARGET_W + TARGET_H)
    n_steps = max(2, int((d_end - d_start) / 50))
    for i in range(n_steps):
        d = d_start + (d_end - d_start) * i / n_steps
        x, y = _perim_to_xy(d)
        draw.rectangle([x - w // 2, y - w // 2, x + w // 2, y + w // 2], fill=color)


def _perim_to_xy(d):
    """Map perimeter distance d to (x, y) coordinate on the border."""
    # Perimeter: top → right → bottom → left
    if d < TARGET_W:
        return (int(d), 0)
    d -= TARGET_W
    if d < TARGET_H:
        return (TARGET_W, int(d))
    d -= TARGET_H
    if d < TARGET_W:
        return (TARGET_W - int(d), TARGET_H)
    d -= TARGET_W
    return (0, TARGET_H - int(d))


def _draw_karaoke_text(draw: ImageDraw.ImageDraw, text: str, progress: float, t: float):
    """Karaoke text with bouncing current word and rainbow-cycling active color."""
    words = text.split()
    if not words:
        return

    n_words = len(words)
    current_word = min(int(progress * n_words), n_words - 1)

    font_active = load_font(220)
    font_normal = load_font(156)

    total_width = 0
    word_widths = []
    for i, word in enumerate(words):
        font = font_active if i == current_word else font_normal
        bbox = font.getbbox(word + " ")
        w = bbox[2] - bbox[0]
        word_widths.append(w)
        total_width += w

    pill_y = int(TARGET_H * 0.76)
    pill_h = 360
    margin = 60

    # Animated pill: dark blue gradient with subtle pulse
    pulse = 0.5 + 0.5 * np.sin(t * 2 * np.pi * 1.2)
    border_color = (
        int(60 + 80 * pulse),
        int(80 + 60 * pulse),
        int(180 + 60 * pulse),
    )
    # Outer glow rectangle
    draw.rectangle(
        [(margin - 8, pill_y - 38), (TARGET_W - margin + 8, pill_y + pill_h + 8)],
        fill=border_color,
    )
    # Inner dark pill
    draw.rectangle(
        [(margin, pill_y - 30), (TARGET_W - margin, pill_y + pill_h)],
        fill=(15, 10, 50),
    )

    x_start = max(margin + 30, (TARGET_W - total_width) // 2)
    x_cursor = x_start

    # Current-word bounce (scale-up effect approximated via vertical lift)
    bounce_lift = int(20 * abs(np.sin(t * 4 * np.pi)))

    # Rainbow color cycling on active word
    active_hue = (t * 180) % 360
    active_color = _hsv_to_rgb(active_hue, 0.6, 1.0)

    for i, word in enumerate(words):
        font = font_active if i == current_word else font_normal
        if i < current_word:
            color = (180, 180, 200)
        elif i == current_word:
            color = active_color
        else:
            color = (130, 130, 160)

        word_y = pill_y - (bounce_lift if i == current_word else 0)

        # Thick shadow for 4K readability
        for dx, dy in [(8, 8), (-4, 8), (8, -4)]:
            draw.text((x_cursor + dx, word_y + dy), word + " ", font=font, fill=(0, 0, 0))
        draw.text((x_cursor, word_y), word + " ", font=font, fill=color)
        x_cursor += word_widths[i]


def create_segment_clip(image_path: str, text: str, duration: float, effect: str,
                        sparkle_data: list, float_data: list) -> VideoClip:
    """Lyric segment: breathing Ken Burns + rotating sparkles + floating shapes
    + rainbow border + bouncing karaoke text."""
    img = Image.open(image_path).convert("RGB").resize((TARGET_W, TARGET_H), Image.LANCZOS)
    base_array = np.array(img)

    def make_frame(t):
        kb_frame = _apply_ken_burns(base_array, t, duration, effect)
        frame_img = Image.fromarray(kb_frame.astype(np.uint8))
        draw = ImageDraw.Draw(frame_img)
        _draw_rainbow_border(draw, t)
        _draw_floating_elements(draw, t, float_data)
        _draw_sparkles(draw, t, sparkle_data)
        progress = t / max(duration, 0.001)
        _draw_karaoke_text(draw, text, progress, t)
        return np.array(frame_img)

    return VideoClip(make_frame, duration=duration).set_fps(FPS)


def create_intro_clip(title: str, duration: float = INTRO_DURATION) -> VideoClip:
    """Animated intro with channel title pop-in. Duration matches time before first voice line."""
    bg_color = (30, 20, 80)
    font = load_font(180)
    font_sub = load_font(108)

    def make_frame(t):
        progress = min(t / max(duration, 0.01), 1.0)
        scale = 0.5 + 0.5 * progress  # scale up from 50% to 100%
        alpha = int(255 * progress)

        img = Image.new("RGB", (TARGET_W, TARGET_H), bg_color)
        draw = ImageDraw.Draw(img)

        # Draw stars background
        rng = random.Random(42)
        for _ in range(30):
            sx = rng.randint(0, TARGET_W)
            sy = rng.randint(0, TARGET_H)
            sr = rng.randint(6, 18)
            brightness = int(100 + 155 * progress)
            draw.ellipse([(sx - sr, sy - sr), (sx + sr, sy + sr)],
                         fill=(brightness, brightness, 200))

        # Title text centered
        short_title = title[:28] + "..." if len(title) > 28 else title
        bbox = font.getbbox(short_title)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (TARGET_W - int(tw * scale)) // 2
        ty = TARGET_H // 2 - 60

        draw.text((tx + 2, ty + 2), short_title, font=font, fill=(0, 0, 0))
        draw.text((tx, ty), short_title, font=font, fill=(255, 240, 80))

        sub = "Nursery Rhymes for Kids 🎵"
        sbbox = font_sub.getbbox(sub)
        sw = sbbox[2] - sbbox[0]
        draw.text(((TARGET_W - sw) // 2, ty + th + 20), sub,
                  font=font_sub, fill=(180, 220, 255))

        return np.array(img)

    return VideoClip(make_frame, duration=duration).set_fps(FPS)


def create_outro_clip() -> VideoClip:
    """1.5s subscribe outro with bell animation."""
    bg_color = (20, 60, 20)
    font_big = load_font(192)    # scaled for 4K
    font_med = load_font(132)
    font_small = load_font(100)

    def make_frame(t):
        progress = min(t / OUTRO_DURATION, 1.0)
        img = Image.new("RGB", (TARGET_W, TARGET_H), bg_color)
        draw = ImageDraw.Draw(img)

        # Animated confetti
        rng = random.Random(int(t * 10))
        for _ in range(20):
            cx = rng.randint(0, TARGET_W)
            cy = rng.randint(0, TARGET_H)
            color = random.choice([(255, 200, 0), (255, 100, 100),
                                   (100, 200, 255), (200, 255, 100)])
            draw.rectangle([(cx, cy), (cx + 24, cy + 24)], fill=color)

        # Subscribe text
        bell_bounce = int(10 * abs(np.sin(t * 6)))
        sub_text = "Subscribe! 🔔"
        sbbox = font_big.getbbox(sub_text)
        sw = sbbox[2] - sbbox[0]
        draw.text(((TARGET_W - sw) // 2 + 2, TARGET_H // 2 - 80 + bell_bounce + 2),
                  sub_text, font=font_big, fill=(0, 0, 0))
        draw.text(((TARGET_W - sw) // 2, TARGET_H // 2 - 80 + bell_bounce),
                  sub_text, font=font_big, fill=(255, 240, 80))

        line2 = "New video every day!"
        l2bbox = font_med.getbbox(line2)
        l2w = l2bbox[2] - l2bbox[0]
        draw.text(((TARGET_W - l2w) // 2, TARGET_H // 2), line2,
                  font=font_med, fill=(200, 255, 200))

        line3 = "Nursery Rhymes for Kids"
        l3bbox = font_small.getbbox(line3)
        l3w = l3bbox[2] - l3bbox[0]
        draw.text(((TARGET_W - l3w) // 2, TARGET_H // 2 + 70), line3,
                  font=font_small, fill=(180, 200, 255))

        return np.array(img)

    return VideoClip(make_frame, duration=OUTRO_DURATION).set_fps(FPS)


def _make_sparkle_data(n: int = 16) -> list:
    """Pre-generate sparkle parameters for one clip."""
    return [
        {
            "x": random.randint(50, TARGET_W - 50),
            "y": random.randint(80, int(TARGET_H * 0.65)),
            "phase": random.uniform(0, 6.28),
            "freq": random.uniform(1.2, 3.0),
            "size": random.randint(25, 60),
            "color": random.choice(SPARKLE_COLORS),
        }
        for _ in range(n)
    ]


def _make_float_data(n: int = 10) -> list:
    """Pre-generate floating shape (heart/star/note) animation parameters."""
    return [
        {
            "x_base": random.randint(80, TARGET_W - 80),
            "size": random.randint(50, 110),
            "color": random.choice(FLOATING_COLORS),
            "shape": random.choice(FLOATING_SHAPES),
            "period": random.uniform(4.0, 8.0),
            "phase_offset": random.random(),
            "sway_phase": random.uniform(0, 6.28),
        }
        for _ in range(n)
    ]


def build_video(rhyme: dict, audio_path: str, temp_dir: str, output_path: str,
                segments: list = None):
    """
    Assemble the full 30-second video.
    segments: list of (start_ms, end_ms) per lyric line from audio_generator.
    When provided, each scene clip matches the exact duration of its audio line.
    """
    ensure_font()

    lines = rhyme["lines"]
    n_lines = len(lines)

    # --- Sync strategy: start-to-start timing ---
    # Scene i is visible from when audio line i starts until audio line i+1 starts.
    # Last scene holds from its start until the outro begins at (TOTAL_DURATION - OUTRO_DURATION).
    # This guarantees: scene change happens exactly when the voice switches lines.
    # Intro lasts from t=0 until the first line starts speaking.

    OUTRO_START_MS = int((TOTAL_DURATION - OUTRO_DURATION) * 1000)  # 28500ms

    if segments and len(segments) == n_lines:
        # Intro duration = time before first voice line
        intro_dur = max(0.3, segments[0][0] / 1000.0)

        # Scene i: from line i start → line i+1 start (or outro start for last)
        seg_durations = []
        for i in range(n_lines):
            start_ms = segments[i][0]
            end_ms = segments[i + 1][0] if i < n_lines - 1 else OUTRO_START_MS
            seg_durations.append(max(0.5, (end_ms - start_ms) / 1000.0))

        total_check = intro_dur + sum(seg_durations) + OUTRO_DURATION
        print(f"  Sync timeline: {intro_dur:.2f}s intro + "
              f"{[f'{d:.2f}s' for d in seg_durations]} + "
              f"{OUTRO_DURATION}s outro = {total_check:.2f}s")
    else:
        intro_dur = INTRO_DURATION
        seg_durations = [CONTENT_DURATION / n_lines] * n_lines
        print(f"  Equal split fallback: {n_lines} × {CONTENT_DURATION / n_lines:.2f}s")

    clips = []

    # Intro — duration matches gap before first voice line
    intro = create_intro_clip(rhyme["title"], duration=intro_dur)
    clips.append(intro)

    # Content segments — each clip shows exactly while its line plays
    for i, line in enumerate(lines):
        image_path = os.path.join(temp_dir, f"scene_{i}.png")
        effect = EFFECTS[i % len(EFFECTS)]
        sparkles = _make_sparkle_data()
        floats = _make_float_data()
        seg_clip = create_segment_clip(
            image_path, line["text"], seg_durations[i], effect, sparkles, floats
        )
        if i > 0:
            seg_clip = seg_clip.crossfadein(0.3)
        clips.append(seg_clip)

    # Outro — always last 1.5s
    outro = create_outro_clip()
    outro = outro.crossfadein(0.3)
    clips.append(outro)

    print("  Concatenating clips...")
    final = concatenate_videoclips(clips, method="compose")
    final = final.set_duration(TOTAL_DURATION)

    print("  Adding audio...")
    audio = AudioFileClip(audio_path).set_duration(TOTAL_DURATION)
    final = final.set_audio(audio)

    print(f"  Writing video to {output_path}...")
    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="slow",          # better compression quality at 4K
        bitrate="40000k",       # 40 Mbps — broadcast-quality 4K
        audio_bitrate="320k",   # high-quality audio
        logger=None,
        ffmpeg_params=["-crf", "16"],  # visually lossless
    )
    print(f"  Video complete: {output_path}")
