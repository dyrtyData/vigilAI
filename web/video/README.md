# Project-overview film (Remotion)

Editable source for the 3 min 12 s motion-graphics overview opened from the website’s **hero**. It is a separate package so that Remotion never enters the website runtime: the site only serves the encoded files in `../public/media/` through a native `<video>` element. The film covers the documented findings, current limitations and research credits; the internal next-steps segment has been removed.

- **Script and timing:** `../src/lib/project-overview.ts` — one module drives the film’s on-screen text and beat timings, the website’s chapter navigation and its HTML transcript. Edit it there, then run `pnpm script-doc` to regenerate [`docs/script.md`](docs/script.md).
- **Evidence:** [`docs/claims.md`](docs/claims.md) maps every number and substantive claim to a pinned source (evidence snapshot `36d0030`). `pnpm verify` fails on an undocumented or unused claim ID.
- **Design tokens:** `src/theme.ts`. Every colour is taken from `../src/app/globals.css`, and `pnpm verify` fails if one drifts. Fonts are the site’s own local Manrope and Instrument Serif files (`pnpm fonts` copies them from `../node_modules/@fontsource*`).
- **Music:** original composition synthesized by `music/compose.py`; see [`music/README.md`](music/README.md).

## Requirements

Node 22, pnpm, ffmpeg with libx264, and [uv](https://docs.astral.sh/uv/) (it fetches Python 3.12 with numpy for the music and Pillow for the WebP poster). The site’s dependencies must be installed first (`cd .. && pnpm install`) because the fonts are copied from them. Remotion downloads its headless Chrome on the first render.

## Commands

Run from `web/video/`:

```sh
pnpm install            # Remotion, React, TypeScript (esbuild's build script is approved in pnpm-workspace.yaml)
pnpm fonts              # copy the site's local font files into public/fonts/
pnpm verify             # tokens ↔ globals.css, timeline, claim coverage, glyph coverage, word count
pnpm music              # export music/timeline.json, then synthesize public/audio/soundtrack.wav
pnpm studio             # interactive preview in Remotion Studio (with soundtrack)
pnpm render             # silent H.264 master: out/project-overview-master.mp4 (1920×1080, 30 fps, CRF 12)
pnpm poster             # poster still: out/project-overview-poster.png
pnpm export             # encode ../public/media/* (muxes the soundtrack WAV; see below)
pnpm media              # all of the above in order
```

`pnpm export` writes:

| File | Content |
| --- | --- |
| `project-overview.mp4` | 1920×1080, 30 fps, H.264 High (CRF 20) + AAC 192 kb/s 48 kHz stereo, fast-start |
| `project-overview-720p.mp4` | 1280×720, H.264 (CRF 22) + AAC 128 kb/s, fast-start |
| `project-overview-silent.mp4` | 1280×720, no audio, keyframe every 0.5 s for optional scroll-controlled seeking |
| `project-overview-poster.webp` | 1920×1080 poster frame (title, research question, layered model) |

The master is rendered without audio and the soundtrack is encoded once, directly from the lossless WAV, into each rendition. If `public/audio/soundtrack.wav` is missing, `pnpm export` warns and encodes the renditions without sound.

## Changing the project name

“Vigil AI” is a working name. The film has no logo; the name is text. Change `brand.name` in `../src/lib/content.ts` (it updates the film, the poster and the website), or override it for a single render:

```sh
pnpm exec remotion render src/index.ts ProjectOverview out/project-overview-master.mp4 --codec h264 --crf 12 --pixel-format yuv420p --muted --props='{"withAudio":false,"projectName":"New Name"}'
pnpm exec remotion still src/index.ts Poster out/project-overview-poster.png --props='{"projectName":"New Name"}'
```

## Structure

```
src/
  Root.tsx              compositions: ProjectOverview (5,760 frames) and Poster (still)
  ProjectOverview.tsx   background, chapter sequences, persistent chrome, soundtrack
  theme.ts  fonts.ts    design tokens and local font loading
  time.tsx              frame-based timing helpers (no timers, no randomness)
  components/           primitives (text with serif emphasis, chips, badges, connectors) and chrome
  scenes/s1 … s8        one file per chapter
scripts/                fonts, verify, script doc, export, review stills and contact sheets
docs/                   script.md (generated) and claims.md
music/                  compose.py, timeline.json, README.md
```

Every animation is a pure function of the frame number. Charts place data points directly at their sourced values and reveal them by opacity; no value is animated through invented intermediate numbers.

## Licensing notes

- **Remotion** is not MIT-licensed. Its licence allows free use by individuals, not-for-profit organizations and for-profit organizations with up to three employees; larger companies need a company licence (<https://github.com/remotion-dev/remotion/blob/main/LICENSE.md>, checked 2026-10-09). Confirm eligibility before using this package commercially.
- **Fonts:** Manrope and Instrument Serif are distributed under the SIL Open Font License through the site’s existing `@fontsource` packages.
- **Music:** see `music/README.md`.

## Current status-cut verification (2026-10-09)

- Removed the next-steps segment; limitations lead directly into research credits. Duration: **192 seconds / 5,760 frames** in all three MP4s, confirmed with ffprobe. The hero design is unchanged.
- The shared timeline, transcript, poster and instrumental ending were updated together. The full and 720p files retain AAC audio; the silent rendition has no audio stream.
- `pnpm verify`: 38 claims, 408 narrative words; video TypeScript check passes. Website production build and all 11 Chromium tests pass, including duration matching, transcript exclusions and modal close/pause behavior.
- Reviewed exported frames at 3:00 (limitations) and 3:10 (credits). The soundtrack has not been auditioned in this pass; physical mobile devices were not tested.

## Original-cut verification (2026-10-09, superseded 198-second export)

- **Media:** all three MP4s are exactly 198.000 s at 30 fps (5,940 frames), H.264 High, `moov` atom first. `project-overview.mp4` 1920×1080, 20.4 MB, AAC 48 kHz stereo at −18.0 LUFS; `project-overview-720p.mp4` 1280×720, 12.4 MB; `project-overview-silent.mp4` 1280×720, 18.0 MB, keyframes every 0.5 s; poster 1920×1080 WebP, 53 KB. The master renders in about 40 s on Apple silicon.
- **Frames:** review stills of every beat and chapter transition were inspected at 1920 px and at a 390 px player width (essential copy ≈ 11–15 CSS px). Fixed during review: text collisions, rail highlight timing, label overflow, unsupported glyphs (→ is drawn as SVG instead), content fading before the ivory/dark background crossfades.
- **Source checks:** `pnpm verify` passes (tokens, timeline, 40 claims, glyph coverage, 429 narrative words); `tsc --noEmit` passes.
- **Website:** `next build --webpack` and `tsc --noEmit` pass. Playwright: 10/10 in Chromium (the 4 existing tests plus 6 film tests covering poster-first loading, no autoplay, play/pause, chapter seek, mute/volume, replay, keyboard, transcript, reduced motion and the 390 px layout) and the 6 film tests in WebKit (Desktop Safari and iPhone 13 emulation).
- **Not verified:** physical iOS/Android devices, and listening to the soundtrack (see `music/README.md`).
