import asyncio
import os
import random
from pathlib import Path
from pydub import AudioSegment
from pydub.effects import speedup

TARGET_DURATION_MS = 28500  # 28.5s content (0.5s intro + 1.0s outro = 30s)
MUSIC_DIR = Path("data/music")

# Edge TTS neural voices — genuine child voices first, warm females as fallback
VOICE_OPTIONS = [
    "en-GB-MaisieNeural",    # British child voice — sweet, sing-song, perfect for rhymes
    "en-US-AnaNeural",       # American child voice
    "en-US-JennyNeural",     # warm, friendly American female
    "en-IE-EmilyNeural",     # soft Irish — great melodic quality
]
PRIMARY_VOICE = VOICE_OPTIONS[0]

# Slower + higher pitched = classic nursery rhyme storytelling feel
PROSODY_RATE = "-20%"    # noticeably slower — kids follow along easily
PROSODY_PITCH = "+18Hz"  # higher pitch = brighter, more child-like tone


async def _tts_line(text: str, output_path: str, voice: str = PRIMARY_VOICE):
    """Generate Edge TTS audio for a single line."""
    import edge_tts
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=PROSODY_RATE,
        pitch=PROSODY_PITCH,
    )
    await communicate.save(output_path)


def text_to_speech(text: str, output_path: str, voice: str = PRIMARY_VOICE):
    """Sync wrapper for Edge TTS. Saves audio to output_path."""
    asyncio.run(_tts_line(text, output_path, voice))


def generate_voice_track(lines: list, temp_dir: str):
    """
    Generate TTS for each lyric line, combine with short pauses.
    Returns (combined_path, [(start_ms, end_ms), ...])
    """
    segments = []
    combined = AudioSegment.empty()
    pause = AudioSegment.silent(duration=350)  # slightly longer pause = more musical breathing room

    for i, line in enumerate(lines):
        line_path = os.path.join(temp_dir, f"line_{i}.mp3")
        text_to_speech(line["text"], line_path)
        seg = AudioSegment.from_file(line_path)

        # Slight volume boost on each line for clarity
        seg = seg + 2

        start_ms = len(combined)
        combined += seg + pause
        end_ms = len(combined)
        segments.append((start_ms, end_ms))

    voice_path = os.path.join(temp_dir, "voice_raw.mp3")
    combined.export(voice_path, format="mp3")
    return voice_path, segments


def adjust_voice_to_target(voice_path: str, temp_dir: str):
    """Adjust voice duration to TARGET_DURATION_MS. Returns (path, speed_ratio)."""
    voice = AudioSegment.from_file(voice_path)
    duration_ms = len(voice)

    if duration_ms == 0:
        raise ValueError("Voice audio is empty")

    speed_ratio = duration_ms / TARGET_DURATION_MS

    if 0.85 <= speed_ratio <= 1.15:
        adjusted = _pad_or_trim(voice, TARGET_DURATION_MS)
        speed_ratio = 1.0
    elif speed_ratio > 1.15:
        speed_ratio = min(speed_ratio, 1.6)
        adjusted = speedup(voice, playback_speed=speed_ratio)
        adjusted = _pad_or_trim(adjusted, TARGET_DURATION_MS)
    else:
        # Too short — repeat last line or just pad
        adjusted = _pad_or_trim(voice, TARGET_DURATION_MS)
        speed_ratio = 1.0

    out_path = os.path.join(temp_dir, "voice_adjusted.wav")
    adjusted.export(out_path, format="wav")
    return out_path, speed_ratio


def _pad_or_trim(audio: AudioSegment, target_ms: int) -> AudioSegment:
    if len(audio) < target_ms:
        return audio + AudioSegment.silent(duration=target_ms - len(audio))
    return audio[:target_ms]


def pick_background_music():
    """Pick a random BGM track from data/music/."""
    if not MUSIC_DIR.exists():
        return None
    music_files = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
    return str(random.choice(music_files)) if music_files else None


def _generate_chime(duration_ms: int = 500) -> AudioSegment:
    """
    Generate a simple cheerful chime using pure tone synthesis.
    Plays a bright C5 note (523 Hz) with quick decay — like a xylophone hit.
    """
    import struct, wave, math, io
    sample_rate = 44100
    n_samples = int(sample_rate * duration_ms / 1000)
    freq = 523.25  # C5 — bright, cheerful
    freq2 = 659.25  # E5 — harmony note

    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        decay = math.exp(-6 * t)  # fast decay = xylophone feel
        val = decay * (
            0.6 * math.sin(2 * math.pi * freq * t) +
            0.4 * math.sin(2 * math.pi * freq2 * t)
        )
        samples.append(int(val * 28000))

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f'<{n_samples}h', *samples))
    buf.seek(0)
    chime = AudioSegment.from_wav(buf).set_channels(2)
    return chime


def mix_audio(voice_path: str, music_path, output_path: str, total_duration_ms: int = 30000):
    """
    Mix voice + background music + intro chime into a single 30s track.
    - Cheerful xylophone chime at the very start
    - Music at -8dB (prominent but not overpowering)
    - Music ducks slightly when voice plays for clarity
    """
    voice = AudioSegment.from_file(voice_path)
    voice = _pad_or_trim(voice, 28500)

    # 500ms chime at start instead of silence
    chime = _generate_chime(500)
    voice_with_offset = chime.overlay(AudioSegment.silent(duration=500)) + voice
    voice_with_offset = _pad_or_trim(voice_with_offset, total_duration_ms)

    if music_path:
        music = AudioSegment.from_file(music_path)
        while len(music) < total_duration_ms:
            music = music + music
        music = music[:total_duration_ms]

        # More prominent music: -8dB under voice for a real kids-show feel
        music = music - 8
        music = music.fade_in(400).fade_out(1200)

        final = voice_with_offset.overlay(music)
    else:
        final = voice_with_offset

    final = _pad_or_trim(final, total_duration_ms)
    final.export(output_path, format="wav")
    return output_path


def generate_audio(rhyme: dict, output_path: str, temp_dir: str) -> list:
    """Full pipeline: Edge TTS → adjust → mix with music → 30s WAV."""
    print("  Generating voice track (Edge TTS neural voice)...")
    voice_raw, segments = generate_voice_track(rhyme["lines"], temp_dir)

    print("  Adjusting timing to 28.5s...")
    voice_adjusted, speed_ratio = adjust_voice_to_target(voice_raw, temp_dir)

    if speed_ratio != 1.0:
        segments = [
            (int(s / speed_ratio), int(e / speed_ratio))
            for s, e in segments
        ]

    # Offset all segments by 500ms (intro)
    segments = [(s + 500, e + 500) for s, e in segments]

    print("  Mixing with background music...")
    music_path = pick_background_music()
    if not music_path:
        print("  No music found in data/music/ — voice only.")
    mix_audio(voice_adjusted, music_path, output_path)

    print(f"  Audio generated: {output_path}")
    return segments
