"""Cuts Cat Walk to the story on its bar lines: public/audio/music.wav, one film bar per track bar. The track is
130 bpm with its first beat at 0.232 s (tools/grid.py), so each cut lands on a kick with the groove intact."""
import os
import subprocess
import wave

import numpy as np

SRC = os.path.expanduser("~/.claude/skills/video-shotcraft/assets/audio/bgm/cat-walk.mp3")
SR = 48000
FIRST = 0.232
BAR = 60 / 130 * 4
# (first track bar, how many bars, gain): quiet hook, build, drop, breakdown at sleep, the kick back for Sessions,
# empty again as the colour drains, the climb, the peak
PLAN = [(4, 3, 1.5), (14, 2, 1.1), (16, 11, 1.0), (32, 3, 1.15), (26, 4, 1.0), (36, 3, 1.5), (46, 2, 1.1), (48, 6, 1.0)]
TOTAL_BARS = sum(p[1] for p in PLAN)

raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", SRC, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
out = np.zeros((int(TOTAL_BARS * BAR * SR) + SR, 2))
fade = int(0.012 * SR)  # a short crossfade hides each join
film_bar = 0
for first, bars, gain in PLAN:
    a = int((FIRST + first * BAR) * SR)
    n = int(bars * BAR * SR)
    piece = x[a: a + n + fade].copy() * gain
    env = np.ones(len(piece))
    env[:fade] = np.linspace(0, 1, fade)
    env[-fade:] = np.linspace(1, 0, fade)
    start = int(film_bar * BAR * SR)
    out[start: start + len(piece)] += piece * env[:, None]
    film_bar += bars
# The last bar and a bit fade away with the picture
end = int(TOTAL_BARS * BAR * SR)
tail = int(1.2 * BAR * SR)
out[end - tail: end] *= np.linspace(1, 0, tail)[:, None] ** 1.5
out = out[:end]
peak = np.abs(out).max()
print(f"{len(out) / SR:.2f} s, peak {peak:.2f}, {TOTAL_BARS} bars")
out = np.clip(out / max(1.0, peak) * 0.98, -1, 1)
os.makedirs("public/audio", exist_ok=True)
with wave.open("public/audio/music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((out * 32767).astype(np.int16).tobytes())
