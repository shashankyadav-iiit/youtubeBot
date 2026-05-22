"""
image_generator.py — AI scene image for the AI-image fallback path.

When Pexels has no usable stock clip for a theme, the pipeline falls back to a
single dark, cinematic 4K landscape still that video_generator animates with a
slow seamless drift. Images come from Pollinations.ai (free, no key); if that
fails, a calm procedurally-drawn night scene is used.

Public API:
    generate_scene(prompt, output_path) -> output_path   (always produces a file)
"""

import os
import time
import random
import requests
import numpy as np
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"
WIDTH = 3840          # 4K landscape
HEIGHT = 2160
WIDTH_HD = 1920       # Full HD fallback
HEIGHT_HD = 1080
MODEL = "flux"

# Dark night-sky gradient palettes for the procedural fallback.
NIGHT_PALETTES = [
    [(8, 12, 32), (28, 36, 72)],     # deep navy
    [(14, 10, 30), (44, 28, 66)],    # navy → purple
    [(6, 16, 26), (20, 44, 58)],     # midnight teal
    [(20, 12, 28), (56, 30, 44)],    # dark plum
]


def _enhance_image(img):
    """Gentle sharpening + mild contrast for a crisp but calm, dark image."""
    img = img.filter(ImageFilter.UnsharpMask(radius=1.4, percent=110, threshold=2))
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Color(img).enhance(1.05)
    img = ImageEnhance.Brightness(img).enhance(0.92)   # keep it sleep-dark
    return img


def _try_download(prompt, output_path, w, h, timeout):
    """Attempt a single Pollinations.ai download at the given resolution."""
    full_prompt = (f"{prompt}, cinematic, soft moody lighting, dark calm "
                   f"atmosphere, highly detailed, no text, no people, 4K")
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


def generate_scene_image(prompt, output_path, retries=2):
    """Download a dark 4K landscape scene image, HD fallback. Returns bool."""
    resolutions = [(WIDTH, HEIGHT, 150), (WIDTH_HD, HEIGHT_HD, 90)]

    for attempt in range(retries):
        for w, h, timeout in resolutions:
            print(f"    Trying {w}×{h}...")
            if _try_download(prompt, output_path, w, h, timeout):
                try:
                    img = Image.open(output_path).convert("RGB")
                    img = _enhance_image(img)
                    if img.size != (WIDTH, HEIGHT):
                        img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
                    img.save(output_path, "PNG", quality=100)
                except Exception:
                    pass
                return True
        if attempt < retries - 1:
            time.sleep(4)
    return False


def _add(base, overlay):
    """Additive blend of two RGB images (clamped to 0-255)."""
    a = np.asarray(base).astype(np.int16)
    b = np.asarray(overlay).astype(np.int16)
    return Image.fromarray(np.clip(a + b, 0, 255).astype("uint8"), "RGB")


def _generate_fallback_image(output_path, seed=None):
    """Draw a calm dark night-sky scene as a last-resort fallback."""
    rng = random.Random(seed if seed is not None else random.randint(0, 9999))
    c1, c2 = rng.choice(NIGHT_PALETTES)

    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # Vertical gradient: darker at the bottom, slightly lit sky at the top.
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(c2[0] * (1 - ratio) + c1[0] * ratio)
        g = int(c2[1] * (1 - ratio) + c1[1] * ratio)
        b = int(c2[2] * (1 - ratio) + c1[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Soft moon glow.
    mx = rng.randint(int(WIDTH * 0.6), int(WIDTH * 0.85))
    my = rng.randint(int(HEIGHT * 0.15), int(HEIGHT * 0.35))
    glow = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for rad in range(420, 0, -20):
        a = int(60 * (1 - rad / 420))
        gdraw.ellipse([mx - rad, my - rad, mx + rad, my + rad],
                      fill=(a, a, int(a * 1.1)))
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img = _add(img, glow)
    draw = ImageDraw.Draw(img)

    # Stars scattered in the upper two-thirds.
    for _ in range(220):
        sx = rng.randint(0, WIDTH)
        sy = rng.randint(0, int(HEIGHT * 0.7))
        sr = rng.choice([1, 1, 1, 2, 2, 3])
        bright = rng.randint(140, 235)
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr],
                     fill=(bright, bright, min(255, bright + 15)))

    img.save(output_path, "PNG")


def generate_scene(prompt, output_path):
    """Produce one dark 4K landscape scene image. Always yields a file."""
    print("  Generating AI scene image (fallback path)...")
    if not generate_scene_image(prompt, output_path):
        print("  Pollinations unavailable — using procedural night scene.")
        _generate_fallback_image(output_path)
    return output_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dark scene image test")
    parser.add_argument("--prompt",
                        default="calm dark ocean at night under moonlight")
    parser.add_argument("--out", default="scene_test.png")
    args = parser.parse_args()
    generate_scene(args.prompt, args.out)
    print(f"Saved: {os.path.abspath(args.out)}")
