"""
soundscape_audio.py — Procedural ambient sound synthesis.

Every render generates unique audio from noise + filters + modulation, so the
output is 100% original (no "reused content" copyright risk) and free forever.

Public API:
    generate_soundscape(recipe, output_path, loop_seconds=300) -> output_path

The output is a seamless WAV loop; video_generator stream-loops it to full length.
"""

import os
import argparse
import numpy as np
from scipy import signal
from scipy.io import wavfile

SAMPLE_RATE = 44100
DEFAULT_LOOP_SECONDS = 300      # 5-minute seamless loop
CROSSFADE_SECONDS = 4.0         # wrap-point crossfade for seamless looping

RECIPES = [
    "rain", "thunderstorm", "ocean", "fireplace", "forest",
    "stream", "wind", "white_noise", "pink_noise", "brown_noise",
]


# ----------------------------------------------------------------------------
# Noise generators (mono float32, peak-normalized)
# ----------------------------------------------------------------------------
def _normalize(x):
    peak = np.max(np.abs(x))
    if peak < 1e-9:
        return x.astype(np.float32)
    return (x / peak).astype(np.float32)


def white_noise(n):
    return np.random.uniform(-1.0, 1.0, n).astype(np.float32)


def pink_noise(n):
    """1/f noise via FFT spectral shaping."""
    white = np.random.randn(n).astype(np.float32)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n)
    freqs[0] = freqs[1] if len(freqs) > 1 else 1.0
    spec = spec / np.sqrt(freqs)
    pink = np.fft.irfft(spec, n=n)
    return _normalize(pink)


def brown_noise(n):
    """Brownian (1/f^2) noise — deep rumble. Highpassed to remove DC wander."""
    white = np.random.randn(n).astype(np.float32)
    brown = np.cumsum(white)
    brown = brown - np.mean(brown)
    brown = _butter(brown, SAMPLE_RATE, 18.0, "high", order=2)
    return _normalize(brown)


# ----------------------------------------------------------------------------
# Filters & modulation
# ----------------------------------------------------------------------------
def _butter(x, sr, cutoff, btype, order=4):
    sos = signal.butter(order, cutoff, btype=btype, fs=sr, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def bandpass(x, sr, lo, hi, order=4):
    return _butter(x, sr, [lo, hi], "band", order=order)


def smooth_random_env(n, sr, rate_hz, lo=0.3, hi=1.0):
    """Fast random amplitude envelope (control points interpolated)."""
    n_ctrl = max(2, int(n / sr * rate_hz))
    ctrl = np.random.uniform(lo, hi, n_ctrl).astype(np.float32)
    env = np.interp(np.linspace(0, n_ctrl - 1, n),
                    np.arange(n_ctrl), ctrl)
    return env.astype(np.float32)


def lfo(n, sr, freq, depth=0.5, base=0.5):
    """Slow sine low-frequency oscillator envelope."""
    t = np.arange(n, dtype=np.float32) / sr
    return (base + depth * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def sprinkle(n, sr, events_per_sec, make_event):
    """Place sparse short transient events into an n-length buffer."""
    out = np.zeros(n, dtype=np.float32)
    count = max(0, int(n / sr * events_per_sec))
    for _ in range(count):
        ev = make_event(sr)
        pos = np.random.randint(0, n)
        end = min(n, pos + len(ev))
        out[pos:end] += ev[: end - pos]
    return out


# ----------------------------------------------------------------------------
# Transient event makers
# ----------------------------------------------------------------------------
def _droplet(sr):
    dur = np.random.uniform(0.010, 0.045)
    m = max(2, int(dur * sr))
    burst = np.random.randn(m).astype(np.float32)
    burst *= np.exp(-np.linspace(0, 6, m))
    return burst * np.random.uniform(0.3, 1.0)


def _crackle(sr):
    dur = np.random.uniform(0.002, 0.018)
    m = max(2, int(dur * sr))
    burst = np.random.randn(m).astype(np.float32)
    burst *= np.exp(-np.linspace(0, 9, m))
    return burst * np.random.uniform(0.25, 1.0)


def _thunder(n, sr):
    """Sparse low rumble swells."""
    out = np.zeros(n, dtype=np.float32)
    count = max(1, int(n / sr / 26))   # ~one every 26s
    for _ in range(count):
        dur = np.random.uniform(3.0, 7.0)
        m = min(n, int(dur * sr))
        rumble = brown_noise(m)
        attack = int(m * 0.18)
        env = np.concatenate([
            np.linspace(0, 1, attack),
            np.exp(-np.linspace(0, 4, m - attack)),
        ]).astype(np.float32)
        rumble *= env[:m]
        pos = np.random.randint(0, max(1, n - m))
        out[pos:pos + m] += rumble * np.random.uniform(0.6, 1.0)
    return _butter(out, sr, 190.0, "low")


def _crickets(n, sr):
    """Several crickets chirping in rhythmic pulse trains."""
    out = np.zeros(n, dtype=np.float32)
    t = np.arange(n, dtype=np.float32) / sr
    for _ in range(np.random.randint(3, 6)):
        freq = np.random.uniform(3800, 5200)
        tone = np.sin(2 * np.pi * freq * t).astype(np.float32)
        pulse_rate = np.random.uniform(2.0, 4.0)
        gate = (np.sin(2 * np.pi * pulse_rate * t) > 0.30).astype(np.float32)
        gate = _butter(gate, sr, 70.0, "low")
        out += tone * gate * np.random.uniform(0.10, 0.22)
    return out


# ----------------------------------------------------------------------------
# Recipe builders — each returns a mono float32 mix (one channel)
# ----------------------------------------------------------------------------
def _mix(*layers):
    n = max(len(layer) for layer, _ in layers)
    out = np.zeros(n, dtype=np.float32)
    for layer, gain in layers:
        out[: len(layer)] += layer * gain
    return out


def _build_rain(n, sr):
    rumble = _butter(brown_noise(n), sr, 520.0, "low")
    hiss = bandpass(white_noise(n), sr, 900.0, 9000.0)
    hiss *= smooth_random_env(n, sr, rate_hz=14.0, lo=0.45, hi=1.0)
    drops = sprinkle(n, sr, events_per_sec=22, make_event=_droplet)
    drops = bandpass(drops, sr, 1200.0, 6000.0)
    return _mix((rumble, 0.55), (hiss, 0.42), (drops, 0.35))


def _build_thunderstorm(n, sr):
    rain = _build_rain(n, sr)
    thunder = _thunder(n, sr)
    return _mix((rain, 0.85), (thunder, 0.9))


def _build_ocean(n, sr):
    base = _butter(brown_noise(n), sr, 700.0, "low")
    swell = lfo(n, sr, freq=0.10, depth=0.45, base=0.55)
    crash = bandpass(white_noise(n), sr, 800.0, 6000.0)
    crash_env = np.clip(swell - 0.55, 0.0, 1.0) * 2.2
    return _mix((base * swell, 0.6), (crash * crash_env, 0.4))


def _build_fireplace(n, sr):
    room = _butter(brown_noise(n), sr, 420.0, "low")
    crackle = sprinkle(n, sr, events_per_sec=40, make_event=_crackle)
    crackle = bandpass(crackle, sr, 700.0, 7500.0)
    pops = sprinkle(n, sr, events_per_sec=2, make_event=_droplet)
    pops = bandpass(pops, sr, 200.0, 1800.0)
    return _mix((room, 0.30), (crackle, 0.55), (pops, 0.30))


def _build_forest(n, sr):
    air = _butter(pink_noise(n), sr, 2200.0, "low")
    crickets = _crickets(n, sr)
    breeze = _butter(brown_noise(n), sr, 350.0, "low")
    breeze *= smooth_random_env(n, sr, rate_hz=0.25, lo=0.2, hi=0.7)
    return _mix((air, 0.18), (crickets, 0.6), (breeze, 0.25))


def _build_stream(n, sr):
    flow = _butter(brown_noise(n), sr, 450.0, "low")
    bubble = bandpass(white_noise(n), sr, 500.0, 4500.0)
    bubble *= smooth_random_env(n, sr, rate_hz=20.0, lo=0.4, hi=1.0)
    trickle = sprinkle(n, sr, events_per_sec=30, make_event=_droplet)
    trickle = bandpass(trickle, sr, 1500.0, 5500.0)
    return _mix((flow, 0.4), (bubble, 0.5), (trickle, 0.22))


def _build_wind(n, sr):
    body = _butter(brown_noise(n), sr, 600.0, "low")
    gust = smooth_random_env(n, sr, rate_hz=0.18, lo=0.15, hi=1.0)
    howl = bandpass(pink_noise(n), sr, 300.0, 1400.0)
    howl *= smooth_random_env(n, sr, rate_hz=0.10, lo=0.0, hi=0.6)
    return _mix((body * gust, 0.6), (howl, 0.3))


def _build_white_noise(n, sr):
    return _butter(white_noise(n), sr, 13000.0, "low")


def _build_pink_noise(n, sr):
    return pink_noise(n)


def _build_brown_noise(n, sr):
    return brown_noise(n)


_BUILDERS = {
    "rain": _build_rain,
    "thunderstorm": _build_thunderstorm,
    "ocean": _build_ocean,
    "fireplace": _build_fireplace,
    "forest": _build_forest,
    "stream": _build_stream,
    "wind": _build_wind,
    "white_noise": _build_white_noise,
    "pink_noise": _build_pink_noise,
    "brown_noise": _build_brown_noise,
}


# ----------------------------------------------------------------------------
# Mastering & seamless looping
# ----------------------------------------------------------------------------
def _master(stereo):
    """RMS-normalize, soft-limit, peak to -1 dBFS — gentle, consistent level."""
    rms = np.sqrt(np.mean(stereo ** 2))
    if rms > 1e-9:
        stereo = stereo * (0.18 / rms)          # target a calm RMS level
    stereo = np.tanh(stereo * 0.9)              # soft saturation / limiter
    peak = np.max(np.abs(stereo))
    if peak > 1e-9:
        stereo = stereo * (0.891 / peak)        # -1 dBFS ceiling
    return stereo.astype(np.float32)


def _make_seamless(stereo, sr, crossfade_s):
    """Crossfade the tail into the head so the loop wraps with no click.

    `stereo` is longer than the target by `crossfade_s`; returns the target.
    """
    n_cf = int(crossfade_s * sr)
    target_len = len(stereo) - n_cf
    body = stereo[:target_len].copy()
    tail = stereo[target_len:target_len + n_cf]
    head = body[:n_cf].copy()
    t = np.linspace(0.0, 1.0, n_cf, dtype=np.float32)
    fade_out = np.cos(t * np.pi / 2)[:, None]
    fade_in = np.sin(t * np.pi / 2)[:, None]
    body[:n_cf] = tail * fade_out + head * fade_in
    return body


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------
def generate_soundscape(recipe, output_path, loop_seconds=DEFAULT_LOOP_SECONDS):
    """Synthesize a seamless ambient WAV loop for the given recipe."""
    if recipe not in _BUILDERS:
        print(f"  Unknown recipe '{recipe}', falling back to 'rain'.")
        recipe = "rain"

    sr = SAMPLE_RATE
    n = int((loop_seconds + CROSSFADE_SECONDS) * sr)
    builder = _BUILDERS[recipe]

    print(f"  Synthesizing '{recipe}' ({loop_seconds}s seamless loop)...")
    # Independent L/R passes for a wide, natural stereo image.
    left = builder(n, sr)
    right = builder(n, sr)
    stereo = np.stack([left, right], axis=1)

    stereo = _master(stereo)
    stereo = _make_seamless(stereo, sr, CROSSFADE_SECONDS)

    pcm = np.clip(stereo, -1.0, 1.0)
    pcm16 = (pcm * 32767.0).astype(np.int16)
    wavfile.write(output_path, sr, pcm16)
    print(f"  Audio loop written: {output_path} ({len(pcm16) / sr:.1f}s)")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Procedural soundscape synthesis")
    parser.add_argument("--theme", "--recipe", dest="recipe", default="rain",
                        choices=RECIPES, help="Soundscape recipe to synthesize")
    parser.add_argument("--preview", action="store_true",
                        help="Generate a short 60s preview")
    parser.add_argument("--out", default=None, help="Output WAV path")
    args = parser.parse_args()

    seconds = 60 if args.preview else DEFAULT_LOOP_SECONDS
    out = args.out or f"preview_{args.recipe}.wav"
    generate_soundscape(args.recipe, out, loop_seconds=seconds)
    print(f"Done. Play it: {os.path.abspath(out)}")
