import os
import math
import random
import time
import requests
from pathlib import Path
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
WIDTH = 2160    # 4K portrait width
HEIGHT = 3840   # 4K portrait height
WIDTH_HD = 1080  # fallback Full HD
HEIGHT_HD = 1920
MODEL = "flux"

# Bright kid-friendly color palettes per scene index
PALETTES = [
    [(255, 80, 120),  (255, 180, 50)],   # pink → yellow
    [(50, 160, 255),  (100, 230, 255)],  # blue → cyan
    [(80, 200, 80),   (200, 240, 80)],   # green → lime
    [(180, 80, 255),  (255, 120, 200)],  # purple → pink
    [(255, 140, 40),  (255, 220, 60)],   # orange → yellow
    [(40, 200, 180),  (80, 240, 140)],   # teal → mint
]

EMOJI_SHAPES = ["star", "circle", "heart", "cloud"]


def _enhance_image(img: Image.Image) -> Image.Image:
    """Apply sharpening and contrast/colour boost for crisp, vivid 4K output."""
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=160, threshold=2))
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.25)
    img = ImageEnhance.Sharpness(img).enhance(1.4)
    return img


def _try_download(prompt: str, output_path: str, w: int, h: int, timeout: int) -> bool:
    """Attempt a single Pollinations.ai download at the given resolution."""
    full_prompt = (f"{prompt}, cartoon style, ultra bright vivid colors, "
                   f"children illustration, highly detailed, no text, 4K HDR")
    url = (f"{POLLINATIONS_URL.format(prompt=quote(full_prompt))}"
           f"?width={w}&height={h}&model={MODEL}&nologo=true&enhance=true")
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200 and len(response.content) > 5000:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"    ↳ {w}×{h} failed: {e}")
    return False


def generate_scene_image(prompt: str, output_path: str, retries: int = 2) -> bool:
    """
    Download AI-generated scene image at 4K (2160×3840), falling back to
    Full HD (1080×1920) if the server is too slow. Enhances after download.
    """
    # Try 4K first, then Full HD fallback
    resolutions = [(WIDTH, HEIGHT, 150), (WIDTH_HD, HEIGHT_HD, 90)]

    for attempt in range(retries):
        for w, h, timeout in resolutions:
            print(f"    Trying {w}×{h}...")
            if _try_download(prompt, output_path, w, h, timeout):
                # Enhance the downloaded image
                try:
                    img = Image.open(output_path).convert("RGB")
                    img = _enhance_image(img)
                    # Always save at 4K by upscaling HD if needed
                    if img.size != (WIDTH, HEIGHT):
                        img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
                    img.save(output_path, "PNG", quality=100)
                except Exception:
                    pass  # keep original if enhancement fails
                return True
        if attempt < retries - 1:
            time.sleep(4)

    return False


def generate_all_scenes(lines: list, temp_dir: str) -> list:
    """Generate scene images for all lyric lines. Returns list of image paths."""
    paths = []
    for i, line in enumerate(lines):
        out_path = os.path.join(temp_dir, f"scene_{i}.png")
        prompt = line.get("scene_prompt", "colorful cartoon children illustration nursery rhyme")
        print(f"  Generating scene {i + 1}/{len(lines)}: {prompt[:50]}...")
        success = generate_scene_image(prompt, out_path)
        if not success:
            print(f"  Using vibrant fallback for scene {i + 1}")
            _generate_fallback_image(out_path, i)
        paths.append(out_path)
    return paths


def _draw_star(draw, cx, cy, r, color):
    """Draw a 5-pointed star."""
    points = []
    for k in range(10):
        angle = math.pi / 5 * k - math.pi / 2
        radius = r if k % 2 == 0 else r * 0.45
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(points, fill=color)


def _draw_cloud(draw, cx, cy, size, color):
    """Draw a simple cloud shape."""
    draw.ellipse([cx - size, cy - size // 2, cx + size, cy + size // 2], fill=color)
    draw.ellipse([cx - size // 2, cy - size, cx + size // 2, cy], fill=color)
    draw.ellipse([cx, cy - size * 0.7, cx + size * 1.2, cy + size * 0.3], fill=color)


def _draw_heart(draw, cx, cy, size, color):
    """Draw a simple heart."""
    draw.ellipse([cx - size, cy - size, cx, cy], fill=color)
    draw.ellipse([cx, cy - size, cx + size, cy], fill=color)
    draw.polygon([
        (cx - size, cy), (cx, cy + size * 1.2), (cx + size, cy)
    ], fill=color)


def _generate_fallback_image(output_path: str, index: int):
    """
    Generate a vibrant, cartoon-style fallback image with gradient background,
    decorative shapes, stars, clouds, and bouncing circles — kid-friendly.
    """
    rng = random.Random(index * 42)
    palette = PALETTES[index % len(PALETTES)]
    c1, c2 = palette

    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Background decorative large circles (semi-transparent feel via lighter shade)
    for _ in range(6):
        cx = rng.randint(0, WIDTH)
        cy = rng.randint(0, HEIGHT)
        cr = rng.randint(60, 160)
        shade = (
            min(255, c1[0] + 60),
            min(255, c1[1] + 60),
            min(255, c1[2] + 60),
        )
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=shade)

    # White fluffy clouds (upper area)
    for _ in range(3):
        cx = rng.randint(80, WIDTH - 80)
        cy = rng.randint(80, 300)
        _draw_cloud(draw, cx, cy, rng.randint(50, 90), (255, 255, 255))

    # Colorful stars scattered across image
    star_colors = [(255, 240, 60), (255, 200, 100), (255, 255, 180), (255, 160, 80)]
    for _ in range(12):
        sx = rng.randint(30, WIDTH - 30)
        sy = rng.randint(30, HEIGHT - 200)
        sr = rng.randint(18, 42)
        color = rng.choice(star_colors)
        _draw_star(draw, sx, sy, sr, color)

    # Bright colored circles (bubbles) for playful look
    bubble_colors = [
        (255, 100, 150), (100, 200, 255), (150, 255, 150),
        (255, 200, 80), (200, 100, 255),
    ]
    for _ in range(8):
        bx = rng.randint(30, WIDTH - 30)
        by = rng.randint(HEIGHT // 3, HEIGHT - 100)
        br = rng.randint(25, 65)
        bc = rng.choice(bubble_colors)
        draw.ellipse([bx - br, by - br, bx + br, by + br], fill=bc)
        # White shine dot
        draw.ellipse([bx - br // 4, by - br // 2,
                      bx + br // 4, by - br // 4], fill=(255, 255, 255))

    # Hearts along the sides
    heart_colors = [(255, 80, 120), (255, 150, 180), (255, 100, 100)]
    for _ in range(4):
        hx = rng.choice([rng.randint(20, 80), rng.randint(WIDTH - 80, WIDTH - 20)])
        hy = rng.randint(300, HEIGHT - 300)
        _draw_heart(draw, hx, hy, rng.randint(15, 30), rng.choice(heart_colors))

    # Rainbow arc in upper middle
    arc_colors = [
        (255, 60, 60), (255, 160, 40), (255, 240, 40),
        (80, 220, 80), (60, 140, 255), (160, 80, 255),
    ]
    arc_cx, arc_cy = WIDTH // 2, HEIGHT // 3
    for k, ac in enumerate(arc_colors):
        r_arc = 180 - k * 22
        draw.arc(
            [arc_cx - r_arc, arc_cy - r_arc // 2,
             arc_cx + r_arc, arc_cy + r_arc // 2],
            start=200, end=340, fill=ac, width=14,
        )

    img.save(output_path, "PNG")
