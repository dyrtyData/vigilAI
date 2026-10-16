import { createContext, useContext, type CSSProperties, type ReactNode } from "react";
import { emphasisRuns, fillName } from "../script";
import { fonts, motion, palettes, type Palette } from "../theme";
import { presence, progress } from "../time";

export const NameContext = createContext("Vigil AI");
export const PaletteContext = createContext<Palette>(palettes.light);

export function usePalette() {
  return useContext(PaletteContext);
}

type RichProps = {
  text: string;
  size: number;
  weight?: number;
  color?: string;
  emColor?: string;
  lineHeight?: number;
  tracking?: number;
  style?: CSSProperties;
};

/** Manrope text with `*emphasis*` set in Instrument Serif Italic and `{name}` filled in. */
export function Rich({ text, size, weight = 500, color, emColor, lineHeight = 1.18, tracking, style }: RichProps) {
  const name = useContext(NameContext);
  const palette = usePalette();
  const runs = emphasisRuns(fillName(text, name));
  return <span style={{
    fontFamily: fonts.sans, fontSize: size, fontWeight: weight, color: color ?? palette.text,
    lineHeight: `${Math.round(size * lineHeight)}px`, letterSpacing: tracking ?? -size * 0.03, ...style,
  }}>
    {runs.map((run, index) => run.em
      ? <em key={index} style={{ fontFamily: fonts.serif, fontStyle: "italic", fontWeight: 400, fontSize: "1.12em", letterSpacing: -size * 0.005, color: emColor ?? palette.accent }}>{run.text}</em>
      : <span key={index}>{run.text}</span>)}
  </span>;
}

type Box = { x: number; y: number; w?: number; h?: number; style?: CSSProperties; children?: ReactNode };

export function Abs({ x, y, w, h, style, children }: Box) {
  return <div style={{ position: "absolute", left: x, top: y, width: w, height: h, ...style }}>{children}</div>;
}

/** Fades and rises in at `at`, fades out so that it is gone at `until`. */
export function Appear({ t, at, until = Infinity, dy = motion.rise, dx = 0, x, y, w, h, style, children }: Box & { t: number; at: number; until?: number; dy?: number; dx?: number }) {
  const opacity = presence(t, at, until);
  if (opacity <= 0.001) return null;
  const p = progress(t, at);
  return <Abs x={x} y={y} w={w} h={h} style={{ opacity, transform: `translate(${dx * (1 - p)}px, ${dy * (1 - p)}px)`, ...style }}>{children}</Abs>;
}

export function Label({ children, size = 34, color, weight = 600, tracking = 3.2, style }: { children: ReactNode; size?: number; color?: string; weight?: number; tracking?: number; style?: CSSProperties }) {
  const palette = usePalette();
  return <span style={{ fontFamily: fonts.sans, fontSize: size, fontWeight: weight, letterSpacing: tracking, textTransform: "uppercase", color: color ?? palette.secondary, lineHeight: 1.25, ...style }}>{children}</span>;
}

export function Chip({ children, size = 34, filled = false, color, style }: { children: ReactNode; size?: number; filled?: boolean; color?: string; style?: CSSProperties }) {
  const palette = usePalette();
  const tone = color ?? palette.accent;
  return <span style={{
    display: "inline-flex", alignItems: "center", gap: size * 0.4, fontFamily: fonts.sans, fontSize: size, fontWeight: 600,
    lineHeight: 1, padding: `${size * 0.42}px ${size * 0.55}px`, borderRadius: 8, border: `2px solid ${tone}`,
    color: filled ? palette.background : tone, background: filled ? tone : "transparent", whiteSpace: "nowrap", ...style,
  }}>{children}</span>;
}

/** Square benchmark number badge — the persistent marker for the five Brazilian benchmarks. */
export function Badge({ number, size = 56, style }: { number: string; size?: number; style?: CSSProperties }) {
  const palette = usePalette();
  return <span style={{
    display: "inline-grid", placeItems: "center", width: size, height: size, borderRadius: size * 0.16, background: palette.accent,
    color: palette.background, fontFamily: fonts.sans, fontWeight: 700, fontSize: size * 0.42, letterSpacing: 0.5, fontVariantNumeric: "tabular-nums", ...style,
  }}>{number}</span>;
}

export function Svg({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: "absolute", inset: 0, overflow: "visible", ...style }}>{children}</svg>;
}

/** A path drawn on from 0 to `p` of its length. */
export function Draw({ d, p, stroke, width = 2, dash, opacity = 1, fill = "none", linecap = "round" }: { d: string; p: number; stroke: string; width?: number; dash?: string; opacity?: number; fill?: string; linecap?: "round" | "butt" }) {
  if (p <= 0) return null;
  if (dash) return <path d={d} stroke={stroke} strokeWidth={width} fill={fill} strokeDasharray={dash} opacity={opacity * Math.min(1, p * 3)} strokeLinecap={linecap}/>;
  return <path d={d} pathLength={1} stroke={stroke} strokeWidth={width} fill={fill} strokeDasharray="1 1" strokeDashoffset={1 - p} opacity={opacity} strokeLinecap={linecap}/>;
}

export function arrowHead(x: number, y: number, angle: number, size = 14) {
  const a = (angle * Math.PI) / 180;
  const left = [x - size * Math.cos(a - 0.45), y - size * Math.sin(a - 0.45)];
  const right = [x - size * Math.cos(a + 0.45), y - size * Math.sin(a + 0.45)];
  return `M${left[0]} ${left[1]} L${x} ${y} L${right[0]} ${right[1]}`;
}

/** Horizontal connector with an arrowhead, drawn on with `p`. */
export function Arrow({ x1, y1, x2, y2, p, stroke, width = 2 }: { x1: number; y1: number; x2: number; y2: number; p: number; stroke: string; width?: number }) {
  const angle = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;
  return <g>
    <Draw d={`M${x1} ${y1} L${x2} ${y2}`} p={p} stroke={stroke} width={width}/>
    {p > 0.98 && <path d={arrowHead(x2, y2, angle)} stroke={stroke} strokeWidth={width} fill="none" strokeLinecap="round" strokeLinejoin="round"/>}
  </g>;
}

export function Check({ x, y, size = 40, p, color }: { x: number; y: number; size?: number; p: number; color: string }) {
  const r = size / 2;
  return <g transform={`translate(${x} ${y})`}>
    <circle cx={r} cy={r} r={r - 1.5} fill="none" stroke={color} strokeWidth={2} opacity={Math.min(1, p * 2)}/>
    <Draw d={`M${r * 0.52} ${r * 1.02} L${r * 0.88} ${r * 1.36} L${r * 1.5} ${r * 0.68}`} p={Math.max(0, p * 1.4 - 0.4)} stroke={color} width={2.6}/>
  </g>;
}

/** Neutral rubric criterion marker: what a scorer looks for, not whether a model satisfied it. */
export function Criterion({ x, y, size = 40, p, color }: { x: number; y: number; size?: number; p: number; color: string }) {
  const r = size * 0.18;
  const inset = size * 0.12;
  const side = size - inset * 2;
  return <g transform={`translate(${x} ${y})`}>
    <Draw d={`M${inset + r} ${inset} H${inset + side - r} Q${inset + side} ${inset} ${inset + side} ${inset + r} V${inset + side - r} Q${inset + side} ${inset + side} ${inset + side - r} ${inset + side} H${inset + r} Q${inset} ${inset + side} ${inset} ${inset + side - r} V${inset + r} Q${inset} ${inset} ${inset + r} ${inset}`} p={p} stroke={color} width={2.4}/>
    <rect x={size * 0.38} y={size * 0.38} width={size * 0.24} height={size * 0.24} rx={2} fill={color} opacity={Math.max(0, p * 2 - 1)}/>
  </g>;
}

export function Cross({ x, y, size = 40, p, color }: { x: number; y: number; size?: number; p: number; color: string }) {
  const r = size / 2;
  return <g transform={`translate(${x} ${y})`} opacity={Math.min(1, p * 2)}>
    <circle cx={r} cy={r} r={r - 1.5} fill="none" stroke={color} strokeWidth={2}/>
    <Draw d={`M${r * 0.64} ${r * 0.64} L${r * 1.36} ${r * 1.36}`} p={p} stroke={color} width={2.6}/>
    <Draw d={`M${r * 1.36} ${r * 0.64} L${r * 0.64} ${r * 1.36}`} p={Math.max(0, p * 1.5 - 0.5)} stroke={color} width={2.6}/>
  </g>;
}
