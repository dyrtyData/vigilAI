import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import ts from "typescript";
import { benchmarks, brand } from "../src/lib/content";
import { overviewChapters, overviewFilm } from "../src/lib/project-overview";
import { ptBR } from "../src/lib/locales/pt-br";

test("Portuguese translations cover the interface and complete research transcript", () => {
  const copy = new Set([brand.descriptor]);
  const sources = ["app/[locale]/page.tsx", "app/[locale]/layout.tsx", "components/benchmark-explorer.tsx", "components/scroll-story.tsx", "components/project-film.tsx", "components/film-transcript.tsx", "components/language-switch.tsx"];
  for (const source of sources) {
    const file = ts.createSourceFile(source, readFileSync(path.join(process.cwd(), "src", source), "utf8"), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    function visit(node: ts.Node) {
      if (ts.isCallExpression(node) && node.expression.getText(file) === "t" && node.arguments[0] && ts.isStringLiteral(node.arguments[0])) copy.add(node.arguments[0].text);
      if (ts.isPropertyAssignment(node) && ["title", "label", "text"].includes(node.name.getText(file)) && ts.isStringLiteral(node.initializer)) copy.add(node.initializer.text);
      ts.forEachChild(node, visit);
    }
    visit(file);
  }
  for (const item of benchmarks) for (const text of [item.name, item.scope, item.title, item.description, ...item.criteria]) copy.add(text);
  for (const chapter of overviewChapters) {
    copy.add(chapter.title);
    for (const beat of chapter.beats) {
      for (const text of [beat.heading, beat.text, beat.visual, ...beat.items ?? []]) if (text) copy.add(text);
      if (beat.table) for (const text of [beat.table.caption, beat.table.note, ...beat.table.columns, ...beat.table.rows.map(row => row[0])]) if (text) copy.add(text);
    }
  }
  const unchanged = new Set(["Global South AI Safety Hackathon", "COMPL-AI", "Inspect AI", "GLOBAL SOUTH", "AI SAFETY HACKATHON", "PT-BR", "EN", "Haiku 4.5", "Sonnet 4.6", "Claude Haiku 4.5", "Claude Sonnet 4.6", "{name}"]);
  expect([...copy].filter(text => !Object.hasOwn(ptBR, text) && !unchanged.has(text))).toEqual([]);
  // Translation must not silently change research figures, model versions, dates or article numbers.
  for (const [english, portuguese] of Object.entries(ptBR)) {
    expect(portuguese.match(/\d+(?:[.,]\d+)*/g) ?? [], english).toEqual(english.match(/\d+(?:[.,]\d+)*/g) ?? []);
  }
});

test("Portuguese is rendered on the server with localized metadata and no JavaScript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  const response = await page.goto("/");
  expect(response?.status()).toBe(200);
  expect(response?.request().redirectedFrom()).toBeNull();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "pt-BR");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Avaliando IA");
  await expect(page).toHaveTitle(/Avaliação de modelos de linguagem baseada em direitos/);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /Resumo da pesquisa Vigil AI/);
  await expect(page.locator('link[hreflang="en"]')).toHaveAttribute("href", /\/en$/);
  await expect(page.locator('link[hreflang="pt-BR"]')).toHaveAttribute("href", /\/$/);
  await expect(page.locator('link[hreflang="x-default"]')).toHaveAttribute("href", /\/$/);
  await page.getByRole("link", { name: "English", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.getByRole("link", { name: "Português do Brasil" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "pt-BR");
  await context.close();
});

test("language switching preserves the section and selected language on reload", async ({ page }) => {
  await page.goto("/en?ref=research#benchmarks");
  await page.getByRole("link", { name: "Português do Brasil" }).click();
  await expect(page).toHaveURL(/\/\?ref=research#benchmarks$/);
  await expect(page.getByRole("link", { name: "Português do Brasil" })).toHaveAttribute("aria-current", "page");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("lang", "pt-BR");
  await page.getByRole("link", { name: "English", exact: true }).click();
  await expect(page).toHaveURL(/\/en\?ref=research#benchmarks$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});

test("Portuguese benchmarks, methods and transcript retain the evidence", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("tab", { name: /Não discriminação/ }).click();
  await expect(page.getByRole("tabpanel")).toContainText("100 cenários");
  const questionLanguages = page.getByRole("group", { name: "Idioma da pergunta" });
  await questionLanguages.getByRole("button", { name: "EN", exact: true }).click();
  await expect(page.getByRole("tabpanel").locator('p[lang="en"]')).toContainText("Two people");
  await expect(page.locator("html")).toHaveAttribute("lang", "pt-BR");
  await questionLanguages.getByRole("button", { name: "PT-BR", exact: true }).click();
  await expect(page.getByRole("tabpanel").locator('p[lang="pt-BR"]')).toContainText("Duas pessoas");
  await page.getByRole("button", { name: /Validação da medição/ }).click();
  await expect(page.getByRole("region", { name: "Validação da medição" })).toContainText("Registros de avaliação rastreáveis");
  const transcript = page.locator("#film-transcript");
  await transcript.locator("summary").click();
  await expect(transcript).toContainText("Esse resultado foi retratado.");
  await expect(transcript).toContainText("não uma prova de que uma jurisdição");
  await expect(transcript).toContainText("0.986 ± 0.014");
  await expect(transcript).toContainText("+0.218 ± 0.030");
  await expect(transcript).toContainText("não foram validados por anotadores nativos");
  await expect(transcript).not.toContainText("Next steps");
  await expect(page.locator(".hero-film")).toContainText("Vídeo em inglês");
});

test("Portuguese mobile page has no overflow and the translated film controls work", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("link", { name: "English", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("portuguese-mobile.png"), caret: "initial" });
  const trigger = page.getByRole("button", { name: "Reproduzir a apresentação" });
  await trigger.click();
  await expect(page.getByRole("dialog", { name: "O vídeo da pesquisa" })).toBeVisible();
  await expect.poll(() => page.locator("video").evaluate((el: HTMLVideoElement) => el.currentTime)).toBeGreaterThan(0);
  expect(await page.locator("video").evaluate((el: HTMLVideoElement) => el.duration)).toBeCloseTo(overviewFilm.durationSeconds, 1);
  await page.getByRole("button", { name: /Reproduzir capítulo 08/ }).click();
  await expect.poll(() => page.locator("video").evaluate((el: HTMLVideoElement) => el.currentTime)).toBeGreaterThanOrEqual(177);
  await page.getByRole("button", { name: "Pausar", exact: true }).click();
  await expect(page.getByRole("slider", { name: "Posição no vídeo" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("portuguese-player.png"), caret: "initial" });
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  expect(errors).toEqual([]);
});

test("Portuguese is the default, legacy links redirect and unsupported locales return 404", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "pt-BR");
  const legacy = await page.request.get("/pt-br?ref=legacy", { maxRedirects: 0 });
  expect(legacy.status()).toBe(308);
  expect(legacy.headers().location).toBe("/?ref=legacy");
  await page.goto("/pt-br?ref=legacy#benchmarks");
  await expect(page).toHaveURL(/\/\?ref=legacy#benchmarks$/);
  await expect(page.locator("html")).toHaveAttribute("lang", "pt-BR");
  const response = await page.request.get("/fr");
  expect(response.status()).toBe(404);
});

test("Portuguese desktop layout and reduced motion remain accessible", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator("#film-transcript")).toHaveAttribute("open", "");
  await expect(page.getByRole("navigation", { name: "Navegação principal" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(page.getByRole("button", { name: "Reproduzir a apresentação" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("portuguese-desktop.png"), caret: "initial" });
});
