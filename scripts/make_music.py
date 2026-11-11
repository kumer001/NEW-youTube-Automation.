#!/usr/bin/env python3
"""Generate a royalty-free looping background tune (pure stdlib). Usage: make_music.py out.wav [seed]"""
import math
import random
import struct
import sys
import wave

out = sys.argv[1]
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
random.seed(seed)

SR = 22050
BPM = random.choice([112, 120, 128])
STEP = 60 / BPM / 2
ROOT = random.choice([196.0, 220.0, 246.94, 261.63])
PENTA = [0, 2, 4, 7, 9, 12, 14, 16]
LENGTH = 48.0

steps = int(LENGTH / STEP)
buf = [0.0] * int(SR * (steps * STEP + 1.0))


def freq(n):
    return ROOT * 2 ** (n / 12)


def note(t0, f, vol, dur):
    s = int(t0 * SR)
    for i in range(int(dur * SR)):
        if s + i >= len(buf):
            break
        t = i / SR
        env = min(1.0, t * 200) * math.exp(-t * 6)
        v = math.sin(2 * math.pi * f * t) + 0.4 * math.sin(4 * math.pi * f * t) + 0.2 * math.sin(6 * math.pi * f * t)
        buf[s + i] += vol * env * v


def tick(t0, vol):
    s = int(t0 * SR)
    for i in range(int(0.03 * SR)):
        if s + i >= len(buf):
            break
        buf[s + i] += vol * random.uniform(-1, 1) * math.exp(-i / SR * 150)


idx = 3
for k in range(steps):
    t = k * STEP
    idx = max(0, min(len(PENTA) - 1, idx + random.choice([-2, -1, 0, 1, 1, 2])))
    if random.random() < 0.85:
        note(t, freq(PENTA[idx]), 0.2, 0.4)
    if k % 4 == 0:
        note(t, freq(PENTA[[0, 2, 3, 1][(k // 4) % 4]] - 12), 0.3, 0.7)
    if k % 2 == 1:
        tick(t, 0.05)

peak = max(abs(x) for x in buf) or 1.0
g = 0.8 / peak
with wave.open(out, 'wb') as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, x * g)) * 32767)) for x in buf))
print('wrote', out)
