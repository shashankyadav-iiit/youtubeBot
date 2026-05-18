#!/usr/bin/env python3
"""
Nursery Rhyme YouTube Shorts Bot
Generates and uploads a 30-second animated nursery rhyme video.

Usage:
  python main.py --slot morning             # generate and upload publicly
  python main.py --slot evening --dry-run   # generate only, no upload
  python main.py --slot afternoon --private # upload as private (for testing)
"""

import argparse
import os
import shutil
import tempfile
from pathlib import Path

SLOTS = ["dawn", "morning", "afternoon", "afterschool", "evening"]


def main():
    parser = argparse.ArgumentParser(description="Nursery Rhyme Shorts Bot")
    parser.add_argument("--slot", required=True, choices=SLOTS,
                        help="Upload slot (determines which rhyme and publish time)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate video only, skip YouTube upload")
    parser.add_argument("--private", action="store_true",
                        help="Upload as private (for testing)")
    args = parser.parse_args()

    temp_dir = Path("temp") / args.slot
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(temp_dir / "output.mp4")
    audio_path = str(temp_dir / "final_audio.wav")

    try:
        # 1. Select rhyme
        from script_generator import get_next_rhyme, mark_uploaded
        rhyme = get_next_rhyme(args.slot)
        print(f"\n[{args.slot.upper()}] Selected: {rhyme['title']}")

        # 2. Generate scene images (in parallel calls)
        print("\nStep 1/4: Generating scene images...")
        from image_generator import generate_all_scenes
        generate_all_scenes(rhyme["lines"], str(temp_dir))

        # 3. Generate audio — returns per-line segment timings
        print("\nStep 2/4: Generating audio...")
        from audio_generator import generate_audio
        segments = generate_audio(rhyme, audio_path, str(temp_dir))

        # 4. Build video — pass segment timings so video syncs to audio
        print("\nStep 3/4: Building video...")
        from video_generator import build_video
        build_video(rhyme, audio_path, str(temp_dir), output_path, segments)

        # 5. Generate SEO metadata
        from seo_generator import generate_seo
        seo = generate_seo(rhyme, args.slot)

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

        # 7. Mark as uploaded
        mark_uploaded(rhyme["id"])
        print(f"\nDone! https://youtube.com/watch?v={video_id}")

    except Exception as e:
        print(f"\nError: {e}")
        raise

    finally:
        # Clean up temp files
        if temp_dir.exists() and not args.dry_run:
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    main()
