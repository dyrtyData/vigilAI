// Consistency checks for the film source. Run with `pnpm verify`.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { overviewChapters, overviewFilm, plainText } from "../../src/lib/project-overview.ts";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const failures: string[] = [];
const check = (ok: boolean, message: string) => { if (!ok) failures.push(message); };

// 1. Every colour token exists in the website's globals.css (the source of truth).
const css = readFileSync(join(root, "..", "src", "app", "globals.css"), "utf8").toLowerCase();
const theme = readFileSync(join(root, "src", "theme.ts"), "utf8");
for (const hex of theme.match(/#[0-9a-f]{6}(?:[0-9a-f]{2})?/gi) ?? []) check(css.includes(hex.toLowerCase()), `theme colour ${hex} not found in globals.css`);

// 2. Timeline: contiguous chapters, ordered beats, bar-aligned boundaries, exact duration.
const bar = (60 / overviewFilm.bpm) * 4;
overviewChapters.forEach((chapter, i) => {
  check(i === 0 ? chapter.start === 0 : chapter.start === overviewChapters[i - 1].end, `chapter ${chapter.id} is not contiguous`);
  check(Math.abs(chapter.start / bar - Math.round(chapter.start / bar)) < 1e-9, `chapter ${chapter.id} does not start on a bar line`);
  chapter.beats.forEach((beat, j) => {
    check(beat.at >= chapter.start && beat.at < chapter.end, `beat ${chapter.id}.${beat.id} outside its chapter`);
    if (j > 0) check(beat.at > chapter.beats[j - 1].at, `beat ${chapter.id}.${beat.id} out of order`);
  });
});
check(overviewChapters[overviewChapters.length - 1].end === overviewFilm.durationSeconds, "last chapter does not end at durationSeconds");

// 3. Claims: every referenced ID is documented, and every documented ID is used.
const claimsDoc = readFileSync(join(root, "docs", "claims.md"), "utf8");
const documented = new Set([...claimsDoc.matchAll(/^\| (C\d{2}) \|/gm)].map(match => match[1]));
const used = new Set(overviewChapters.flatMap(chapter => chapter.beats.flatMap(beat => beat.claims)));
for (const id of used) check(documented.has(id), `claim ${id} is used but not documented`);
for (const id of documented) check(used.has(id), `claim ${id} is documented but never used`);
for (const chapter of overviewChapters) for (const beat of chapter.beats) {
  const numbers = /\d\.\d{3}|\b\d{2,3}\b/.test(`${beat.text} ${beat.visual ?? ""}`);
  if (numbers && beat.id !== "title") check(beat.claims.length > 0, `beat ${chapter.id}.${beat.id} shows numbers without a claim`);
}

// 4. Film text uses only glyphs covered by the bundled font subsets (Latin, Latin Extended, Greek).
const covered = (code: number) => code <= 0x24f || (code >= 0x370 && code <= 0x3ff) || (code >= 0x2000 && code <= 0x206f) || [0x2212, 0x20ac, 0x2122].includes(code);
for (const chapter of overviewChapters) for (const beat of chapter.beats) {
  for (const text of [beat.heading ?? "", beat.text, ...(beat.items ?? [])]) {
    for (const char of text) check(covered(char.codePointAt(0)!), `glyph “${char}” in ${chapter.id}.${beat.id} is outside the font subsets`);
  }
}

// 5. Essential narrative word count (target 350–450, benchmark headings excluded).
const words = overviewChapters.flatMap(chapter => chapter.beats.flatMap(beat => [beat.id === "title" ? "" : "", beat.text, ...(beat.items ?? [])]))
  .map(text => plainText(text, "Vigil AI")).join(" ").split(/\s+/).filter(word => /[\p{L}\p{N}]/u.test(word)).length;
check(words >= 350 && words <= 450, `essential narrative has ${words} words (target 350–450)`);

if (failures.length) {
  console.error(failures.map(item => `✗ ${item}`).join("\n"));
  process.exit(1);
}
console.log(`✓ tokens, timeline (${overviewFilm.durationSeconds} s, ${overviewChapters.length} chapters), ${used.size} claims, glyph coverage, ${words} narrative words`);
