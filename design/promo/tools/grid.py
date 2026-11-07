"""Finds a track's exact beat grid and prints its energy bar by bar, so scenes and music edits land on bars."""
import subprocess
import sys

import numpy as np

path, lo, hi = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
SR, HOP = 22050, 256
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                     capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.int16).astype(float) / 32768
n = len(x) // HOP
spec = np.abs(np.fft.rfft(x[:n * HOP].reshape(n, HOP) * np.hanning(HOP), axis=1))
bass = spec[:, :4].sum(1)  # below about 340 Hz: the kick
treble = spec[:, 12:].sum(1)
flux = np.maximum(0, np.diff(np.log1p(bass * 5)))
fps = SR / HOP
best = (0, 0, 0)
for bpm in np.arange(lo, hi, 0.01):
    period = 60 / bpm * fps
    for phase in np.arange(0, period, 1):
        idx = (phase + period * np.arange(int(len(flux) / period))).astype(int)
        idx = idx[idx < len(flux)]
        score = flux[idx].mean()
        if score > best[0]:
            best = (score, bpm, phase / fps)
score, bpm, phase = best
beat = 60 / bpm
print(f"{bpm:.2f} bpm, first beat {phase:.3f} s, beat {beat:.4f} s = {beat * 30:.2f} frames, contrast {score / flux.mean():.1f}x")
bar = beat * 4
print("bar  start    bass treble")
for i in range(0, int((len(x) / SR - phase) / bar)):
    a, b = int((phase + i * bar) * fps), int((phase + (i + 1) * bar) * fps)
    print(f"{i:3d} {phase + i * bar:7.2f}  {bass[a:b].mean():6.1f} {treble[a:b].mean():6.1f}")
