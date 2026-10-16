# Vigil AI — research landing page

A bilingual research summary in English and Brazilian Portuguese covering the study, methodology, evaluation instruments, corrected findings, and limitations. The Python package and CLI remain `vigilai`.

## Run locally

Requires Node.js 22 and pnpm.

```sh
cd web
pnpm install
pnpm dev
```

The default development address is `http://127.0.0.1:3000`. To use port 3001 instead, run `pnpm dev --port 3001`.

## Verification

```sh
pnpm build
pnpm typecheck
pnpm exec playwright test
```

Playwright requires Chromium (`pnpm exec playwright install chromium`). By default, the test configuration starts a local server on port 3100. To test the development server already running on port 3001:

```sh
PLAYWRIGHT_PORT=3001 pnpm exec playwright test
```

The film tests play the MP4s in `public/media/`. These deliverables are included; regeneration instructions are in [video/README.md](video/README.md).

## Architecture

### Languages

- `/` serves Brazilian Portuguese by default; `/en` serves English. An internal rewrite reuses the statically generated Portuguese page, and legacy `/pt-br` links permanently redirect to `/`.
- Both versions are statically rendered, with the correct document language, localized titles/descriptions and language-alternate metadata. Preview `noindex` settings are unchanged.
- The header language links preserve the current section and query parameters during normal navigation. Direct links work without JavaScript; the selected language persists in the URL on reload.
- Translation data lives in `src/lib/locales/pt-br.ts`, with locale helpers in `src/lib/i18n.ts`. Keep English documentation and source identifiers unchanged.
- The benchmark question-language toggle is independent of the site language. Source quotations, model names, article numbers, numerical results and evidence links are preserved.
- The Portuguese page includes translated player controls, chapter navigation and the complete HTML transcript. The existing video and poster still contain English on-screen text, explicitly noted in the Portuguese interface. No translated video has been rendered.
- `tests/i18n.spec.ts` checks translation coverage, numerical parity, server rendering without JavaScript, language navigation, mobile layout and Portuguese playback controls.

### Application

- Next.js App Router, TypeScript, and Tailwind CSS.
- A button built with the shadcn/ui composition pattern (Radix Slot + CVA), styled for this identity. `components.json` supports adding components from the official registry.
- Webpack builds: Turbopack could not open an internal CSS-process port in the original development environment.
- Motion powers the scroll-driven study narrative. Magic UI is not installed.
- Local Manrope and Instrument Serif fonts; builds do not download fonts from Google.
- Shared brand and research content in `src/lib/content.ts`.
- Five-benchmark explorer with keyboard navigation and explicitly illustrative Portuguese/English prompts.
- No forms, accounts, or model evaluations in the browser. Calls to action link to the research and source code.
- The preview uses `noindex`. A public deployment requires final domain, canonical, social metadata, and indexing configuration.
- `researchRevision` pins evidence to `36d00305656ff41343c4f86e818c35732e6e2e9e`. Displayed figures are transcribed from that revision's reports; this site does not recompute them or run new evaluations.

Technical references consulted on 2026-10-08:

- https://ui.shadcn.com/docs/installation/next
- https://motion.dev/docs/react-scroll-animations
- https://magicui.design/docs/installation

## Brand identity

**Vigil AI** is the working name. The descriptor is “Rights-based evaluation of language models.” The editorial identity uses ivory, deep green, and olive, with a globe-based mark.

The name remains configurable in the website and editable video source. Changing it in an exported video requires rendering new deliverables. No domain has been configured for this site.

## Research film

The hero displays the film poster (`#overview`). The film runs **3 minutes 12 seconds**, at 1920 × 1080 and 30 fps, with original instrumental music and no voiceover.

Selecting the poster opens a viewport-filling dialog containing the video, timeline, and chapter navigation. Closing the dialog or pressing Escape pauses playback, restores page scrolling, and returns focus to the hero button. Native fullscreen is optional; the dialog also works without that API. The transcript remains available on the page below the abstract.

- Poster-first loading (`preload="none"`); no video download or autoplay before interaction.
- Keyboard-accessible playback, volume, replay, seeking, and chapter controls.
- Inline mobile playback (`playsInline`). Viewports up to 900 px or data-saving connections use the 720p rendition.
- `src/lib/project-overview.ts` is the shared source for on-screen text, timing, chapter navigation, and the HTML transcript.
- With `prefers-reduced-motion`, the transcript opens by default. Playback still requires an explicit action.
- `public/media/` contains the full MP4, 720p MP4, silent MP4, and WebP poster. The silent version has keyframes every 0.5 seconds for potential scroll-controlled use; the current page does not use that mode.
- The film presents documented findings, current limitations, and research credits. It contains no internal planning segment.
- Editable Remotion source, rendering commands, the claim-to-source table, and music provenance are documented in [video/README.md](video/README.md). Remotion has its own package under `video/` and is not part of the website runtime.

## Scroll-driven study narrative

The separate Motion section retains three chapters:

| Chapter | Scroll range | Content |
| --- | --- | --- |
| Evaluation framework | 0–33% | A model connects to the 30 COMPL-AI tasks. |
| Brazil-specific instruments | 33–66% | Portuguese/English conditions and five Brazilian instruments appear. |
| Measurement validation | 66–100% | Responses, scoring rules, and legal mappings connect to the measurement audit. |

This section does not synchronize video or audio. It preserves normal scrolling, uses a sticky layout on desktop, and switches to compact button navigation on mobile or with reduced motion. Essential benchmark information is also available outside the animation.

## Evidence and editorial rules

The root README retracts the approximately 0.45 AI-disclosure gap on 2026-07-26. The pinned results also document corrections to contestation, explanation, impact-assessment, and bias scoring. **Do not present first-iteration charts, percentages, PDFs, or scorecards as current findings.**

- The framework retains 30 upstream tasks and adds five Brazilian instruments. Retaining tasks does not mean their configuration is unchanged.
- English/Portuguese coverage is not evidence of linguistic equivalence.
- Top 25% at the Global South AI Safety Hackathon is team-reported and recorded in the root README. The official project page confirms the project, participants, and event; a public ranking was not independently verified there. Do not call the project a winner or infer an exact placement.
- COMPL-AI, ETH Zurich, INSAIT, and LatticeFlow AI receive upstream attribution, not endorsement or partnership claims.
- Explorer prompts are illustrative examples, not scored samples or responses from a live backend.
- Do not claim “first” or “only” without supporting prior-art research.
- A shared scorer does not causally isolate language or jurisdiction; scenario construction and coverage also differ.
- Response scores are not legal certification. An HTML report does not establish complete fulfillment of Article 28.
- Article references follow the project's version-specific mapping of PL 2338/2023. The site links to the official legislative record; this is not a new legal review.

Sources:

- [Root README and retraction notice](../README.md).
- [Versioned corrected results](https://github.com/dyrtyData/vigilAI/blob/36d00305656ff41343c4f86e818c35732e6e2e9e/reports/RESULTS.md).
- [Hackathon project page](https://apartresearch.com/sprints/projects/vigilai-l3xg).
- [Official legislative record](https://www.camara.leg.br/proposicoesWeb/fichadetramitacao/?idProposicao=2487262).

## Deployment checks

Confirm the domain, legal-source version, recognition attribution, canonical and social metadata, and indexing settings before public deployment. Review the film and audition its soundtrack. Check Remotion licence eligibility for the organization using the video package.

The landing cites the corrected two-model evidence snapshot; historical HTML scorecards are not included. Local development and Git pushes do not deploy the site.
