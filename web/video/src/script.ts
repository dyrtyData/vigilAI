import { emphasisRuns, fillName, overviewChapters, overviewFilm, type OverviewBeat, type OverviewChapter } from "../../src/lib/project-overview.ts";

export { emphasisRuns, fillName, overviewChapters, overviewFilm };
export type { OverviewBeat, OverviewChapter };

export const FPS = overviewFilm.fps;
export const DURATION_FRAMES = Math.round(overviewFilm.durationSeconds * FPS);

export function chapter(id: string): OverviewChapter {
  const found = overviewChapters.find(item => item.id === id);
  if (!found) throw new Error(`Unknown chapter ${id}`);
  return found;
}

export function beat(chapterId: string, beatId: string): OverviewBeat & { end: number } {
  const owner = chapter(chapterId);
  const index = owner.beats.findIndex(item => item.id === beatId);
  if (index < 0) throw new Error(`Unknown beat ${chapterId}.${beatId}`);
  const next = owner.beats[index + 1];
  return { ...owner.beats[index], end: next ? next.at : owner.end };
}

export function chapterAt(seconds: number) {
  return overviewChapters.find(item => seconds >= item.start && seconds < item.end) ?? overviewChapters[overviewChapters.length - 1];
}
