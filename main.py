#!/usr/bin/env python3
"""
Sleep Soundscape YouTube Bot
Generates and uploads a long-form 4K relaxing soundscape video.

Usage:
  python3 main.py --slot night                      # generate + upload (3 hours)
  python3 main.py --slot night --duration 1         # 1-hour video
  python3 main.py --slot night --dry-run            # generate only, no upload
  python3 main.py --slot night --duration 1 --private  # upload as private (test)
"""

import argparse
import os
import shutil
from pathlib import Path

SLOTS = ["night", "evening", "afternoon"]
DURATIONS = [1, 3, 8]


def _load_dotenv():
    """Load KEY=VALUE pairs from a local .env into os.environ (if present)."""
    env_file = Path(".env")
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main():
    parser = argparse.ArgumentParser(description="Sleep Soundscape Bot")
    parser.add_argument("--slot", default="night", choices=SLOTS,
                        help="Publish slot (determines scheduled publish time)")
    parser.add_argument("--duration", type=int, default=3, choices=DURATIONS,
                        help="Video length in hours")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate video only, skip YouTube upload")
    parser.add_argument("--private", action="store_true",
                        help="Upload as private (for testing)")
    args = parser.parse_args()

    _load_dotenv()

    total_seconds = args.duration * 3600

    work_base = Path(os.environ.get("BOT_WORK_DIR", "temp"))
    temp_dir = work_base / args.slot
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(temp_dir / "output.mp4")
    audio_path = str(temp_dir / "soundscape.wav")
    clip_path = str(temp_dir / "stock_clip.mp4")
    image_path = str(temp_dir / "scene.png")

    try:
        # 1. Select soundscape theme
        from script_generator import get_next_theme, mark_uploaded
        theme = get_next_theme(args.slot)
        print(f"\n[{args.slot.upper()}] Theme: {theme['name']} "
              f"({args.duration}h)")

        # 2. Get visuals — Pexels stock clip, fall back to AI still
        print("\nStep 1/4: Sourcing visuals...")
        from stock_video import get_clip
        visual_path = get_clip(theme["video_query"], clip_path)
        is_video = visual_path is not None
        if not is_video:
            from image_generator import generate_scene
            visual_path = generate_scene(theme["visual_prompt"], image_path)

        # 3. Synthesize procedural soundscape audio
        print("\nStep 2/4: Synthesizing soundscape audio...")
        from soundscape_audio import generate_soundscape
        generate_soundscape(theme["audio_recipe"], audio_path)

        # 4. Build the looped video
        print("\nStep 3/4: Building video...")
        from video_generator import build_video
        build_video(visual_path, is_video, audio_path,
                    str(temp_dir), output_path, total_seconds)

        # 5. SEO metadata
        from seo_generator import generate_seo
        seo = generate_seo(theme, args.duration)
        print(f"\n--- SEO Preview ---")
        print(f"Title: {seo['title']}")
        print(f"Tags ({len(seo['tags'])}): {', '.join(seo['tags'][:5])}...")

        if args.dry_run:
            final_path = f"output_{args.slot}.mp4"
            shutil.copy(output_path, final_path)
            print(f"\nDry run complete. Video saved to: {final_path}")
            return

        # 6. Upload
        print("\nStep 4/4: Uploading to YouTube...")
        from youtube_uploader import authenticate, upload_video
        youtube = authenticate()
        privacy = "private" if args.private else "public"
        video_id = upload_video(youtube, output_path, seo, privacy, args.slot)

        # 7. Mark theme as uploaded
        mark_uploaded(theme["id"])
        print(f"\nDone! https://youtube.com/watch?v={video_id}")

    except Exception as e:
        print(f"\nError: {e}")
        raise

    finally:
        if temp_dir.exists() and not args.dry_run:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
