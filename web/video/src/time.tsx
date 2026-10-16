import { createContext, useContext, type ReactNode } from "react";
import { Easing, interpolate, Sequence, useCurrentFrame, useVideoConfig } from "remotion";
import { motion } from "./theme";

// Every animation is a pure function of the frame number. Scenes work in absolute film seconds so
// that beat times can be read directly from the shared script module.

const Offset = createContext(0);

export function useTime() {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return frame / fps + useContext(Offset);
}

export function Span({ start, end, name, children }: { start: number; end: number; name: string; children: ReactNode }) {
  const { fps } = useVideoConfig();
  const from = Math.round(start * fps);
  return <Sequence from={from} durationInFrames={Math.round(end * fps) - from} name={name} layout="none">
    <Offset.Provider value={from / fps}>{children}</Offset.Provider>
  </Sequence>;
}

export const ease = Easing.bezier(0.22, 1, 0.36, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** 0 → 1 between `start` and `start + duration`. */
export function progress(t: number, start: number, duration: number = motion.enter, easing = ease) {
  if (duration <= 0) return t >= start ? 1 : 0;
  return interpolate(t, [start, start + duration], [0, 1], { ...clamp, easing });
}

/** Opacity for an element shown from `start` until `end` (fully gone at `end`). */
export function presence(t: number, start: number, end = Infinity, enter: number = motion.enter, exit: number = motion.exit) {
  const fadeIn = progress(t, start, enter);
  const fadeOut = end === Infinity ? 0 : progress(t, end - exit, exit, Easing.in(Easing.quad));
  return Math.max(0, Math.min(fadeIn, 1 - fadeOut));
}

/** Interpolates between keyframes `[time, value]` with easing on each segment. */
export function keyframes(t: number, frames: readonly (readonly [number, number])[], easing = easeInOut) {
  if (t <= frames[0][0]) return frames[0][1];
  for (let i = 1; i < frames.length; i++) {
    const [t1, v1] = frames[i];
    const [t0, v0] = frames[i - 1];
    if (t <= t1) return v0 + (v1 - v0) * easing((t - t0) / Math.max(1e-6, t1 - t0));
  }
  return frames[frames.length - 1][1];
}

export function mix(a: number, b: number, p: number) {
  return a + (b - a) * p;
}
