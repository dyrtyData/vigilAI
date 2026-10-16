import { Abs, Appear, Arrow, Chip, Draw, Label, Rich, Svg, usePalette } from "../components/primitives";
import { beat, chapter } from "../script";
import { fonts, type } from "../theme";
import { easeInOut, keyframes, presence, progress, useTime } from "../time";

const C = chapter("origin");
const fork = beat("origin", "fork");
const tasks = beat("origin", "tasks");
const recognition = beat("origin", "recognition");

export const UPSTREAM = { x: 120, y: 470, w: 660, h: 390 };
export const FORK = { x: 1080, y: 470, w: 720, h: 390 };
const FOUNDATION_Y = 892;
export const TILE = { size: 46, gap: 14 };

export function tilePosition(block: { x: number; y: number }, index: number) {
  return { x: block.x + 37 + (index % 10) * (TILE.size + TILE.gap), y: block.y + 104 + Math.floor(index / 10) * (TILE.size + TILE.gap) };
}

/** Positions of the five Brazil-specific tiles inside the fork block (handed over to chapter 03). */
export function brazilTilePosition(index: number) {
  return { x: FORK.x + 37 + index * (TILE.size + TILE.gap), y: FORK.y + 104 + 3 * (TILE.size + TILE.gap) + 14 };
}

function blockPath(b: { x: number; y: number; w: number; h: number }, r = 12) {
  return `M${b.x + r} ${b.y} H${b.x + b.w - r} Q${b.x + b.w} ${b.y} ${b.x + b.w} ${b.y + r} V${b.y + b.h - r} Q${b.x + b.w} ${b.y + b.h} ${b.x + b.w - r} ${b.y + b.h} H${b.x + r} Q${b.x} ${b.y + b.h} ${b.x} ${b.y + b.h - r} V${b.y + r} Q${b.x} ${b.y} ${b.x + r} ${b.y}`;
}

export function OriginScene() {
  const t = useTime();
  const palette = usePalette();
  // The architecture recedes while the recognition timeline is shown; the five new tiles stay.
  const diagram = presence(t, fork.at, C.end, 0.6, 0.5) * (1 - progress(t, recognition.at, 0.6));
  const brazilTiles = presence(t, tasks.at + 2.3, Infinity, 0.5);

  return <>
    <Appear t={t} at={fork.at + 0.3} until={fork.end} x={120} y={170} w={1580}><Rich text={fork.text} size={type.statement}/></Appear>
    <Appear t={t} at={tasks.at + 0.2} until={tasks.end} x={120} y={170} w={1580}><Rich text={tasks.text} size={type.statement}/></Appear>
    <Appear t={t} at={recognition.at + 0.3} until={recognition.end} x={120} y={170} w={1580}><Rich text={recognition.text} size={type.statement}/></Appear>

    <div style={{ position: "absolute", inset: 0, opacity: diagram }}>
      <Abs x={120} y={FOUNDATION_Y} w={1680} h={74} style={{ background: palette.surface, border: `2px solid ${palette.line}`, borderRadius: 10, opacity: progress(t, fork.at + 0.6, 0.6), display: "flex", alignItems: "center", gap: 22, paddingLeft: 30 }}>
        <Label size={32} color={palette.text}>Inspect AI</Label>
        <span style={{ fontFamily: fonts.sans, fontSize: 30, color: palette.secondary }}>shared evaluation infrastructure</span>
      </Abs>
      <Svg>
        <Draw d={blockPath(UPSTREAM)} p={progress(t, fork.at + 0.2, 1.0)} stroke={palette.shape}/>
        <Draw d={blockPath(FORK)} p={progress(t, fork.at + 1.6, 1.0)} stroke={palette.accent} width={2.5}/>
        <Arrow x1={UPSTREAM.x + UPSTREAM.w + 24} y1={650} x2={FORK.x - 24} y2={650} p={progress(t, fork.at + 1.3, 0.8)} stroke={palette.shape}/>
        {[UPSTREAM, FORK].map((b, i) => <Draw key={i} d={`M${b.x + b.w / 2} ${b.y + b.h} V${FOUNDATION_Y}`} p={progress(t, fork.at + 0.9 + i * 0.8, 0.5)} stroke={palette.line} width={2}/>)}
      </Svg>
      <Abs x={828} y={575} w={200} style={{ textAlign: "center", opacity: progress(t, fork.at + 1.8, 0.6) }}>
        <span style={{ fontFamily: fonts.serif, fontStyle: "italic", fontSize: 56, color: palette.accent }}>fork</span>
      </Abs>
      <Abs x={UPSTREAM.x + 37} y={UPSTREAM.y + 26} style={{ opacity: progress(t, fork.at + 0.5, 0.6) }}>
        <span style={{ fontFamily: fonts.sans, fontSize: 46, fontWeight: 650, letterSpacing: -1.2, color: palette.text }}>COMPL-AI</span>
        <span style={{ fontFamily: fonts.sans, fontSize: 30, color: palette.secondary, marginLeft: 18 }}>EU AI Act evaluation suite</span>
      </Abs>
      <Abs x={UPSTREAM.x + 37} y={UPSTREAM.y + 290} w={600} style={{ opacity: progress(t, fork.at + 2.4, 0.6) }}>
        <span style={{ fontFamily: fonts.sans, fontSize: 30, color: palette.secondary }}>ETH Zurich · INSAIT · LatticeFlow AI</span>
      </Abs>
      <Abs x={UPSTREAM.x + 37} y={UPSTREAM.y + 336} w={640} style={{ opacity: progress(t, fork.at + 2.8, 0.6) }}>
        <Label size={24} tracking={1.6}>Upstream credit · not an endorsement</Label>
      </Abs>
      <Abs x={FORK.x + 37} y={FORK.y + 26} style={{ opacity: progress(t, fork.at + 2.0, 0.6) }}>
        <Rich text="{name}" size={46} weight={650} tracking={-1.2}/>
        <span style={{ fontFamily: fonts.sans, fontSize: 30, color: palette.secondary, marginLeft: 18 }}>Brazil extension</span>
      </Abs>
      {Array.from({ length: 30 }, (_, i) => {
        const from = tilePosition(UPSTREAM, i);
        const to = tilePosition(FORK, i);
        const start = tasks.at + 0.5 + i * 0.03;
        const travel = progress(t, start, 1.1, easeInOut);
        const appear = progress(t, fork.at + 0.7 + i * 0.025, 0.4);
        return <div key={i}>
          <Abs x={from.x} y={from.y} w={TILE.size} h={TILE.size} style={{ background: palette.shape, borderRadius: 6, opacity: appear * 0.9 }}/>
          {travel > 0 && <Abs x={from.x + (to.x - from.x) * travel} y={from.y + (to.y - from.y) * travel} w={TILE.size} h={TILE.size} style={{ background: palette.shape, borderRadius: 6, opacity: 0.9 }}/>}
        </div>;
      })}
      <Abs x={FORK.x + 37 + 5 * (TILE.size + TILE.gap) + 10} y={brazilTilePosition(0).y + 6} style={{ opacity: progress(t, tasks.at + 3.0, 0.6) }}>
        <span style={{ fontFamily: fonts.sans, fontSize: 32, fontWeight: 650, color: palette.accent }}>+5 Brazil-specific</span>
      </Abs>
      <Abs x={800} y={680} w={260} style={{ textAlign: "center", opacity: progress(t, tasks.at + 1.8, 0.6) }}>
        <span style={{ fontFamily: fonts.sans, fontSize: 32, fontWeight: 650, lineHeight: 1.2, color: palette.text }}>30 tasks<br/>preserved</span>
      </Abs>
    </div>

    {Array.from({ length: 5 }, (_, i) => {
      const position = brazilTilePosition(i);
      const scale = keyframes(t, [[tasks.at + 2.3 + i * 0.12, 0.4], [tasks.at + 2.8 + i * 0.12, 1]]);
      const opacity = brazilTiles * progress(t, tasks.at + 2.3 + i * 0.12, 0.4) * (1 - progress(t, recognition.at, 0.6));
      return <Abs key={i} x={position.x} y={position.y} w={TILE.size} h={TILE.size} style={{ background: palette.accent, borderRadius: 6, opacity, transform: `scale(${scale})` }}/>;
    })}

    <Timeline t={t} at={recognition.at} until={C.end}/>
  </>;
}

function Timeline({ t, at, until }: { t: number; at: number; until: number }) {
  const palette = usePalette();
  const opacity = presence(t, at + 0.5, until);
  if (opacity <= 0) return null;
  const line = progress(t, at + 0.5, 1.2);
  const stops = [
    { x: 160, when: "June 2026", what: "Original hackathon submission", delay: 0.9 },
    { x: 1080, when: "July 2026", what: "Measurement audit and corrected analysis", delay: 2.2 },
  ];
  return <div style={{ position: "absolute", inset: 0, opacity }}>
    <Svg>
      <Draw d="M160 520 H1760" p={line} stroke={palette.shape} width={2}/>
      {stops.map(stop => <circle key={stop.x} cx={stop.x} cy={520} r={12 * progress(t, at + stop.delay, 0.5)} fill={palette.shape}/>)}
    </Svg>
    {stops.map(stop => <Appear key={stop.x} t={t} at={at + stop.delay} x={stop.x} y={560} w={640}>
      <Label size={30} color={palette.accent}>{stop.when}</Label>
      <div style={{ marginTop: 12 }}><Rich text={stop.what} size={44} weight={600}/></div>
    </Appear>)}
    <Appear t={t} at={at + 1.5} x={160} y={740} w={720}>
      <div style={{ display: "inline-flex", flexDirection: "column", gap: 8, padding: "22px 28px", border: `2px solid ${palette.accent}`, borderRadius: 12, background: palette.surface }}>
        <span style={{ fontFamily: fonts.sans, fontSize: 52, fontWeight: 700, letterSpacing: -1.5, color: palette.text }}>Top 25%</span>
        <span style={{ fontFamily: fonts.sans, fontSize: 34, fontWeight: 550, color: palette.text }}>Global South AI Safety Hackathon</span>
      </div>
    </Appear>
    <Appear t={t} at={at + 2.6} x={1080} y={740} w={640}>
      <Chip size={30} color={palette.secondary}>Documented separately</Chip>
    </Appear>
  </div>;
}
