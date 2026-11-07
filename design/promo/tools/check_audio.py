"""Checks the rendered sound. Levels and clipping on the full mix; where each pinned sound actually lands, against
the frame it's pinned to, on the version without music, where each hit stands alone."""
import subprocess
import sys

import numpy as np

SR = 48000
BAR = 60 / 130 * 4


def load(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


mix, fx = load(sys.argv[1]), load(sys.argv[2])
print(f"full mix {len(mix) / SR:.2f} s, peak {np.abs(mix).max():.3f}, samples at or over 0.99: {(np.abs(mix) >= 0.99).sum()}")
print("level by bar: " + " ".join(str(int(np.sqrt(np.mean(mix[int(i * BAR * SR): int((i + 1) * BAR * SR)] ** 2)) * 100)) for i in range(34)))
print(f"without music: peak {np.abs(fx).max():.3f}")


def landed(bar):
    """Frames from the pinned moment to where the sound's strongest rise falls."""
    t = bar * BAR
    a, b = int((t - 0.2) * SR), int((t + 0.25) * SR)
    hop = 96
    env = np.sqrt(np.array([np.mean(fx[i:i + hop] ** 2) for i in range(a, b, hop)]))
    rise = np.diff(env, prepend=env[0])
    i = int(np.argmax(rise))
    return (a + i * hop) / SR - t, env.max()


def row(name, bars):
    print(f"{name:26s}" + " ".join(f"{landed(b)[0] * 30:+5.1f}" for b in bars))


row("anvil blows", [8 + i / 2 for i in range(6)])
row("key press", [13])
row("bezel clicks", [21.5 + i / 4 for i in range(6)])
row("the tap", [20.5])
row("light switch, 18:00", [17.5])
