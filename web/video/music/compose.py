#!/usr/bin/env python3
"""Original soundtrack for the vigilAI project-overview film.

A slow bossa-nova / ambient-downtempo piece in D major at the film's tempo (80 BPM, 4/4). Every
sound is synthesized in this file from sines, exponentials and seeded noise: no samples,
recordings, soundfonts, MIDI files or loops are read. The only input is the film timeline,
music/timeline.json, exported from web/src/lib/project-overview.ts by scripts/export-timeline.ts.

Regenerate from web/video:
    node scripts/export-timeline.ts
    uv run --no-project --python 3.12 --with numpy python music/compose.py

The render is deterministic: the same timeline and script give a byte-identical WAV.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SR = 44_100
SEED = 23_382_023            # every random choice derives from this seed
BEATS_PER_BAR = 4            # 4/4
TARGET_LUFS = -18.0          # integrated loudness of the delivered file
TRUE_PEAK_LIMIT = -1.5       # dBTP delivery ceiling
TRUE_PEAK_AIM = -2.0         # internal ceiling, leaves margin for meter differences
FADE_IN = 1.5                # seconds, from digital silence
FADE_OUT = 3.9               # seconds, ending 50 ms before the film end
SILENT_TAIL = 0.05           # seconds of digital silence at the very end

HERE = Path(__file__).resolve().parent
TIMELINE = HERE / "timeline.json"
OUTPUT = HERE.parent / "public" / "audio" / "soundtrack.wav"

TAU = 2.0 * np.pi


def hz(midi: float) -> float:
    """Equal temperament, A4 = 440 Hz."""
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def db(value: float) -> float:
    return 10.0 ** (value / 20.0)


# --------------------------------------------------------------------------------------------
# Timeline
# --------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Chapter:
    id: str
    theme: str
    start_bar: int
    end_bar: int
    beats: dict

    @property
    def bars(self) -> int:
        return self.end_bar - self.start_bar


@dataclass(frozen=True)
class Timeline:
    bpm: float
    bar: float               # seconds per bar
    duration: float
    n_bars: int
    chapters: tuple


def check(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"timeline check failed: {message}")


def load_timeline(path: Path) -> Timeline:
    data = json.loads(path.read_text(encoding="utf-8"))
    bpm = float(data["bpm"])
    bar = 60.0 / bpm * BEATS_PER_BAR
    duration = float(data["durationSeconds"])

    def bar_index(seconds: float, what: str) -> int:
        position = seconds / bar
        check(abs(position - round(position)) < 1e-9, f"{what} ({seconds} s) is not on a bar line (bar = {bar:g} s)")
        return int(round(position))

    n_bars = bar_index(duration, "film end")
    chapters, edge = [], 0
    for item in data["chapters"]:
        start = bar_index(float(item["start"]), f"start of chapter '{item['id']}'")
        end = bar_index(float(item["end"]), f"end of chapter '{item['id']}'")
        check(start == edge, f"chapter '{item['id']}' starts at bar {start}, expected bar {edge}")
        check(end > start, f"chapter '{item['id']}' is empty")
        beats = {beat["id"]: float(beat["at"]) for beat in item["beats"]}
        chapters.append(Chapter(item["id"], item["theme"], start, end, beats))
        edge = end
    check(edge == n_bars, f"chapters end at bar {edge}, the film ends at bar {n_bars}")
    return Timeline(bpm, bar, duration, n_bars, tuple(chapters))


# --------------------------------------------------------------------------------------------
# Harmony: close, guitar-like voicings between E2 and E5 (MIDI numbers)
# --------------------------------------------------------------------------------------------

PITCH = {"C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "A#": 10, "B": 11}


@dataclass(frozen=True)
class Chord:
    tones: str               # chord tones, used for melodic choices (fills, colour notes)
    bass: int                # bass-instrument root
    thumb: tuple             # guitar thumb: root, alternate bass
    comp: tuple              # three-finger voicing for bossa comping
    full: tuple              # full guitar voicing, lowest string first
    ep: tuple                # electric-piano voicing
    pad: tuple               # pad voicing

    @property
    def pcs(self) -> frozenset:
        return frozenset(PITCH[name] for name in self.tones.split())


CHORDS = {
    "Dmaj9":    Chord("D F# A C# E",   38, (50, 45), (54, 61, 64), (50, 54, 61, 64, 69), (57, 61, 64, 66), (50, 57, 61, 64)),
    "Bm9":      Chord("B D F# A C#",   35, (47, 42), (50, 57, 61), (47, 50, 57, 61, 66), (50, 57, 61, 66), (47, 54, 57, 62)),
    "Em9":      Chord("E G B D F#",    40, (40, 47), (55, 62, 66), (40, 55, 62, 66, 71), (55, 62, 66, 71), (52, 55, 62, 66)),
    "A13sus4":  Chord("A D E G B F#",  33, (45, 40), (55, 62, 66), (45, 55, 62, 66, 71), (55, 62, 66, 71), (45, 55, 62, 66)),
    "A13":      Chord("A C# E G B F#", 33, (45, 40), (55, 61, 66), (45, 55, 61, 66, 71), (55, 61, 66, 71), (45, 55, 61, 66)),
    "Gmaj9":    Chord("G B D F# A",    43, (43, 50), (54, 59, 62), (43, 54, 59, 62, 69), (59, 62, 66, 69), (43, 54, 59, 62)),
    "Gm6":      Chord("G Bb D E",      43, (43, 50), (52, 58, 62), (43, 52, 58, 62, 67), (58, 62, 64, 67), (43, 52, 58, 62)),
    # darker colours for the measurement-audit chapter
    "Gmaj7#11": Chord("G B D F# C#",   31, (43, 50), (54, 59, 61), (43, 54, 59, 61, 66), (50, 54, 59, 61), (43, 54, 59, 61)),
    "Em11":     Chord("E G B D F# A",  40, (40, 47), (55, 57, 62), (40, 55, 57, 62, 66), (55, 57, 62, 66), (40, 55, 57, 62)),
    "F#7b13":   Chord("F# A# C# E D",  42, (42, 49), (52, 58, 62), (42, 52, 58, 62, 66), (52, 58, 62, 66), (42, 52, 58, 62)),
}
FINAL_EP = (61, 64, 66, 69)            # top voicing for the last Dmaj9

LOOP = ("Dmaj9", "Bm9", "Em9", "A13sus4>A13")     # "a>b": a on beats 1-2, b on beats 3-4
DARK = ("Bm9", "Gmaj7#11", "Em11", "F#7b13")


def halves(name: str) -> tuple:
    first, _, second = name.partition(">")
    return first, second or first


def bass_fifth(root: int) -> int:
    return root - 5 if root - 5 >= 31 else root + 7


def loop_bars(n: int) -> list:
    """One chord per bar; a block always ends on the dominant so the next chapter lands on D."""
    k, r = divmod(n, 4)
    seq = list(LOOP) * k
    if r == 1:
        seq = seq[:-1] + ["A13sus4", "A13"] if k else ["Dmaj9"]
    elif r == 2:
        seq += ["Gmaj9", "A13sus4>A13"]
    elif r == 3:
        seq += ["Dmaj9", "Gmaj9", "A13sus4>A13"]
    return seq


def slow_loop(n: int) -> list:
    """The same changes at two bars per chord."""
    pairs = (("Dmaj9", "Dmaj9"), ("Bm9", "Bm9"), ("Em9", "Em9"), ("A13sus4", "A13"))
    seq, i = [], 0
    while len(seq) < n:
        seq += pairs[i % 4]
        i += 1
    return seq[:n]


def dark_bars(n: int, lift: int) -> list:
    """Relative-minor colours at two bars per chord, then a ii-V lift back towards D."""
    seq, i = [], 0
    while len(seq) < lift:
        seq += [DARK[i % 4]] * 2
        i += 1
    seq = seq[:lift]
    tail = n - lift
    return seq + ["Gmaj9"] * (tail - 2) + ["Em9", "A13sus4>A13"]


def outro_bars(n: int, final: int) -> list:
    return (list(LOOP) * 4)[: final - 2] + ["Gmaj9", "Gm6"] + ["Dmaj9"] * (n - final)


# --------------------------------------------------------------------------------------------
# Arrangement: one record per bar
# --------------------------------------------------------------------------------------------

ROLES = {
    "question": "intro", "origin": "build", "benchmarks": "groove", "design": "groove",
    "disclosure": "findings", "validity": "dark", "implementation": "return", "limitations": "outro",
}


@dataclass
class Bar:
    index: int
    chapter: str
    role: str
    i: int                   # bar within its chapter
    chords: tuple            # chord on beats 1-2, chord on beats 3-4
    guitar: str = "none"
    g_lvl: float = 0.0
    bass: str = "none"
    b_lvl: float = 0.0
    ep: str = "none"
    e_lvl: float = 0.0
    pad: object = 0.0        # level, or (start, end) ramp within the bar
    swish: object = 0.0
    tap: float = 0.0
    stick: float = 0.0


def lift_start(ch: Chapter, bar: float) -> int:
    """The lift begins in the bar holding the closing 'message' beat (fallback: last two bars)."""
    at = ch.beats.get("message")
    i = int(at // bar) - ch.start_bar if at is not None else ch.bars - 2
    return max(2, min(i, ch.bars - 2))


def final_bar(ch: Chapter, bar: float) -> int:
    """The final tonic lands on the first bar line after the closing 'close' beat."""
    at = ch.beats.get("close")
    i = math.ceil(at / bar - 1e-9) - ch.start_bar if at is not None else ch.bars - 2
    return max(2, min(i, ch.bars - 1))


def build_plan(tl: Timeline) -> list:
    plan = []
    for ch in tl.chapters:
        check(ch.id in ROLES, f"no musical role for chapter '{ch.id}'")
        role = ROLES[ch.id]
        check((role == "dark") == (ch.theme == "dark"), f"chapter '{ch.id}' theme '{ch.theme}' does not match role '{role}'")
        n, extra = ch.bars, {}
        if role == "findings":
            seq = slow_loop(n)
        elif role == "dark":
            extra["lift"] = lift_start(ch, tl.bar)
            seq = dark_bars(n, extra["lift"])
        elif role == "outro":
            extra["final"] = final_bar(ch, tl.bar)
            seq = outro_bars(n, extra["final"])
        else:
            seq = loop_bars(n)
        bars = [Bar(ch.start_bar + i, ch.id, role, i, halves(name)) for i, name in enumerate(seq)]
        arrange(bars, role, extra)
        plan += bars
    return plan


def arrange(bars: list, role: str, extra: dict) -> None:
    n = len(bars)
    for b in bars:
        i = b.i
        dominant = b.chords[1] == "A13"
        if role == "intro":                      # nylon guitar alone, pad swell
            b.guitar, b.g_lvl = "arp", 0.55
            b.pad = (0.2, 0.6) if i == 0 else 0.6
        elif role == "build":                    # bass from the first bar, brushes from the third
            b.guitar, b.g_lvl = ("arp", 0.78) if i < 2 else ("comp", 0.72)
            b.bass, b.b_lvl = ("half", 0.72) if i < n - 2 else ("groove", 0.74)
            if i >= 2:
                span = max(1, n - 2)
                b.swish = (0.25 + 0.4 * (i - 2) / span, 0.25 + 0.4 * (i - 1) / span)
            b.pad = 0.8
            if i == n - 1:
                b.ep, b.e_lvl = "fill", 0.7
        elif role == "groove":                   # the full (still gentle) bossa
            b.guitar, b.g_lvl = "comp", 0.85
            b.bass, b.b_lvl = "groove", 0.9
            b.swish, b.tap, b.stick = 0.75, 0.7, 0.65
            b.pad = 0.55
            if dominant:
                b.ep, b.e_lvl = "fill", 0.85
        elif role == "findings":                 # fewer attacks, bass on downbeats, faint swish
            b.guitar, b.g_lvl = "hold", 0.78
            b.bass, b.b_lvl = "downbeat", 0.8
            b.swish = 0.3
            b.pad = 0.7
            if i % 4 == 2:
                b.ep, b.e_lvl = "sparse", 0.7
        elif role == "dark":                     # ambient: low e-piano and pad, no rhythm
            if i < extra["lift"]:
                b.bass, b.b_lvl = "sustain", 0.55
                b.ep, b.e_lvl = "dark", 0.75
                b.pad = 0.95
            else:
                first = i == extra["lift"]
                b.guitar, b.g_lvl = "roll", 0.62
                b.bass, b.b_lvl = "downbeat", 0.7
                b.ep, b.e_lvl = ("lift_rise" if first else "lift_dom"), 0.75
                b.pad = 1.15
                if i == n - 1:
                    b.swish = (0.0, 0.32)
        elif role == "return":                   # light groove: comping, soft brushes, bass
            b.guitar, b.g_lvl = "comp", 0.72
            b.bass, b.b_lvl = "groove", 0.72
            b.swish, b.tap = 0.5, 0.35
            b.pad = 0.5
            if dominant:
                b.ep, b.e_lvl = "fill", 0.75
        elif role == "outro":                    # thin out, plagal cadence, final tonic
            final = extra["final"]
            pre = final - 2
            if i < pre:
                f = i / max(1, pre - 1)
                b.guitar, b.g_lvl = ("comp" if f < 0.5 else "hold"), 0.75 - 0.12 * f
                b.bass = "groove" if f < 0.34 else ("half" if f < 0.67 else "downbeat")
                b.b_lvl = 0.75 - 0.15 * f
                b.swish = (0.5 * (1 - f), 0.5 * (1 - f) * 0.7)
                b.tap = 0.3 if f < 0.34 else 0.0
                b.pad = 0.5
            elif i < final:
                b.guitar, b.g_lvl = "roll", 0.58
                b.bass, b.b_lvl = "downbeat", 0.55
                b.ep, b.e_lvl = "cadence", 0.7
                b.pad = 0.6
            else:
                if i == final:
                    b.guitar, b.g_lvl = "final", 0.42
                    b.bass, b.b_lvl = "final", 0.4
                    b.ep, b.e_lvl = "final", 0.45
                b.pad = 0.65


def chord_at(plan: list, bar_index: int, eighth: int) -> Chord:
    bar_index += eighth // 8
    eighth %= 8
    b = plan[min(bar_index, len(plan) - 1)]
    return CHORDS[b.chords[0 if eighth < 4 else 1]]


def chord_span(plan: list, index: int, key: str) -> int:
    """Number of consecutive bars (from index) that keep the same chord and the same part mode."""
    b, k = plan[index], 1
    while index + k < len(plan):
        nxt = plan[index + k]
        if nxt.chords != b.chords or getattr(nxt, key) != getattr(b, key) or b.chords[0] != b.chords[1]:
            break
        k += 1
    return k


def chord_changed(plan: list, index: int, key: str) -> bool:
    if index == 0:
        return True
    prev, b = plan[index - 1], plan[index]
    return prev.chords[1] != b.chords[0] or getattr(prev, key) != getattr(b, key)


# --------------------------------------------------------------------------------------------
# Performance: deterministic humanisation
# --------------------------------------------------------------------------------------------

class Player:
    """Slow timing drift plus small per-note timing and velocity scatter, all from one RNG."""

    def __init__(self, rng: np.random.Generator, jitter_ms: float, drift_ms: float, lag_ms: float = 0.0):
        self.rng = rng
        self.jitter = jitter_ms / 1000.0
        self.drift = drift_ms / 1000.0
        self.lag = lag_ms / 1000.0
        self.periods = rng.uniform(6.0, 21.0, 3)
        self.phases = rng.uniform(0.0, TAU, 3)

    def time(self, t: float) -> float:
        drift = self.drift * float(np.mean(np.sin(TAU * t / self.periods + self.phases)))
        jitter = float(np.clip(self.rng.normal(0.0, self.jitter), -2.5 * self.jitter, 2.5 * self.jitter))
        return max(0.0, t + self.lag + drift + jitter)

    def vel(self, v: float, spread: float = 0.07) -> float:
        return float(np.clip(v * math.exp(self.rng.normal(0.0, spread)), 0.02, 1.0))


# --------------------------------------------------------------------------------------------
# Parts: note events (time s, midi, velocity, duration s, flags)
# --------------------------------------------------------------------------------------------

COMP_PATTERNS = (((0, 3, 6, 10, 13), 0.55), ((0, 3, 7, 10, 13), 0.2), ((0, 3, 6, 11, 13), 0.15), ((0, 3, 6, 9, 12), 0.1))
ARP_PATTERNS = (
    ((0, 0, 0.62), (1, 1, 0.40), (2, 2, 0.44), (3, 3, 0.47), (5, 4, 0.40), (6, 2, 0.34)),
    ((0, 0, 0.58), (0, (1, 2, 3), 0.42), (4, "alt", 0.45), (5, 4, 0.36), (6, 3, 0.32)),
    ((0, 0, 0.60), (1, 2, 0.40), (2, 3, 0.44), (3, 4, 0.42), (4, "alt", 0.40), (6, (2, 3), 0.34)),
)
FILL_TEMPLATES = (
    ((4, 1), (5, 1), (6, 1)),
    ((3, 2), (6, 1)),
    ((4, 2), (6, 1), (7, 1)),
    ((2, 1), (4, 1), (6, 2)),
    ((5, 1), (6, 1), (8, 1)),
)
CLAVE = (0, 3, 6, 10, 13)                                  # two-bar bossa clave, eighth positions
TAP_ACCENTS = (0.55, 0.28, 0.78, 0.32, 0.52, 0.28, 0.80, 0.36)


def guitar_events(plan: list, bar: float, rng: np.random.Generator) -> list:
    e8 = bar / 8
    thumb = Player(rng, 3.0, 3.0)
    fingers = Player(rng, 4.0, 3.0, lag_ms=5.0)
    events = []
    last_arp, pattern, run_start = -1, None, 0

    def note(player, t, m, v, d):
        events.append((player.time(t), m, player.vel(v), d))

    def roll(player, t, notes, v, d, spread):
        t = player.time(t)
        for j, m in enumerate(notes):
            offset = max(0.0, spread * j * (1.0 + 0.2 * rng.standard_normal()))
            events.append((t + offset, m, player.vel(v * (1.0 - 0.04 * j)), max(0.2, d - offset)))

    for b in plan:
        if b.guitar == "none":
            continue
        t0, lvl = b.index * bar, b.g_lvl
        c1, c2 = CHORDS[b.chords[0]], CHORDS[b.chords[1]]
        split = b.chords[0] != b.chords[1]

        def at(pos):
            return c1 if pos < 4 else c2

        def ring(pos):
            return ((4 if split and pos < 4 else 8) - pos) * e8 + 0.25

        if b.guitar == "arp":
            options = [k for k in range(len(ARP_PATTERNS)) if k != last_arp]
            last_arp = options[int(rng.integers(len(options)))]
            for pos, voice, v in ARP_PATTERNS[last_arp]:
                c, t = at(pos), t0 + pos * e8
                if voice == "alt":
                    note(thumb, t, c.thumb[1], v * lvl, ring(pos))
                elif isinstance(voice, tuple):
                    roll(fingers, t + 0.01, [c.full[x] for x in voice], v * lvl, ring(pos), 0.035)
                elif voice == 0:
                    note(thumb, t, c.full[0], v * lvl, ring(pos))
                else:
                    note(fingers, t, c.full[voice], v * lvl, ring(pos))

        elif b.guitar == "comp":
            if b.index == 0 or plan[b.index - 1].guitar != "comp":
                run_start = b.index
            cycle = (b.index - run_start) % 2
            if cycle == 0 or pattern is None:
                weights = np.array([w for _, w in COMP_PATTERNS])
                pattern = COMP_PATTERNS[int(rng.choice(len(COMP_PATTERNS), p=weights / weights.sum()))][0]
            for pos in (0, 4):                                     # thumb on beats 1 and 3
                c = at(pos)
                note(thumb, t0 + pos * e8, c.thumb[0] if pos == 0 else c.thumb[1], (0.4 if pos == 0 else 0.34) * lvl, 1.2)
            hits = [p for p in pattern if 8 * cycle <= p < 8 * cycle + 8]
            for j, p in enumerate(hits):
                pos = p - 8 * cycle
                nxt = hits[j + 1] - 8 * cycle if j + 1 < len(hits) else 8
                c = at(pos)
                voicing = list(c.comp)
                if pos != 0 and rng.random() < 0.15:
                    voicing.append(c.full[-1])
                v = (0.52 if p in (3, 6, 13) else 0.47) * lvl
                d = float(np.clip((nxt - pos) * e8 * 0.85, 0.22, 0.95))
                roll(fingers, t0 + pos * e8, voicing, v, d, 0.006)

        elif b.guitar == "hold":
            if chord_changed(plan, b.index, "guitar"):
                note(thumb, t0, c1.thumb[0], 0.5 * lvl, bar * chord_span(plan, b.index, "guitar") * 0.9)
                roll(fingers, t0 + 0.012, list(c1.comp) + [c1.full[-1]], 0.44 * lvl, bar * 1.6, 0.012)
                if rng.random() < 0.35:
                    note(fingers, t0 + 6 * e8, c1.full[-1], 0.28 * lvl, 1.5)
            else:
                if rng.random() < 0.75:
                    note(thumb, t0, c1.thumb[1], 0.38 * lvl, bar * 0.9)
                if rng.random() < 0.6:
                    roll(fingers, t0 + 3 * e8, list(c1.comp), 0.34 * lvl, 1.6, 0.01)
            if split:
                note(thumb, t0 + 4 * e8, c2.thumb[0], 0.4 * lvl, 1.6)
                roll(fingers, t0 + 4 * e8 + 0.01, list(c2.comp), 0.4 * lvl, 1.6, 0.012)

        elif b.guitar == "roll":
            roll(fingers, t0, list(c1.full), 0.5 * lvl, bar * (0.5 if split else 1.0) + 0.6, 0.03)
            if split:
                note(thumb, t0 + 4 * e8, c2.thumb[0], 0.38 * lvl, 2.0)
                roll(fingers, t0 + 4 * e8 + 0.01, list(c2.comp), 0.42 * lvl, 2.2, 0.02)
            else:
                note(thumb, t0 + 4 * e8, c1.thumb[1], 0.34 * lvl, 1.6)
                note(fingers, t0 + 6 * e8, c1.full[-1], 0.28 * lvl, 1.6)

        elif b.guitar == "final":
            roll(fingers, t0, list(c1.full), 0.52 * lvl, 6.0, 0.06)
            note(fingers, t0 + bar + 2 * e8, 66, 0.22 * lvl, 3.0)
    return events


def bass_events(plan: list, bar: float, rng: np.random.Generator) -> list:
    e8 = bar / 8
    player = Player(rng, 3.0, 2.5, lag_ms=2.0)
    events = []

    def note(t, m, v, d, sustain=False):
        events.append((player.time(t), m, player.vel(v, 0.06), d, sustain))

    for b in plan:
        if b.bass == "none":
            continue
        t0, lvl = b.index * bar, b.b_lvl
        c1, c2 = CHORDS[b.chords[0]], CHORDS[b.chords[1]]
        nxt = plan[b.index + 1] if b.index + 1 < len(plan) else None
        if b.bass == "half":
            note(t0, c1.bass, 0.62 * lvl, 1.35)
            note(t0 + 4 * e8, bass_fifth(c2.bass) if c1 is c2 else c2.bass, 0.5 * lvl, 1.35)
        elif b.bass == "groove":                                   # dotted quarter + eighth, root-fifth
            note(t0, c1.bass, 0.62 * lvl, 3 * e8 * 0.95)
            if rng.random() < 0.7:
                note(t0 + 3 * e8, c1.bass, 0.36 * lvl, e8 * 0.9)
            note(t0 + 4 * e8, bass_fifth(c2.bass), 0.54 * lvl, 3 * e8 * 0.95)
            if rng.random() < 0.65:
                target = CHORDS[nxt.chords[0]].bass if nxt else c2.bass
                if target != c2.bass and rng.random() < 0.5:
                    m = target + (1 if rng.random() < 0.5 else -1)    # chromatic approach
                else:
                    m = bass_fifth(c2.bass)
                note(t0 + 7 * e8, m, 0.38 * lvl, e8 * 0.9)
        elif b.bass == "downbeat":
            if chord_changed(plan, b.index, "bass"):
                note(t0, c1.bass, 0.6 * lvl, bar * chord_span(plan, b.index, "bass") * 0.95)
            elif rng.random() < 0.5:
                note(t0 + 4 * e8, bass_fifth(c1.bass), 0.42 * lvl, bar * 0.45)
            if b.chords[0] != b.chords[1]:
                note(t0 + 4 * e8, c2.bass, 0.5 * lvl, bar * 0.45)
        elif b.bass == "sustain":
            if chord_changed(plan, b.index, "bass"):
                note(t0, c1.bass, 0.6 * lvl, bar * chord_span(plan, b.index, "bass") - 0.15, True)
        elif b.bass == "final":
            note(t0, c1.bass, 0.55 * lvl, 5.5, True)
    return events


def epiano_events(plan: list, bar: float, rng: np.random.Generator) -> list:
    e8 = bar / 8
    player = Player(rng, 6.0, 3.0, lag_ms=6.0)
    events = []
    skipped = False

    def chord_notes(t, notes, v, d, spread, dark=False):
        t = player.time(t)
        for j, m in enumerate(notes):
            events.append((t + spread * j, m, player.vel(v), d, dark))

    def pool(c, lo=62, hi=76):
        return [m for m in range(lo, hi + 1) if m % 12 in c.pcs]

    for b in plan:
        mode, lvl, t0 = b.ep, b.e_lvl, b.index * bar
        c1, c2 = CHORDS[b.chords[0]], CHORDS[b.chords[1]]
        if mode == "fill":
            if b.role != "build" and rng.random() < 0.12 and not skipped:   # occasionally rest
                skipped = True
                continue
            skipped = False
            template = FILL_TEMPLATES[int(rng.integers(len(FILL_TEMPLATES)))]
            current = float(rng.choice([69, 71, 73]))
            direction = -1 if rng.random() < 0.7 else 1
            for j, (pos, voices) in enumerate(template):
                notes_pool = pool(chord_at(plan, b.index, pos))
                idx = int(np.argmin([abs(m - current) for m in notes_pool]))
                if j:
                    idx = int(np.clip(idx + direction * int(rng.choice([1, 1, 2])), 0, len(notes_pool) - 1))
                m = notes_pool[idx]
                current = m
                notes = [m]
                if voices == 2:
                    lower = [x for x in notes_pool if 3 <= m - x <= 5]
                    if lower:
                        notes.append(lower[-1])
                last = j == len(template) - 1
                chord_notes(t0 + pos * e8, notes, (0.44 - 0.04 * j) * lvl, 1.6 if last else 0.8, 0.004)
        elif mode == "sparse":
            notes_pool = pool(c2, 64, 74)
            aim = 69 + int(rng.integers(-2, 3))
            top = notes_pool[int(np.argmin([abs(m - aim) for m in notes_pool]))]
            lower = [x for x in notes_pool if 3 <= top - x <= 5]
            chord_notes(t0 + 4 * e8, [top] + lower[-1:], 0.32 * lvl, 2.2, 0.006)
        elif mode == "dark":
            if chord_changed(plan, b.index, "ep"):
                span = chord_span(plan, b.index, "ep")
                chord_notes(t0, list(c1.ep), 0.46 * lvl, span * bar - 0.15, 0.018, dark=True)
            elif rng.random() < 0.65:
                colour = [m for m in pool(c1, 62, 72) if m not in c1.ep]
                m = colour[int(rng.integers(len(colour)))]
                chord_notes(t0 + (4 + int(rng.integers(0, 2))) * e8, [m], 0.3 * lvl, 2.2, 0.0, dark=True)
        elif mode == "lift_rise":
            chord_notes(t0, list(c1.ep), 0.4 * lvl, bar * 0.95, 0.015)
            rise = [m for m in pool(c1, 64, 74)][:3]
            for j, m in enumerate(rise):
                chord_notes(t0 + (4 + j) * e8, [m], (0.3 + 0.02 * j) * lvl, 1.6, 0.0)
        elif mode == "lift_dom":
            chord_notes(t0, list(c1.ep), 0.38 * lvl, bar * 0.5, 0.015)
            chord_notes(t0 + 4 * e8, list(c2.ep), 0.36 * lvl, bar * 0.6, 0.015)
            lead = 73 if 73 % 12 in c2.pcs else c2.ep[-1]
            chord_notes(t0 + 6 * e8, [lead], 0.3 * lvl, 1.8, 0.0)
        elif mode == "cadence":
            chord_notes(t0, list(c1.ep), 0.36 * lvl, bar * 1.05, 0.025)
        elif mode == "final":
            chord_notes(t0 + 0.02, list(FINAL_EP), 0.38 * lvl, 6.0, 0.03)
    return events


def percussion_events(plan: list, bar: float, rng: np.random.Generator) -> tuple:
    """Swish accents (beats 2 and 4), brush taps (eighths) and side-stick (bossa clave)."""
    e8 = bar / 8
    player = Player(rng, 3.0, 2.0)
    swishes, taps, sticks = [], [], []
    run_start = 0
    for b in plan:
        t0 = b.index * bar
        level = max(b.swish) if isinstance(b.swish, tuple) else b.swish
        if level > 0:
            for beat in (1, 3):
                swishes.append((player.time(t0 + beat * bar / 4), player.vel(0.7, 0.12)))
        if b.tap > 0:
            for pos, accent in enumerate(TAP_ACCENTS):
                if accent < 0.4 and rng.random() < 0.2:
                    continue
                taps.append((player.time(t0 + pos * e8), player.vel(accent * b.tap, 0.12), accent > 0.6))
        if b.stick > 0:
            if b.index == 0 or plan[b.index - 1].stick == 0:
                run_start = b.index
            cycle = (b.index - run_start) % 2
            for p in CLAVE:
                if 8 * cycle <= p < 8 * cycle + 8 and rng.random() > 0.08:
                    sticks.append((player.time(t0 + (p - 8 * cycle) * e8), player.vel(0.7 * b.stick, 0.1)))
    return swishes, taps, sticks


def pad_segments(plan: list, bar: float) -> list:
    """Contiguous spans of one chord (in half bars) -> (start s, end s, chord name)."""
    segments = []
    for b in plan:
        for h, name in enumerate(b.chords):
            t = b.index * bar + h * bar / 2
            if segments and segments[-1][2] == name:
                segments[-1][1] = t + bar / 2
            else:
                segments.append([t, t + bar / 2, name])
    return segments


# --------------------------------------------------------------------------------------------
# Instruments
# --------------------------------------------------------------------------------------------

SOFT_LP = np.hanning(11)[1:-1]
SOFT_LP /= SOFT_LP.sum()


def nylon_tone(f0: float, vel: float, dur: float, rng: np.random.Generator) -> np.ndarray:
    """Modal plucked string: pluck-position weighted harmonics with slight inharmonicity,
    frequency-dependent decay, a second (detuned) polarisation and a soft finger transient."""
    n = int(min(34, 5000 // f0))
    k = np.arange(1, n + 1)
    fk = k * f0 * np.sqrt(1.0 + (3.5e-5 if f0 < 160 else 1.2e-5) * k * k)
    p = 0.11 + 0.07 * rng.random()
    amp = np.abs(np.sin(np.pi * k * p)) / k
    amp /= np.sqrt(1.0 + (fk / (900.0 + 2400.0 * vel)) ** 4)       # softer touch, darker tone
    amp /= np.sqrt(np.sum(amp ** 2))
    t60 = float(np.clip(4.5 * (110.0 / f0) ** 0.6, 1.1, 5.0))
    sigma = 6.91 / t60 + 1.3e-6 * fk ** 2 + 0.25 * (k - 1)
    damp = 0.075                                                   # left-hand release
    length = int(min(dur + 7 * damp, 1.15 * t60) * SR)
    t = np.arange(length) / SR
    y = np.zeros(length)
    detune = 1.0 + 0.0007 * rng.standard_normal(6)
    for j in range(n):
        lj = min(length, int(9.2 / sigma[j] * SR) + 1)
        tj = t[:lj]
        y[:lj] += amp[j] * np.exp(-sigma[j] * tj) * np.sin(TAU * fk[j] * tj)
        if j < 6:
            y[:lj] += 0.22 * amp[j] * np.exp(-1.35 * sigma[j] * tj) * np.sin(TAU * fk[j] * detune[j] * tj)
    off = int(dur * SR)
    if off < length:
        y[off:] *= np.exp(-(t[off:] - dur) / damp)
    a = int(0.0015 * SR)
    y[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    m = min(length, int(0.02 * SR))
    noise = rng.standard_normal(m) * np.exp(-np.arange(m) / (0.0035 * SR))
    y[:m] += 0.06 * vel * np.convolve(noise, SOFT_LP, mode="same")
    return y * vel ** 1.4


def epiano_tone(f0: float, vel: float, dur: float, rng: np.random.Generator, dark: bool = False) -> np.ndarray:
    """Soft two-operator FM (1:1) with a decaying index and a faint, fast tine partial."""
    t60 = float(np.clip(6.0 * (262.0 / f0) ** 0.5, 2.5, 9.0))
    release = 0.28
    length = int(min(dur + 6 * release, 1.05 * t60) * SR)
    t = np.arange(length) / SR
    w = TAU * f0
    index = (0.45 + 1.25 * vel) * (0.6 if dark else 1.0) * np.exp(-t / 0.5) + 0.1
    y = np.sin(w * t + index * np.sin(w * t))
    tine = 7.0 * f0
    if tine < 4200.0:
        y += 0.07 * vel * np.exp(-t / 0.045) * np.sin(TAU * tine * t)
    env = np.exp(-6.91 * t / t60)
    a = int(0.004 * SR)
    env[:a] *= np.linspace(0.0, 1.0, a)
    off = int(dur * SR)
    if off < length:
        env[off:] *= np.exp(-(t[off:] - dur) / release)
    return y * env * vel ** 1.3


def bass_tone(f0: float, vel: float, dur: float, rng: np.random.Generator, sustain: bool = False) -> np.ndarray:
    """Sine fundamental with a little 2nd/3rd harmonic, soft attack, plucked decay."""
    t60 = 8.0 if sustain else 3.0
    attack = 0.04 if sustain else 0.012
    release = 0.35 if sustain else 0.07
    length = int(min(dur + 6 * release, t60) * SR)
    t = np.arange(length) / SR
    w = TAU * f0
    y = (np.sin(w * t)
         + (0.32 * np.exp(-t / 0.5) + 0.18) * np.sin(2 * w * t)
         + 0.13 * np.exp(-t / 0.25) * np.sin(3 * w * t)
         + 0.04 * np.exp(-t / 0.12) * np.sin(4 * w * t))
    env = np.exp(-6.91 * t / t60)
    a = int(attack * SR)
    env[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    off = int(dur * SR)
    if off < length:
        env[off:] *= np.exp(-(t[off:] - dur) / release)
    return y * env * vel


def side_stick(vel: float, rng: np.random.Generator) -> np.ndarray:
    """Short wooden knock: two damped partials, a low body and a band-limited click."""
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    click = rng.standard_normal(n) * np.exp(-t / 0.004)
    spectrum = np.fft.rfft(click)
    f = np.fft.rfftfreq(n, 1 / SR)
    click = np.fft.irfft(spectrum * np.exp(-0.5 * (np.log2(np.maximum(f, 1.0) / 2300.0) / 0.6) ** 2), n)
    wood = 0.6 * np.sin(TAU * 1180.0 * t) * np.exp(-t / 0.012) + 0.3 * np.sin(TAU * 1870.0 * t) * np.exp(-t / 0.008)
    body = 0.5 * np.sin(TAU * 380.0 * t) * np.exp(-t / 0.025)
    return (0.5 * click + wood + body) * vel


def place(bus: np.ndarray, start: float, y: np.ndarray, gains: tuple) -> None:
    i0 = int(round(start * SR))
    if i0 >= bus.shape[0]:
        return
    m = min(len(y), bus.shape[0] - i0)
    for ch, g in enumerate(gains):
        bus[i0:i0 + m, ch] += g * y[:m]


def pan_gains(pan: float) -> tuple:
    angle = (pan + 1.0) * np.pi / 4.0
    return math.cos(angle), math.sin(angle)


def render_notes(events: list, synth, n: int, pan, rng: np.random.Generator) -> np.ndarray:
    bus = np.zeros((n, 2))
    for t, m, v, d, *flags in events:
        y = synth(hz(m), v, d, rng, *flags)
        place(bus, t, y, pan_gains(pan(m)))
    return bus


def render_pad(segments: list, n: int, rng: np.random.Generator) -> np.ndarray:
    """Very quiet warm pad: four soft harmonics, two detuned voices spread left/right."""
    bus = np.zeros((n, 2))
    harmonics = np.array([1.0, 0.32, 0.14, 0.06])
    attack, release = 1.4, 1.8
    for t0, t1, name in segments:
        length = int((t1 - t0 + release) * SR)
        t = np.arange(length) / SR
        env = np.ones(length)
        a = int(attack * SR)
        env[:a] = 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
        r0 = int((t1 - t0) * SR)
        r = length - r0
        env[r0:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(r) / r)
        notes = CHORDS[name].pad
        for m in notes:
            for side, sign in ((0, -1.0), (1, 1.0)):
                f = hz(m) * 2.0 ** ((sign * 4.0 + rng.normal(0.0, 0.8)) / 1200.0)
                phases = rng.uniform(0.0, TAU, len(harmonics))
                y = sum(h * np.sin(TAU * f * (i + 1) * t + phases[i]) for i, h in enumerate(harmonics))
                lfo = 1.0 + 0.12 * np.sin(TAU * (0.11 + 0.05 * rng.random()) * t + rng.uniform(0.0, TAU))
                place(bus, t0, y * env * lfo / len(notes), (1.0, 0.0) if side == 0 else (0.0, 1.0))
    return bus


# --------------------------------------------------------------------------------------------
# DSP helpers (numpy only; filters are zero-phase FFT masks)
# --------------------------------------------------------------------------------------------

def lowpass(f, fc, order=2):
    return 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))


def highpass(f, fc, order=2):
    ratio = fc / np.maximum(f, 1e-9)
    return np.where(f > 0, 1.0 / np.sqrt(1.0 + ratio ** (2 * order)), 0.0)


def bell(f, fc, gain_db, octaves):
    x = np.log2(np.maximum(f, 1.0) / fc) / octaves
    return 10.0 ** (gain_db / 20.0 * np.exp(-0.5 * x * x))


def band(f, fc, octaves):
    x = np.log2(np.maximum(f, 1.0) / fc) / octaves
    return np.exp(-0.5 * x * x)


def fft_filter(x: np.ndarray, response) -> np.ndarray:
    n = x.shape[0]
    spectrum = np.fft.rfft(x, axis=0)
    gain = response(np.fft.rfftfreq(n, 1.0 / SR))
    spectrum *= gain[:, None] if x.ndim == 2 else gain
    return np.fft.irfft(spectrum, n=n, axis=0)


def fast_size(n: int) -> int:
    """Smallest 2^a 3^b 5^c >= n (fast FFT length)."""
    best, p2 = None, 1
    while p2 < 2 * n:
        p3 = p2
        while p3 < 2 * n:
            p5 = p3
            while p5 < 2 * n:
                if p5 >= n and (best is None or p5 < best):
                    best = p5
                p5 *= 5
            p3 *= 3
        p2 *= 2
    return best


def box_smooth(x: np.ndarray, width: int) -> np.ndarray:
    if width <= 1:
        return x
    c = np.concatenate(([0.0], np.cumsum(x)))
    idx = np.arange(len(x))
    lo = np.clip(idx - width // 2, 0, len(x))
    hi = np.clip(idx - width // 2 + width, 0, len(x))
    return (c[hi] - c[lo]) / (hi - lo)


def automation(plan: list, n: int, bar: float, key: str, smooth: float) -> np.ndarray:
    env = np.zeros(n)
    nb = int(round(bar * SR))
    for b in plan:
        value = getattr(b, key)
        a0, a1 = value if isinstance(value, tuple) else (value, value)
        i0, i1 = b.index * nb, min(n, (b.index + 1) * nb)
        env[i0:i1] = np.linspace(a0, a1, i1 - i0, endpoint=False)
    return box_smooth(env, int(smooth * SR))


def make_reverb_ir(rng: np.random.Generator, seconds: float = 2.8, predelay: float = 0.018) -> np.ndarray:
    """Synthetic stereo room: decorrelated noise, faster decay in the highs, sparse early reflections."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    f = np.fft.rfftfreq(n, 1.0 / SR)
    lo_mask = 1.0 / (1.0 + (f / 500.0) ** 4)
    hi_mask = 1.0 - 1.0 / (1.0 + (f / 3000.0) ** 4)
    mid_mask = np.clip(1.0 - lo_mask - hi_mask, 0.0, 1.0)
    bands = ((lo_mask, 2.3), (mid_mask, 1.9), (hi_mask * lowpass(f, 7000.0, 2), 0.9))
    shift = int(predelay * SR)
    ir = np.zeros((n + shift, 2))
    for ch in range(2):
        noise = np.fft.rfft(rng.standard_normal(n))
        tail = sum(np.fft.irfft(noise * mask, n) * np.exp(-6.91 * t / t60) for mask, t60 in bands)
        tail *= 1.0 - np.exp(-t / 0.02)                       # diffuse build-up
        for _ in range(7):                                    # early reflections
            i = int(rng.uniform(0.004, 0.07) * SR)
            tail[i] += rng.uniform(-1.0, 1.0) * 6.0 * np.std(tail[: int(0.1 * SR)])
        ir[shift:, ch] = tail
    return ir / np.sqrt(np.sum(ir ** 2, axis=0) + 1e-30)


# --------------------------------------------------------------------------------------------
# Loudness (ITU-R BS.1770-4) and true peak
# --------------------------------------------------------------------------------------------

def k_weighting(f: np.ndarray) -> np.ndarray:
    """Magnitude of the BS.1770 K-weighting filter (pre-filter shelf x RLB high-pass) at SR."""
    z = np.exp(-1j * TAU * f / SR)

    def biquad(b, a):
        return np.abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))

    gain_db, q, fc = 3.99984385397, 0.7071752369554193, 1681.9744509555319
    big_a = 10.0 ** (gain_db / 40.0)
    w0 = TAU * fc / SR
    alpha, cw, sa = math.sin(w0) / (2 * q), math.cos(w0), math.sqrt(big_a)
    shelf = biquad(
        (big_a * ((big_a + 1) + (big_a - 1) * cw + 2 * sa * alpha), -2 * big_a * ((big_a - 1) + (big_a + 1) * cw),
         big_a * ((big_a + 1) + (big_a - 1) * cw - 2 * sa * alpha)),
        ((big_a + 1) - (big_a - 1) * cw + 2 * sa * alpha, 2 * ((big_a - 1) - (big_a + 1) * cw),
         (big_a + 1) - (big_a - 1) * cw - 2 * sa * alpha))
    q, fc = 0.5003270373253953, 38.13547087613982
    w0 = TAU * fc / SR
    alpha, cw = math.sin(w0) / (2 * q), math.cos(w0)
    high = biquad(((1 + cw) / 2, -(1 + cw), (1 + cw) / 2), (1 + alpha, -2 * cw, 1 - alpha))
    return shelf * high


def integrated_loudness(x: np.ndarray) -> float:
    y = fft_filter(x, k_weighting)
    block, step = int(0.4 * SR), int(0.1 * SR)
    c = np.vstack([np.zeros((1, 2)), np.cumsum(y * y, axis=0)])
    starts = np.arange(0, len(y) - block + 1, step)
    z = ((c[starts + block] - c[starts]) / block).sum(axis=1)
    loud = -0.691 + 10 * np.log10(np.maximum(z, 1e-30))
    gated = z[loud > -70.0]
    if gated.size == 0:
        return -math.inf
    relative = -0.691 + 10 * np.log10(gated.mean()) - 10.0
    final = z[(loud > -70.0) & (loud > relative)]
    return float(-0.691 + 10 * np.log10(final.mean()))


def true_peak_db(x: np.ndarray) -> float:
    """4x oversampled peak (windowed-sinc polyphase interpolation), in dBTP."""
    factor, half = 4, 16
    m = np.arange(-half * factor, half * factor + 1)
    h = np.sinc(m / factor) * np.kaiser(len(m), 8.0)
    size = fast_size(x.shape[0] + 2 * half + 1)
    peak = 0.0
    for ch in range(x.shape[1]):
        spectrum = np.fft.rfft(x[:, ch], size)
        for phase in range(factor):
            g = h[phase::factor]
            g = g / g.sum()
            y = np.fft.irfft(spectrum * np.fft.rfft(g, size), size)
            peak = max(peak, float(np.max(np.abs(y))))
    return 20 * math.log10(max(peak, 1e-12))


def sliding_min(a: np.ndarray, width: int) -> np.ndarray:
    r, span = a.copy(), 1
    while span < width:
        s = min(span, width - span)
        r[:-s] = np.minimum(r[:-s], r[s:])
        span += s
    out = np.empty_like(a)
    shift = width // 2
    out[shift:] = r[: len(a) - shift]
    out[:shift] = r[0]
    return out


def compress(x: np.ndarray, threshold_db: float, ratio: float, attack: float, release: float,
             knee_db: float = 6.0, block: int = 32) -> np.ndarray:
    """Soft-knee, stereo-linked peak compressor. The detector and the attack/release smoothing run
    at a decimated rate (one value per `block` samples) and the gain curve is applied with a
    look-ahead equal to the attack time, so plucked transients are caught without a click."""
    n = x.shape[0]
    nb = -(-n // block)
    peak = np.zeros(nb * block)
    peak[:n] = np.max(np.abs(x), axis=1)
    level = 20 * np.log10(np.maximum(peak.reshape(nb, block).max(axis=1), 1e-9))
    over = level - threshold_db
    slope = 1.0 - 1.0 / ratio
    want = np.where(over <= -knee_db / 2, 0.0,
                    np.where(over >= knee_db / 2, slope * over, slope * (over + knee_db / 2) ** 2 / (2 * knee_db)))
    rate = SR / block
    a_coef, r_coef = math.exp(-1.0 / (attack * rate)), math.exp(-1.0 / (release * rate))
    reduction = np.empty(nb)
    state = 0.0
    for i, target in enumerate(want.tolist()):
        coef = a_coef if target > state else r_coef
        state = target + coef * (state - target)
        reduction[i] = state
    ahead = max(1, int(round(attack * rate)))
    reduction = np.concatenate((reduction[ahead:], np.zeros(ahead)))
    centres = (np.arange(nb) + 0.5) * block
    gain_db = np.interp(np.arange(n), centres, -reduction)
    return x * (10.0 ** (gain_db / 20.0))[:, None]


def peak_limit(x: np.ndarray, ceiling_db: float) -> tuple:
    """Stereo-linked look-ahead peak limiter (offline, zero-latency).
    Returns (signal, max reduction dB, fraction of samples attenuated by more than 0.1 dB)."""
    ceiling = db(ceiling_db)
    need = np.minimum(1.0, ceiling / np.maximum(np.max(np.abs(x), axis=1), 1e-12))
    if need.min() >= 1.0:
        return x, 0.0, 0.0
    w = int(0.008 * SR)
    gain = box_smooth(sliding_min(need, 2 * w + 1), w)
    return x * gain[:, None], float(-20 * math.log10(gain.min())), float(np.mean(gain < db(-0.1)))


# --------------------------------------------------------------------------------------------
# Mix
# --------------------------------------------------------------------------------------------

MIX_DB = {"guitar": 0.0, "bass": -4.0, "epiano": -4.0, "pad": -17.0, "swish": -24.0, "taps": -13.0, "stick": -6.0}
SEND = {"guitar": 0.55, "bass": 0.0, "epiano": 0.65, "pad": 0.75, "swish": 0.2, "taps": 0.25, "stick": 0.3}
WET_DB = -9.0


def guitar_eq(f):
    return (highpass(f, 70.0, 2) * lowpass(f, 5000.0, 2)
            * bell(f, 110.0, 2.5, 0.6) * bell(f, 220.0, 1.5, 0.5) * bell(f, 2600.0, 1.0, 0.5) * bell(f, 400.0, -1.5, 0.7))


def epiano_eq(f):
    return highpass(f, 90.0, 2) * lowpass(f, 4200.0, 2) * bell(f, 300.0, -1.0, 0.8)


def bass_eq(f):
    return highpass(f, 38.0, 2) * lowpass(f, 1100.0, 2)


def pad_eq(f):
    return highpass(f, 110.0, 2) * lowpass(f, 2000.0, 2)


def perc_eq(f):
    return highpass(f, 120.0, 2) * lowpass(f, 5000.0, 3)


def master_eq(f):
    return highpass(f, 28.0, 2) * lowpass(f, 8500.0, 3) * bell(f, 320.0, -1.0, 0.8)


def wet_eq(f):
    return highpass(f, 180.0, 2) * lowpass(f, 5000.0, 2)


def loudness_of(x: np.ndarray) -> float:
    return integrated_loudness(x) if np.any(x) else -math.inf


def compose(tl: Timeline, out_path: Path) -> dict:
    t_start = time.perf_counter()
    n = int(round(tl.duration * SR))
    bar = tl.bar
    plan = build_plan(tl)
    print_chart(tl, plan)

    rng_guitar, rng_bass, rng_ep, rng_pad, rng_perc, rng_noise, rng_ir, rng_dither = (
        np.random.default_rng(s) for s in np.random.SeedSequence(SEED).spawn(8))

    master = np.zeros((n, 2))
    send = np.zeros(n)
    groove = slice(int(plan_index(plan, "groove") * bar * SR), int((plan_index(plan, "groove") + 20) * bar * SR))
    stems = {}

    def mix(name, bus, eq):
        nonlocal master, send
        bus = fft_filter(bus, eq) * db(MIX_DB[name])
        stems[name] = loudness_of(bus[groove])
        master += bus
        send += bus.mean(axis=1) * SEND[name]

    # guitar slightly left, e-piano slightly right, bass centre
    guitar = render_notes(guitar_events(plan, bar, rng_guitar), nylon_tone, n, lambda m: -0.15 - 0.002 * (m - 57), rng_guitar)
    mix("guitar", compress(guitar, -6.0, 2.5, 0.002, 0.15), guitar_eq)
    del guitar
    mix("bass", render_notes(bass_events(plan, bar, rng_bass), bass_tone, n, lambda m: 0.0, rng_bass), bass_eq)
    mix("epiano", tremolo(render_notes(epiano_events(plan, bar, rng_ep), epiano_tone, n,
                                       lambda m: 0.25 + 0.005 * (m - 64), rng_ep)), epiano_eq)
    pad = render_pad(pad_segments(plan, bar), n, rng_pad) * automation(plan, n, bar, "pad", 2.0)[:, None]
    mix("pad", pad, pad_eq)
    del pad

    swishes, taps, sticks = percussion_events(plan, bar, rng_perc)
    swish_bus, tap_bus, stick_bus = brushes(plan, bar, n, swishes, taps, sticks, rng_noise)
    mix("swish", swish_bus, perc_eq)
    mix("taps", tap_bus, perc_eq)
    mix("stick", stick_bus, perc_eq)
    del swish_bus, tap_bus, stick_bus

    # convolution reverb: mono send -> decorrelated stereo return
    ir = make_reverb_ir(rng_ir)
    size = fast_size(n + ir.shape[0] - 1)
    send_spectrum = np.fft.rfft(send, size)
    wet = np.stack([np.fft.irfft(send_spectrum * np.fft.rfft(ir[:, ch], size), size)[:n] for ch in range(2)], axis=1)
    del send_spectrum
    wet = fft_filter(wet, wet_eq) * db(WET_DB)
    stems["reverb"] = loudness_of(wet[groove])
    master += wet
    del wet

    master = fft_filter(master, master_eq)
    gate = fades(n, tl.duration)
    master *= gate[:, None]

    # gentle glue compression that only reaches the plucked attacks, then loudness normalisation
    # and a safety limiter only if the true-peak aim is still exceeded
    master *= db(TARGET_LUFS - integrated_loudness(master))
    master = compress(master, -10.0, 2.0, 0.003, 0.2)
    limited, limited_share, peaks = 0.0, 0.0, []
    for _ in range(4):
        master *= db(TARGET_LUFS - integrated_loudness(master))
        peaks.append(true_peak_db(master))
        if peaks[-1] <= TRUE_PEAK_AIM:
            break
        master, reduction, active = peak_limit(master, TRUE_PEAK_AIM - 0.4)
        limited, limited_share = max(limited, reduction), max(limited_share, active)
    master -= master.mean(axis=0) * gate[:, None] / max(gate.mean(), 1e-12)   # no DC offset

    # 16-bit with gated TPDF dither (exact digital silence where the fades are at zero)
    dither = (rng_dither.random((n, 2)) - rng_dither.random((n, 2))) * (gate > 0)[:, None]
    pcm = np.clip(np.round(master * 32767.0 + dither), -32768, 32767).astype("<i2")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SR)
        wav.writeframes(pcm.tobytes())
    elapsed = time.perf_counter() - t_start

    final = pcm.astype(np.float64) / 32768.0
    return {
        "frames": n,
        "elapsed": elapsed,
        "lufs": integrated_loudness(final),
        "true_peak": true_peak_db(final),
        "limiter_db": limited,
        "limiter_share": limited_share,
        "peaks": peaks,
        "dc": final.mean(axis=0),
        "stems": stems,
        "chapters": [(ch.id, ch.start_bar * bar, ch.end_bar * bar, rms_db(final[int(ch.start_bar * bar * SR):int(ch.end_bar * bar * SR)]))
                     for ch in tl.chapters],
        "tail_zeros": trailing_zeros(pcm),
        "sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
    }


def plan_index(plan: list, role: str) -> int:
    return next(b.index for b in plan if b.role == role)


def tremolo(bus: np.ndarray, rate: float = 3.1, depth: float = 0.07) -> np.ndarray:
    """Slow, shallow tremolo with opposite phase per side (a gentle auto-pan)."""
    t = np.arange(bus.shape[0]) / SR
    lfo = np.sin(TAU * rate * t)
    bus[:, 0] *= 1.0 - depth * (0.5 + 0.5 * lfo)
    bus[:, 1] *= 1.0 - depth * (0.5 - 0.5 * lfo)
    return bus


def brushes(plan, bar, n, swishes, taps, sticks, rng) -> tuple:
    """Brush swish (band-limited noise, slow envelopes), brush taps (short noise bursts with a
    little drum body) and side-stick clicks."""
    f = np.fft.rfftfreq(n, 1.0 / SR)
    shape = band(f, 2200.0, 0.9) + 0.25 * band(f, 700.0, 0.8)
    a = np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) * shape, n)
    b = np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) * shape, n)
    noise = np.stack([a, 0.6 * a + 0.8 * b], axis=1)
    noise /= np.std(noise)
    del a, b

    level = automation(plan, n, bar, "swish", 0.4)
    env = 0.3 * level
    rise, fall = int(0.42 * SR), int(0.7 * SR)
    rise_shape = 0.5 - 0.5 * np.cos(np.pi * np.arange(rise) / rise)
    fall_shape = np.exp(-np.arange(fall) / (0.17 * SR))
    for t, v in swishes:
        peak = int(t * SR)
        amount = v * level[min(peak, n - 1)]
        lo = max(0, peak - rise)
        env[lo:peak] += amount * rise_shape[rise - (peak - lo):]
        hi = min(n, peak + fall)
        env[peak:hi] += amount * fall_shape[: hi - peak]
    swish = noise * env[:, None] * np.array(pan_gains(0.15))
    del noise, env

    tap_noise = np.fft.irfft(np.fft.rfft(rng.standard_normal(n)) * band(f, 3000.0, 0.7), n)
    tap_noise /= np.std(tap_noise)
    tap_env = np.zeros(n)
    body = np.zeros(n)
    length = int(0.2 * SR)
    tt = np.arange(length) / SR
    for t, v, accent in taps:
        i0 = int(t * SR)
        m = min(length, n - i0)
        if m <= 0:
            continue
        decay = 0.045 if accent else 0.028
        burst = v * np.exp(-tt / decay) * np.minimum(1.0, tt / 0.003)
        tap_env[i0:i0 + m] += burst[:m]
        body[i0:i0 + m] += 0.25 * v * np.sin(TAU * 185.0 * tt[:m]) * np.exp(-tt[:m] / 0.035)
    tap = (tap_noise * tap_env + body)[:, None] * np.array(pan_gains(0.1))
    del tap_noise, tap_env, body

    stick = np.zeros((n, 2))
    for t, v in sticks:
        place(stick, t, side_stick(v, rng), pan_gains(-0.2))
    return swish, tap, stick


def fades(n: int, duration: float) -> np.ndarray:
    t = np.arange(n) / SR
    gain = np.ones(n)
    fade_in = t < FADE_IN
    gain[fade_in] = np.sin(0.5 * np.pi * t[fade_in] / FADE_IN) ** 2
    end = duration - SILENT_TAIL
    start = end - FADE_OUT
    out = (t >= start) & (t < end)
    gain[out] = np.cos(0.5 * np.pi * (t[out] - start) / FADE_OUT) ** 2
    gain[t >= end] = 0.0
    return gain


def rms_db(x: np.ndarray) -> float:
    value = math.sqrt(float(np.mean(x * x))) if x.size else 0.0
    return 20 * math.log10(value) if value > 0 else -math.inf


def trailing_zeros(pcm: np.ndarray) -> int:
    nonzero = np.flatnonzero(np.any(pcm != 0, axis=1))
    return pcm.shape[0] - (int(nonzero[-1]) + 1 if nonzero.size else 0)


def print_chart(tl: Timeline, plan: list) -> None:
    for ch in tl.chapters:
        cells = []
        for b in plan[ch.start_bar:ch.end_bar]:
            cells.append(b.chords[0] if b.chords[0] == b.chords[1] else f"{b.chords[0]}>{b.chords[1]}")
        print(f"bars {ch.start_bar:2d}-{ch.end_bar - 1:2d}  {ch.id:<15} {ROLES[ch.id]:<9} | " + " | ".join(cells) + " |")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--timeline", type=Path, default=TIMELINE)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()

    tl = load_timeline(args.timeline)
    print(f"timeline: {tl.duration:g} s, {tl.bpm:g} BPM, {tl.n_bars} bars of {tl.bar:g} s; all chapter boundaries on bar lines")
    report = compose(tl, args.out)

    print("\nstem loudness in the first 20 groove bars (LUFS, before master normalisation):")
    for name, value in report["stems"].items():
        print(f"  {name:<7} {value:7.1f}")
    print("\nper-chapter RMS (dBFS, both channels):")
    for cid, start, end, value in report["chapters"]:
        print(f"  {cid:<15} {start:6.1f}-{end:6.1f} s  {value:6.1f}")
    print(f"\nwrote {args.out}")
    print(f"  frames {report['frames']} ({report['frames'] / SR:.3f} s), 44.1 kHz, stereo, 16-bit PCM")
    print(f"  integrated loudness {report['lufs']:.2f} LUFS, true peak {report['true_peak']:.2f} dBTP"
          f" (pre-limiter true peaks {', '.join(f'{p:.2f}' for p in report['peaks'])} dBTP;"
          f" limiter max reduction {report['limiter_db']:.2f} dB on {100 * report['limiter_share']:.2f}% of samples)")
    print(f"  DC offset L {report['dc'][0]:.2e}, R {report['dc'][1]:.2e}; trailing digital silence {report['tail_zeros']} frames")
    print(f"  sha256 {report['sha256']}")
    print(f"  render time {report['elapsed']:.1f} s")
    if report["true_peak"] > TRUE_PEAK_LIMIT:
        raise SystemExit(f"true peak {report['true_peak']:.2f} dBTP exceeds {TRUE_PEAK_LIMIT} dBTP")


if __name__ == "__main__":
    main()
