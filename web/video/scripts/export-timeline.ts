// Exports the film timeline (tempo, duration, chapters and beat times) to music/timeline.json, the
// only input of the soundtrack generator music/compose.py. Run from web/video:
//   node scripts/export-timeline.ts
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { overviewChapters, overviewFilm } from "../../src/lib/project-overview.ts";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const target = join(root, "music", "timeline.json");

const timeline = {
  source: "web/src/lib/project-overview.ts",
  bpm: overviewFilm.bpm,
  durationSeconds: overviewFilm.durationSeconds,
  chapters: overviewChapters.map(chapter => ({
    id: chapter.id,
    start: chapter.start,
    end: chapter.end,
    theme: chapter.theme,
    beats: chapter.beats.map(beat => ({ id: beat.id, at: beat.at })),
  })),
};

writeFileSync(target, `${JSON.stringify(timeline, null, 2)}\n`);
console.log(`timeline: ${timeline.chapters.length} chapters, ${timeline.durationSeconds} s at ${timeline.bpm} BPM -> music/timeline.json`);
