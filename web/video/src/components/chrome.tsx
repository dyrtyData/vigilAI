import { useContext } from "react";
import { AbsoluteFill, interpolateColors } from "remotion";
import { beat, chapter, overviewChapters } from "../script";
import { dark, fonts, layout, light } from "../theme";
import { presence, progress } from "../time";
import { NameContext } from "./primitives";

const darkChapter = chapter("validity");
const closing = beat("limitations", "close");
const FADE = 0.8;

/** 0 on ivory, 1 on the dark measurement-audit chapter. */
export function darkness(t: number) {
  return progress(t, darkChapter.start - FADE / 2, FADE) - progress(t, darkChapter.end - FADE / 2, FADE);
}

export function themed(t: number, lightColor: string, darkColor: string) {
  return interpolateColors(darkness(t), [0, 1], [lightColor, darkColor]);
}

export function Background({ t }: { t: number }) {
  return <AbsoluteFill style={{ background: themed(t, light.background, dark.background) }}/>;
}

export function Chrome({ t }: { t: number }) {
  const name = useContext(NameContext);
  const end = overviewChapters[overviewChapters.length - 1].end;
  const secondary = themed(t, light.secondary, dark.eyebrow);
  const lineColor = themed(t, light.line, "#90AD8659");
  const accent = themed(t, light.accent, dark.highlight);
  // The title card and the closing card carry the name themselves.
  const nameOpacity = Math.min(presence(t, 4.6, Infinity, 0.6), 1 - progress(t, closing.at, 0.6));
  const chromeOpacity = 1 - progress(t, closing.at, 0.8);
  const gap = 12;
  const totalGap = gap * (overviewChapters.length - 1);
  let x = layout.marginX;

  return <AbsoluteFill style={{ pointerEvents: "none", opacity: chromeOpacity }}>
    {overviewChapters.map(item => {
      const opacity = presence(t, item.start + (item.start === 0 ? 0.4 : 0.15), item.end + 0.15, 0.55, 0.45);
      if (opacity <= 0) return null;
      return <div key={item.id} style={{ position: "absolute", left: layout.marginX, top: 56, opacity, fontFamily: fonts.sans, fontSize: 30, fontWeight: 650, letterSpacing: 4.4, color: secondary, textTransform: "uppercase" }}>
        <span style={{ color: accent }}>{item.number}</span>&nbsp;&nbsp;/&nbsp;&nbsp;{item.title}
      </div>;
    })}
    <div style={{ position: "absolute", right: layout.marginX, top: 52, opacity: nameOpacity, fontFamily: fonts.sans, fontSize: 34, fontWeight: 700, letterSpacing: -1, color: themed(t, light.text, dark.text) }}>{name}</div>
    {overviewChapters.map(item => {
      const width = ((item.end - item.start) / end) * (layout.contentWidth - totalGap);
      const left = x;
      x += width + gap;
      const fill = Math.max(0, Math.min(1, (t - item.start) / (item.end - item.start)));
      return <div key={item.id} style={{ position: "absolute", left, top: layout.railY, width, height: 4, borderRadius: 2, background: lineColor, overflow: "hidden" }}>
        <div style={{ width: `${fill * 100}%`, height: "100%", background: accent, opacity: t >= item.end ? 0.55 : 1 }}/>
      </div>;
    })}
  </AbsoluteFill>;
}
