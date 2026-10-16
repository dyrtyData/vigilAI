# Soundtrack: original composition for the project-overview film

`public/audio/soundtrack.wav` is an original instrumental piece composed and synthesized for this
film by `music/compose.py`. Every sound is generated from sines, exponentials and seeded noise in
that script. No samples, recordings, soundfonts, MIDI files or loops are used.

## Composition

- **Style:** slow bossa nova blended with ambient downtempo. Restrained, so it can sit under on-screen reading.
- **Key and tempo:** D major (tonic Dmaj9), 80 BPM, 4/4. One bar is 3 s, so the 192 s film is exactly 64 bars.
- **Instruments (all synthesized):**
  - Nylon-string guitar: modal plucked-string model, slightly left.
  - Electric piano: soft 1:1 FM with a slow tremolo, slightly right.
  - Bass: sine with a little 2nd and 3rd harmonic, centred.
  - Very quiet warm pad: detuned additive voices spread left and right.
  - Brushes: band-limited noise swish plus taps, with a side-stick on the bossa clave.
  - Convolution reverb with a synthetic noise impulse response.
- **Main changes:** | Dmaj9 | Bm9 | Em9 | A13sus4→A13 |, one chord per bar.
  - When a chapter's length is not a multiple of four bars, the block is padded so it still ends on the dominant (Gmaj9 → A13 for two extra bars, Dmaj9 → Gmaj9 → A13 for three). Every chapter built on this loop therefore opens on D.

| Bars | Seconds | Chapter | Music |
|---|---|---|---|
| 0–5 | 0–15 | question | Intro: nylon guitar alone, arpeggiated maj9 voicings, soft pad swell; 1.5 s fade-in from digital silence. No percussion. |
| 5–11 | 15–33 | origin | The bass enters at bar 5. Guitar moves from arpeggios to light comping. Very soft brush swishes start at bar 7 and grow. A first electric-piano fill comes in bar 10. |
| 11–31 | 33–93 | benchmarks, design | Full but gentle bossa groove. The guitar thumb plays beats 1 and 3, with finger chords on a two-bar pattern (eighths 0, 3, 6, 10, 13, plus three deterministic variants). Brush swish (accents on 2 and 4), eighth-note taps, a quiet side-stick on the clave, a dotted-quarter/eighth root-fifth bass, and sparse electric-piano fills on the dominant bar of most 4-bar cycles. |
| 31–41 | 93–123 | disclosure | Reduced density: the same changes at 2 bars per chord. The guitar holds chords with few re-attacks and the bass plays downbeats. Only a faint swish remains, with an electric-piano dyad every 4 bars. |
| 41–54 | 123–162 | validity (dark) | Ambient downtempo in relative-minor colours at 2 bars per chord: Bm9, Gmaj7(#11), Em11, F#7(b13), Bm9, Gmaj7(#11). The texture is low electric-piano voicings, pad and long bass notes, with no rhythm section. Bars 52–53 hold the lift under "Evaluate the model. Validate the measurement.": rolled guitar, Em9 → A13sus4 → A13, and a rising piano line and swish that lead back to D. |
| 54–59 | 162–177 | implementation | A light groove returns: guitar comping, soft brushes (no side-stick) and bass. |
| 59–62 | 177–186 | limitations | The texture thins, then a plagal cadence: Gmaj9, Gm6. |
| 62–64 | 186–192 | closing | Final Dmaj9, rolled on the guitar with the electric piano, rings in the reverb. The fade reaches zero at 191.95 s; the last 50 ms (2,205 frames) are digital silence. |

The arrangement is driven by the timeline, not by hard-coded times. `compose.py` reads
`music/timeline.json` and fails if any chapter boundary or the film end is not on a bar line.
Chapters map to musical roles by id, and the dark role must match the chapter's `theme: "dark"`.
Two placements come from beat times: the lift starts in the bar that holds the `validity/message`
beat, and the final chord lands on the first bar line after the `limitations/close` beat. Both
have bar-count fallbacks. The script prints the bar-by-bar chord chart on every run.

## Regenerate

From `web/video`:

```sh
node scripts/export-timeline.ts                                         # web/src/lib/project-overview.ts -> music/timeline.json
uv run --no-project --python 3.12 --with numpy python music/compose.py  # -> public/audio/soundtrack.wav
```

`pnpm music` runs both. The only dependency is numpy; it was built and verified with
Python 3.12.12 and numpy 2.5.3. Use `--out <path>` to render somewhere else. A render takes
about 15–20 s on the authoring machine (Apple silicon).

The integrated loudness (ITU-R BS.1770-4 K-weighting and gating) and the 4× oversampled true peak
are measured inside the script. It normalises to −18 LUFS, after a gentle 2:1 glue compressor that
only reaches the plucked attacks. A look-ahead safety limiter engages only if the true peak would
exceed −2.0 dBTP. In this render it reduced at most 1.26 dB, on 0.07 % of samples. The output is
16-bit with TPDF dither, and the dither is gated off wherever the fades are at zero.

## Determinism

Every random choice (humanised timing and velocity, pattern variants, pluck positions, noise,
reverb impulse response, dither) comes from `numpy.random.SeedSequence(23382023)`. Running the
script is deterministic for the same inputs and platform. The current 192-second render has this hash:

```
sha256 906e7523355d8ba72c718ab454fa2378ba9eb4c122bbb03760f25474f9ca6d0d  soundtrack.wav
```

The same timeline, script, numpy version and platform give the same bytes. A different numpy
build or CPU architecture may change the last bits of the floating-point maths and therefore the
hash, without changing what you hear.

## Measurements (this render)

| Check | Result |
|---|---|
| Format (generator output) | pcm_s16le, 44,100 Hz, 2 channels, 8,467,200 frames = 192.000 s |
| Integrated loudness | −18.00 LUFS (script) |
| True peak | −2.39 dBTP (script) |
| DC offset | L −3.71e−10, R 3.64e−10 (script) |

Per-chapter RMS (dBFS, both channels):

| Chapter | Seconds | RMS |
|---|---|---|
| question (intro) | 0–15 | −23.7 |
| origin | 15–33 | −19.2 |
| benchmarks | 33–72 | −17.8 |
| design | 72–93 | −17.8 |
| disclosure (reduced) | 93–123 | −22.5 |
| validity (dark) | 123–162 | −22.3 |
| implementation | 162–177 | −19.0 |
| limitations / closing | 177–192 | −22.4 (digital silence from 191.95 s) |

## Rights

This is an original composition, procedurally synthesized by `music/compose.py` for this project.
It contains no third-party samples, recordings, soundfonts, MIDI files or loops. The harmony uses
common jazz/bossa chord vocabulary and quotes no existing song. Rights in the composition and the
rendered audio rest with the project owners, who may choose its licence.

## Review status

The current cut was checked through the generator's format, duration, loudness, true-peak and
per-section RMS measurements. Listening has not been verified in this editing pass. The synthesized guitar, electric piano and brushes are
approximations of the real instruments. Audition the soundtrack on speakers and headphones before
publication, especially the timbre of the guitar attacks, the bass level on small speakers, and
the balance against narration or on-screen reading.
