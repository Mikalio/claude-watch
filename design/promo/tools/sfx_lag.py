"""How long each sound effect takes to reach its hit, in frames at 30 fps (10 ms RMS)."""
import glob
import os
import subprocess

import numpy as np

SR = 48000
for path in sorted(glob.glob("public/audio/sfx/*.mp3")):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    hop = 480
    rms = np.sqrt(np.array([np.mean(x[i:i + hop] ** 2) for i in range(0, len(x) - hop, hop)]) + 1e-12)
    peak = int(np.argmax(rms))
    first = int(np.argmax(rms > rms[peak] * 0.25))
    print(f"{os.path.basename(path)[:-4]:10s} {len(x) / SR:5.2f} s  starts {first * 0.01 * 30:5.1f} f  peaks {peak * 0.01 * 30:5.1f} f  level {20 * np.log10(rms[peak]):5.1f} dB")
