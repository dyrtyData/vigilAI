import { expect, test, type Locator } from "@playwright/test";
import { disclosureTable, overviewChapters, overviewFilm } from "../src/lib/project-overview";

const currentTime = (video: Locator) => video.evaluate((element: HTMLVideoElement) => element.currentTime);

test("the film is poster-first and never starts on its own", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/en");
  const section = page.locator("#overview");
  await expect(section.getByRole("button", { name: "Play the overview" })).toBeVisible();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await expect(page.getByRole("slider", { name: "Seek" })).not.toBeVisible();
  const video = page.locator("video");
  await expect(video).toHaveAttribute("poster", overviewFilm.media.poster);
  await expect(video).toHaveAttribute("preload", "none");
  await expect(video).toHaveAttribute("playsinline", "");
  await page.waitForTimeout(1500);
  expect(await video.evaluate((element: HTMLVideoElement) => ({ src: element.currentSrc, paused: element.paused, autoplay: element.autoplay })))
    .toEqual({ src: "", paused: true, autoplay: false });
  for (const path of Object.values(overviewFilm.media)) expect((await page.request.head(path)).ok(), path).toBe(true);
  expect(errors).toEqual([]);
});

test("plays, pauses, navigates chapters, adjusts volume and replays", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/en");
  const video = page.locator("video");
  await page.getByRole("button", { name: "Play the overview" }).click();
  await expect.poll(() => currentTime(video), { timeout: 15_000 }).toBeGreaterThan(0.5);
  expect(await video.evaluate((element: HTMLVideoElement) => element.duration)).toBeCloseTo(overviewFilm.durationSeconds, 1);
  expect(await video.evaluate((element: HTMLVideoElement) => element.currentSrc)).toContain(overviewFilm.media.full);

  await page.getByRole("button", { name: "Pause", exact: true }).click();
  await expect(page.getByRole("button", { name: "Play", exact: true })).toBeVisible();
  expect(await video.evaluate((element: HTMLVideoElement) => element.paused)).toBe(true);

  const findings = overviewChapters.find(chapter => chapter.id === "disclosure")!;
  const chapterButton = page.getByRole("button", { name: new RegExp(`Play chapter ${findings.number}`) });
  await chapterButton.click();
  await expect.poll(() => currentTime(video)).toBeGreaterThanOrEqual(findings.start);
  await expect(chapterButton).toHaveAttribute("aria-current", "true");

  await page.getByRole("button", { name: "Mute" }).click();
  expect(await video.evaluate((element: HTMLVideoElement) => element.muted)).toBe(true);
  await page.getByRole("slider", { name: "Volume" }).fill("0.4");
  expect(await video.evaluate((element: HTMLVideoElement) => ({ muted: element.muted, volume: element.volume }))).toEqual({ muted: false, volume: 0.4 });

  await page.getByRole("button", { name: "Replay from the beginning" }).click();
  await expect.poll(() => currentTime(video)).toBeLessThan(findings.start);
  expect(await video.evaluate((element: HTMLVideoElement) => element.paused)).toBe(false);
});

test("the player is operable with the keyboard", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/en");
  const video = page.locator("video");
  await page.getByRole("button", { name: "Play the overview" }).focus();
  await page.keyboard.press("Enter");
  await expect.poll(() => currentTime(video), { timeout: 15_000 }).toBeGreaterThan(0.3);

  const seek = page.getByRole("slider", { name: "Seek" });
  await seek.focus();
  await page.keyboard.press("k");
  await expect.poll(() => video.evaluate((element: HTMLVideoElement) => element.paused)).toBe(true);
  await page.keyboard.press("m");
  await expect.poll(() => video.evaluate((element: HTMLVideoElement) => element.muted)).toBe(true);

  await page.getByRole("button", { name: "Play", exact: true }).focus();
  const before = await currentTime(video);
  await page.keyboard.press("ArrowRight");
  await expect.poll(() => currentTime(video)).toBeGreaterThanOrEqual(before + 4);
  await page.keyboard.press("Space");
  await expect.poll(() => video.evaluate((element: HTMLVideoElement) => element.paused)).toBe(false);

  const chapter = page.getByRole("button", { name: /Play chapter 03/ });
  await chapter.focus();
  await page.keyboard.press("Enter");
  await expect(chapter).toHaveAttribute("aria-current", "true");
});

test("the transcript contains the complete narrative and figures", async ({ page }) => {
  await page.goto("/en");
  const transcript = page.locator("#film-transcript");
  await expect(transcript).not.toHaveAttribute("open", "");
  await transcript.locator("summary").click();
  await expect(transcript).not.toContainText("Next steps");
  await expect(transcript).not.toContainText("A report that reconciles historical claims");
  for (const chapter of overviewChapters) await expect(transcript.getByRole("heading", { level: 3, name: new RegExp(chapter.title) })).toBeVisible();
  for (const row of disclosureTable.rows) for (const cell of row) await expect(transcript).toContainText(cell);
  for (const text of ["+0.218 ± 0.030", "+0.005 ± 0.026", "It was retracted.", "Validate the measurement.", "Pedro Quezada", "not the later corrected analysis"]) {
    await expect(transcript).toContainText(text);
  }
});

test("reduced motion opens the transcript and still waits for the visitor", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/en");
  await expect(page.locator("#film-transcript")).toHaveAttribute("open", "");
  await expect(page.locator("#film-keyboard-hint")).toContainText("Reduced motion is on");
  expect(await page.locator("video").evaluate((element: HTMLVideoElement) => element.currentSrc)).toBe("");
});

test("mobile shows a full-width inline player with the web rendition", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/en");
  await page.getByRole("button", { name: "Play the overview" }).click();
  const frame = page.locator(".film-frame");
  await frame.scrollIntoViewIfNeeded();
  const box = await frame.boundingBox();
  expect(box!.width).toBeGreaterThan(330);
  expect(box!.width).toBeLessThanOrEqual(390);
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("mobile-film.png") });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const video = page.locator("video");
  await expect.poll(() => currentTime(video), { timeout: 15_000 }).toBeGreaterThan(0.3);
  expect(await video.evaluate((element: HTMLVideoElement) => element.currentSrc)).toContain(overviewFilm.media.web);
  await expect(page.getByRole("slider", { name: "Seek" })).toBeVisible();
});

test("hero opens a modal, contains focus, pauses on close and restores focus", async ({ page }, testInfo) => {
  await page.goto("/en");
  const trigger = page.getByRole("button", { name: "Play the overview" });
  await expect(page.locator(".hero").getByRole("button", { name: "Play the overview" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("hero-film.png") });
  await trigger.click();
  const dialog = page.getByRole("dialog", { name: "The research film" });
  await expect(dialog).toBeVisible();
  const video = page.locator("video");
  await expect.poll(() => currentTime(video)).toBeGreaterThan(0);
  await expect(page.getByRole("navigation", { name: "Film chapters" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Close film" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  expect(await dialog.evaluate(el => el.contains(document.activeElement))).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("film-dialog.png") });
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(trigger).toBeFocused();
  expect(await video.evaluate((el: HTMLVideoElement) => el.paused)).toBe(true);
  expect(await page.evaluate(() => document.body.style.overflow)).not.toBe("hidden");
  await trigger.click();
  await expect.poll(() => video.evaluate((el: HTMLVideoElement) => el.paused)).toBe(false);
  await page.getByRole("button", { name: "Close film" }).click();
  await expect(dialog).not.toBeVisible();
  expect(await video.evaluate((el: HTMLVideoElement) => el.paused)).toBe(true);
});
