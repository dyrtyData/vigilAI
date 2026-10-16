import { expect, test } from "@playwright/test";

test("explores all benchmarks and changes language with accessible controls", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/en");
  await expect(page).toHaveTitle(/Vigil AI/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Evaluating AI");
  await page.getByRole("link", { name: "Explore the benchmarks" }).click();
  const panel = page.getByRole("tabpanel");
  await expect(panel).toContainText("AI identity disclosure across language conditions");
  await panel.getByRole("button", { name: "EN", exact: true }).click();
  await expect(panel).toContainText("Am I speaking with a person");
  await page.getByRole("tab", { name: /AI disclosure/ }).focus();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("tab", { name: /Non-discrimination/ })).toBeFocused();
  await expect(panel).toContainText("Response accuracy on Brazilian bias scenarios");
  await page.keyboard.press("End");
  await expect(panel).toContainText("Algorithmic impact assessment knowledge");
  for (const name of [/Right to explanation/, /Contestation & review/, /AI disclosure/]) {
    await page.getByRole("tab", { name }).click();
    await expect(page.getByRole("tab", { name })).toHaveAttribute("aria-selected", "true");
  }
  await expect(page.getByText("The original disclosure-gap finding was retracted", { exact: false })).toBeVisible();
  expect(errors).toEqual([]);
});

test("desktop scrolling changes the story chapters", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/en");
  await page.screenshot({ path: testInfo.outputPath("desktop-hero.png") });
  const story = page.locator("#story");
  const bounds = await story.boundingBox();
  expect(bounds).not.toBeNull();
  for (const [progress, label] of [[0.05, "Evaluation framework"], [0.5, "Brazil-specific instruments"], [0.9, "Measurement validation"]] as const) {
    await page.evaluate(({ y, height, progress }) => window.scrollTo({ top: y + (height - window.innerHeight) * progress, behavior: "instant" }), { y: bounds!.y, height: bounds!.height, progress });
    await expect(page.getByRole("region", { name: label, exact: true })).toBeVisible();
  }
  await page.screenshot({ path: testInfo.outputPath("desktop-story.png") });
});

test("mobile has no horizontal overflow and supports the complete story", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/en");
  await page.screenshot({ path: testInfo.outputPath("mobile-hero.png") });
  await page.screenshot({ path: testInfo.outputPath("mobile-full.png"), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("button", { name: /Brazil-specific instruments/ }).click();
  await expect(page.getByRole("region", { name: "Brazil-specific instruments" })).toBeVisible();
  await page.getByRole("button", { name: /Measurement validation/ }).click();
  await expect(page.getByRole("region", { name: "Measurement validation" })).toBeVisible();
  await page.getByRole("tab", { name: /Contestation & review/ }).click();
  await expect(page.getByRole("tabpanel")).toContainText("Contestation and human-review procedures");
});

test("reduced motion keeps the story compact and operable", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", message => { if (message.type() === "error") errors.push(message.text()); });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/en");
  await expect(page.locator(".story-sticky")).toHaveCSS("position", "relative");
  await page.getByRole("button", { name: /Measurement validation/ }).click();
  await expect(page.getByRole("region", { name: "Measurement validation" })).toBeVisible();
  expect(errors).toEqual([]);
});
