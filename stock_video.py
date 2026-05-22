"""
stock_video.py — Pexels Video API integration.

Searches the free Pexels Video API for a high-resolution (ideally 4K) stock
clip matching a soundscape theme. Pexels footage is licensed for commercial use
including monetization. If no usable clip is found (or no API key is set),
get_clip() returns None so the caller can fall back to an AI-generated still.

Public API:
    get_clip(query, output_path) -> path or None

Env var:
    PEXELS_API_KEY  (free key from https://www.pexels.com/api/)
"""

import os
import argparse
import requests

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
TARGET_W = 3840
TARGET_H = 2160
MIN_W = 1920          # reject clips smaller than Full HD
MIN_DURATION = 8      # seconds — need enough material to crossfade-loop
MAX_DURATION = 60
DOWNLOAD_TIMEOUT = 300


def _api_key():
    return os.environ.get("PEXELS_API_KEY", "").strip()


def _score_video_file(vf):
    """Rank a Pexels video file: prefer 4K-ish landscape MP4."""
    w = vf.get("width") or 0
    h = vf.get("height") or 0
    if w < MIN_W or h < w * 0.4:        # too small or not landscape-ish
        return -1
    if (vf.get("file_type") or "") != "video/mp4":
        return -1
    # closeness to 4K, capped so we don't over-prefer absurd resolutions
    return -abs(min(w, 7680) - TARGET_W)


def _pick_best_file(video):
    """Choose the best downloadable file from a Pexels video entry."""
    best, best_score = None, -1
    for vf in video.get("video_files", []):
        score = _score_video_file(vf)
        if score > best_score:
            best, best_score = vf, score
    return best


def get_clip(query, output_path):
    """Download the best matching Pexels clip. Returns path, or None to fall back."""
    key = _api_key()
    if not key:
        print("  PEXELS_API_KEY not set — skipping stock video (AI fallback).")
        return None

    headers = {"Authorization": key}
    params = {
        "query": query,
        "orientation": "landscape",
        "size": "large",          # large = highest-res results first
        "per_page": 15,
    }

    try:
        resp = requests.get(PEXELS_SEARCH_URL, headers=headers,
                            params=params, timeout=60)
        if resp.status_code != 200:
            print(f"  Pexels API returned {resp.status_code} — AI fallback.")
            return None
        videos = resp.json().get("videos", [])
    except Exception as e:
        print(f"  Pexels search failed: {e} — AI fallback.")
        return None

    if not videos:
        print(f"  No Pexels results for '{query}' — AI fallback.")
        return None

    # Prefer clips long enough to loop, then highest resolution.
    candidates = []
    for v in videos:
        dur = v.get("duration") or 0
        if dur < MIN_DURATION:
            continue
        vf = _pick_best_file(v)
        if vf is None:
            continue
        candidates.append((v, vf))

    if not candidates:
        print(f"  No usable Pexels clip for '{query}' — AI fallback.")
        return None

    # Sort by resolution (descending), pick the best.
    candidates.sort(key=lambda c: (c[1].get("width") or 0), reverse=True)
    video, vfile = candidates[0]
    link = vfile.get("link")
    res = f"{vfile.get('width')}x{vfile.get('height')}"
    print(f"  Pexels match: {res}, {video.get('duration')}s — downloading...")

    try:
        with requests.get(link, stream=True, timeout=DOWNLOAD_TIMEOUT) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
    except Exception as e:
        print(f"  Pexels download failed: {e} — AI fallback.")
        return None

    size = os.path.getsize(output_path)
    if size < 50000:
        print("  Downloaded clip too small — AI fallback.")
        return None

    print(f"  Stock clip saved: {output_path} ({size / 1e6:.1f} MB)")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pexels stock video fetch test")
    parser.add_argument("--query", default="rain window night")
    parser.add_argument("--out", default="stock_test.mp4")
    args = parser.parse_args()

    result = get_clip(args.query, args.out)
    if result:
        print(f"Success: {os.path.abspath(result)}")
    else:
        print("No clip — the pipeline would use the AI-image fallback here.")
