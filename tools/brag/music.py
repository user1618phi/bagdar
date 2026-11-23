"""Soundtrack for the launch film, synthesised from scratch with the standard library.

One piece on one grid: 120 BPM, so a beat is 0.5 s and every cut of the film (3, 6, 10, 14, 17 s)
falls on a beat. Music and effects share the key (C major / A minor) and the same grid: the
"stops" of the route scene are notes of the scale, the cuts are bells on the chord root.

    python tools/brag/music.py out.wav
"""

import math
import random
import struct
import sys
import wave

RATE = 44_100
BEAT = 0.5
LENGTH = 20.0
TAU = 2 * math.pi
mix = [0.0] * int(RATE * LENGTH)
rng = random.Random(7)

NOTE = {name: 440.0 * 2 ** ((semitone - 9) / 12) for name, semitone in
        {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}.items()}  # octave 4


def hz(name: str, octave: int) -> float:
    return NOTE[name] * 2 ** (octave - 4)


def add(start: float, seconds: float, gain: float, sample) -> None:
    """Mix `sample(t)` (t in seconds from the start of the sound) into the track."""
    first = int(start * RATE)
    for i in range(int(seconds * RATE)):
        index = first + i
        if 0 <= index < len(mix):
            mix[index] += gain * sample(i / RATE)


def pad(start, seconds, freq, gain):
    add(start, seconds, gain, lambda t: math.sin(TAU * freq * t) * min(1, t / 0.5) * min(1, (seconds - t) / 0.6))


def pluck(start, freq, gain, decay=0.22):
    add(start, decay * 5, gain, lambda t: (math.sin(TAU * freq * t) + 0.3 * math.sin(TAU * 3 * freq * t)) * math.exp(-t / decay) * min(1, t / 0.004))


def bell(start, freq, gain, decay=0.7):
    add(start, decay * 4, gain, lambda t: (math.sin(TAU * freq * t) + 0.4 * math.sin(TAU * 2.76 * freq * t) * math.exp(-t / 0.15)) * math.exp(-t / decay) * min(1, t / 0.003))


def kick(start, gain):
    add(start, 0.3, gain, lambda t: math.sin(TAU * (45 * t + 75 * 0.05 * (1 - math.exp(-t / 0.05)))) * math.exp(-t / 0.11))


def noise(start, seconds, gain, shape):
    previous = [0.0]

    def sample(t):
        value = rng.uniform(-1, 1)
        high = value - previous[0]  # crude high-pass: keeps the hiss, drops the rumble
        previous[0] = value
        return high * shape(t)

    add(start, seconds, gain, sample)


CHORDS = [("A", "C", "E"), ("A", "C", "E"), ("F", "A", "C"), ("F", "A", "C"), ("C", "E", "G"),
          ("C", "E", "G"), ("G", "B", "D"), ("G", "B", "D"), ("F", "A", "C"), ("C", "E", "G")]  # one per 2-second bar
CUTS = [3.0, 6.0, 10.0, 14.0, 17.0]

for bar, chord in enumerate(CHORDS):
    at = bar * 2.0
    for octave, name in ((2, chord[0]), (3, chord[0]), (3, chord[2]), (4, chord[1])):
        pad(at, 2.25, hz(name, octave), 0.045)
    for step in range(8):  # eighth notes
        t = at + step * BEAT / 2
        if t >= 3.0:
            pluck(t, hz(chord[step % 3], 4 + (step // 3) % 2), 0.055)
        if t >= 6.0 and step % 2 == 1:
            noise(t, 0.03, 0.035, lambda x: math.exp(-x / 0.008))  # hat on the off-beats
    for beat in (0, 2):
        if at + beat * BEAT >= 3.0:
            kick(at + beat * BEAT, 0.42)
    if at >= 6.0:
        for beat in range(4):
            add(at + beat * BEAT, 0.45, 0.11, lambda t, f=hz(chord[0], 2): math.sin(TAU * f * t) * math.exp(-t / 0.16))

# effects, on the same grid and in the same key
for index in range(23):  # scene 1: one soft tick per typed character
    noise(0.15 + index / 23, 0.006, 0.05, lambda x: math.exp(-x / 0.002))
bell(1.5, hz("A", 4), 0.10)  # the question lands
for cut in CUTS:
    noise(cut - 0.35, 0.35, 0.03, lambda x: (x / 0.35) ** 2)  # a breath before the cut
    bell(cut, hz("C" if cut >= 10 else "A", 5), 0.11)
SCALE = ["C", "D", "E", "G", "A"]  # scene 4: each stop of the route is the next note of the pentatonic scale
for stop in range(13):
    pluck(10.5 + stop * 0.25, hz(SCALE[stop % 5], 5 + stop // 5), 0.085, decay=0.16)
bell(15.5, hz("E", 5), 0.13)  # the mark lands on the chosen step
bell(17.0, hz("G", 5), 0.08)

with wave.open(sys.argv[1], "wb") as out:
    out.setnchannels(2)
    out.setsampwidth(2)
    out.setframerate(RATE)
    frames = bytearray()
    for index, value in enumerate(mix):
        t = index / RATE
        value *= min(1.0, t / 0.02) * min(1.0, (LENGTH - t) / 1.4)  # fade in and out
        sample = int(32767 * math.tanh(1.5 * value) * 0.85)  # soft clip: nothing harsh or spiky
        frames += struct.pack("<hh", sample, sample)
    out.writeframes(bytes(frames))
