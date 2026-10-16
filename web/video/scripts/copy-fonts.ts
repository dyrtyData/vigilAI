// Copies the website's existing local font files (from @fontsource packages) into the Remotion
// public directory, so the film uses the same Manrope and Instrument Serif assets as the site.
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const modules = join(root, "..", "node_modules");
const target = join(root, "public", "fonts");
const files = [
  ["@fontsource-variable/manrope/files/manrope-latin-wght-normal.woff2", "manrope-latin.woff2"],
  ["@fontsource-variable/manrope/files/manrope-latin-ext-wght-normal.woff2", "manrope-latin-ext.woff2"],
  ["@fontsource-variable/manrope/files/manrope-greek-wght-normal.woff2", "manrope-greek.woff2"],
  ["@fontsource/instrument-serif/files/instrument-serif-latin-400-italic.woff2", "instrument-serif-latin-italic.woff2"],
  ["@fontsource/instrument-serif/files/instrument-serif-latin-ext-400-italic.woff2", "instrument-serif-latin-ext-italic.woff2"],
];

mkdirSync(target, { recursive: true });
for (const [from, to] of files) {
  copyFileSync(join(modules, from), join(target, to));
  console.log(`fonts: ${to}`);
}
