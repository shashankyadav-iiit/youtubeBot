"""
video_generator.py — Loop-render video assembly (pure ffmpeg).

The loop-render trick: build ONE short seamless 4K loop, then stream-loop it to
the full duration with `-c:v copy` (no re-encode). Keeps a 3-hour 4K render fast.

- Stock clip  → xfade the clip into itself → seamless base loop.
- AI image    → zoompan sine-drift Ken Burns → seamless base loop.
- Assembly    → stream-loop video + audio, mux, cut to total duration.

Public API:
    build_video(visual_path, is_video, audio_loop_path,
                temp_dir, output_path, total_seconds) -> output_path
"""

import os
import json
import subprocess

TARGET_W = 3840
TARGET_H = 2160
FPS = 30
VIDEO_BITRATE = "8M"          # ~8 Mbps 4K → ~11 GB for 3 hours
XFADE_SECONDS = 1.5           # crossfade length for stock-clip loops
IMAGE_LOOP_SECONDS = 24       # base-loop length for the AI-image path

_SCALE_COVER = (f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
                f"crop={TARGET_W}:{TARGET_H},setsar=1")


def _run(cmd):
    """Run a command, raising with stderr tail on failure."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-12:])
        raise RuntimeError(f"Command failed ({cmd[0]}):\n{tail}")
    return proc


def _probe_duration(path):
    """Return media duration in seconds via ffprobe."""
    proc = _run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", path,
    ])
    return float(json.loads(proc.stdout)["format"]["duration"])


def _build_loop_from_clip(clip_path, temp_dir):
    """Crossfade a stock clip into itself → a seamless 4K base loop.

    xfade plays copy A then crossfades into copy B; the segment from t=XFADE to
    t=D is a seamless D-XFADE loop (both ends land on the same source frame X).
    """
    duration = _probe_duration(clip_path)
    xfade = min(XFADE_SECONDS, max(0.5, duration * 0.2))
    offset = duration - xfade
    base_path = os.path.join(temp_dir, "base_loop.mp4")

    filtergraph = (
        f"[0:v]{_SCALE_COVER},fps={FPS}[v0];"
        f"[1:v]{_SCALE_COVER},fps={FPS}[v1];"
        f"[v0][v1]xfade=transition=fade:duration={xfade:.3f}:offset={offset:.3f},"
        f"trim=start={xfade:.3f}:end={duration:.3f},setpts=PTS-STARTPTS[out]"
    )
    print(f"  Crossfade-looping stock clip ({duration:.1f}s → "
          f"{duration - xfade:.1f}s seamless loop)...")
    _run([
        "ffmpeg", "-y", "-i", clip_path, "-i", clip_path,
        "-filter_complex", filtergraph, "-map", "[out]",
        "-c:v", "libx264", "-b:v", VIDEO_BITRATE, "-maxrate", VIDEO_BITRATE,
        "-bufsize", "16M", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-g", str(FPS * 2), "-an", base_path,
    ])
    return base_path


def _build_loop_from_image(image_path, temp_dir):
    """Zoompan sine-drift Ken Burns on a still → a seamless 4K base loop.

    z oscillates as a pure sine of the frame index, so the first and last
    frames are identical → the loop wraps with no jump.
    """
    total_frames = IMAGE_LOOP_SECONDS * FPS
    base_path = os.path.join(temp_dir, "base_loop.mp4")
    z_expr = f"1.04+0.04*sin(2*PI*on/{total_frames})"

    filtergraph = (
        f"scale={TARGET_W}:{TARGET_H},"
        f"zoompan=z='{z_expr}':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d=1:s={TARGET_W}x{TARGET_H}:fps={FPS}"
    )
    print(f"  Rendering {IMAGE_LOOP_SECONDS}s sine-drift loop from still image...")
    _run([
        "ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS),
        "-t", str(IMAGE_LOOP_SECONDS), "-i", image_path,
        "-vf", filtergraph,
        "-c:v", "libx264", "-b:v", VIDEO_BITRATE, "-maxrate", VIDEO_BITRATE,
        "-bufsize", "16M", "-preset", "medium", "-pix_fmt", "yuv420p",
        "-g", str(FPS * 2), "-an", base_path,
    ])
    return base_path


def _assemble(base_loop_path, audio_loop_path, output_path, total_seconds):
    """Stream-loop the base video + audio to full length and mux."""
    print(f"  Assembling {total_seconds / 3600:.1f}-hour video "
          f"(stream-loop, no re-encode)...")
    _run([
        "ffmpeg", "-y",
        "-fflags", "+genpts",
        "-stream_loop", "-1", "-i", base_loop_path,
        "-stream_loop", "-1", "-i", audio_loop_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(int(total_seconds)),
        "-movflags", "+faststart",
        output_path,
    ])
    return output_path


def build_video(visual_path, is_video, audio_loop_path,
                temp_dir, output_path, total_seconds):
    """Build the full looped sleep video.

    visual_path  — a stock MP4 (is_video=True) or a 4K still image (False)
    audio_loop_path — seamless WAV loop from soundscape_audio
    total_seconds   — final video length (e.g. 10800 for 3 hours)
    """
    if is_video:
        base_loop = _build_loop_from_clip(visual_path, temp_dir)
    else:
        base_loop = _build_loop_from_image(visual_path, temp_dir)

    _assemble(base_loop, audio_loop_path, output_path, total_seconds)

    size_gb = os.path.getsize(output_path) / 1e9
    print(f"  Video complete: {output_path} ({size_gb:.2f} GB)")
    return output_path
