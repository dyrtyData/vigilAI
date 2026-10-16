// Design tokens for the film. web/src/app/globals.css is the source of truth: every colour below
// appears there, and `pnpm verify` fails if one drifts. Sizes are in 1920 × 1080 pixels; at a
// 390 CSS-pixel player width one film pixel is about 0.2 CSS pixels, so essential copy stays at
// or above `type.body` (≈ 12 CSS px on a phone) and smaller sizes are reserved for labels.

export const light = {
  background: "#F7F7EF",
  text: "#24392E",
  primary: "#254B39",
  surface: "#EAECE1",
  secondary: "#687163",
  line: "#D9DDCE",
  accent: "#668058",
} as const;

export const dark = {
  background: "#183E35",
  panel: "#20463B",
  text: "#F1F2E7",
  highlight: "#D0DFAD",
  secondary: "#BAC9BA",
  eyebrow: "#A7BCA7",
  line: "#90AD8640",
} as const;

export type Palette = {
  background: string;
  text: string;
  shape: string;
  surface: string;
  secondary: string;
  line: string;
  accent: string;
};

export const palettes: Record<"light" | "dark", Palette> = {
  light: { background: light.background, text: light.text, shape: light.primary, surface: light.surface, secondary: light.secondary, line: light.line, accent: light.accent },
  dark: { background: dark.background, text: dark.text, shape: dark.highlight, surface: dark.panel, secondary: dark.secondary, line: dark.line, accent: dark.highlight },
};

export const fonts = {
  sans: "Manrope Film, sans-serif",
  serif: "Instrument Serif Film, Georgia, serif",
} as const;

export const type = {
  display: 132,
  headline: 92,
  statement: 72,
  body: 60,
  label: 40,
  caption: 34,
  micro: 30,
} as const;

export const layout = {
  width: 1920,
  height: 1080,
  marginX: 120,
  top: 150,
  contentWidth: 1680,
  railY: 1012,
} as const;

export const motion = {
  /** Seconds for a standard entrance. */
  enter: 0.7,
  /** Seconds for a standard exit, completed at the end of a beat. */
  exit: 0.45,
  /** Pixels travelled during an entrance. */
  rise: 26,
} as const;
