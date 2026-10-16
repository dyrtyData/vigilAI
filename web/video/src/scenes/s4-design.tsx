import { Abs, Appear, Chip, Draw, Label, Rich, Svg, usePalette } from "../components/primitives";
import { beat, chapter } from "../script";
import { fonts, type } from "../theme";
import { easeInOut, mix, presence, progress, useTime } from "../time";

const C = chapter("design");
const panel = beat("design", "panel");
const sameModel = beat("design", "same-model");
const units = beat("design", "units");
const repetitions = beat("design", "repetitions");

const MODELS = ["Claude\nHaiku 4.5", "Claude\nSonnet 4.6", "Llama 3.1\n8B", "gpt-oss\n20B", "Qwen2.5\n14B", "Mistral\nSmall"];
const NODE_Y = 540;
const nodeX = (i: number) => 300 + i * 264;
const SINGLE = { x: 470, y: 650 };

export function DesignScene() {
  const t = useTime();
  const palette = usePalette();
  const pending = progress(t, panel.at + 2.4, 0.8);
  const toSingle = progress(t, sameModel.at, 1.0, easeInOut);
  const sceneOut = 1 - progress(t, C.end - 0.5, 0.5);

  return <div style={{ position: "absolute", inset: 0, opacity: sceneOut }}>
    <Appear t={t} at={panel.at + 0.3} until={panel.end} x={120} y={170} w={1600}><Rich text={panel.text} size={type.statement}/></Appear>
    <Appear t={t} at={sameModel.at + 0.3} until={sameModel.end} x={120} y={170} w={1600}><Rich text={sameModel.text} size={type.statement}/></Appear>
    <Appear t={t} at={units.at + 0.3} until={units.end} x={120} y={170} w={1600}><Rich text={units.text} size={type.statement}/></Appear>
    <Appear t={t} at={repetitions.at + 0.3} until={C.end} x={120} y={170} w={1600}><Rich text={repetitions.text} size={type.statement}/></Appear>

    {/* Panel of six → the corrected two. */}
    <Svg>
      {MODELS.map((_, i) => {
        const isFrontier = i < 2;
        const appear = progress(t, panel.at + 0.6 + i * 0.12, 0.6);
        const leave = i === 0 ? 0 : progress(t, sameModel.at, 0.5);
        const x = i === 0 ? mix(nodeX(0), SINGLE.x, toSingle) : nodeX(i);
        const y = i === 0 ? mix(NODE_Y, SINGLE.y, toSingle) : NODE_Y;
        const opacity = appear * (1 - leave) * presence(t, panel.at, units.at, 0.01, 0.5);
        const hollow = isFrontier ? 0 : pending;
        return <g key={i} opacity={opacity}>
          <circle cx={x} cy={y} r={48} fill={palette.shape} fillOpacity={1 - hollow} stroke={hollow > 0 ? palette.secondary : palette.shape} strokeWidth={2.5} strokeDasharray={hollow > 0.5 ? "7 7" : undefined}/>
        </g>;
      })}
      <g opacity={presence(t, panel.at + 2.8, sameModel.at + 0.4, 0.6, 0.4)}>
        <Draw d={`M${nodeX(0) - 60} 745 V765 H${nodeX(1) + 60} V745`} p={progress(t, panel.at + 2.8, 0.7)} stroke={palette.accent} width={2.5}/>
        <Draw d={`M${nodeX(2) - 60} 745 V765 H${nodeX(5) + 60} V745`} p={progress(t, panel.at + 3.1, 0.7)} stroke={palette.secondary} width={2}/>
      </g>
    </Svg>
    {MODELS.map((label, i) => {
      const opacity = progress(t, panel.at + 0.8 + i * 0.12, 0.6) * (1 - progress(t, sameModel.at, 0.4));
      if (opacity <= 0) return null;
      return <Abs key={label} x={nodeX(i) - 130} y={NODE_Y + 70} w={260} style={{ textAlign: "center", opacity }}>
        <span style={{ whiteSpace: "pre-line", fontFamily: fonts.sans, fontSize: 32, fontWeight: 600, lineHeight: 1.2, color: i >= 2 && pending > 0.5 ? palette.secondary : palette.text }}>{label}</span>
      </Abs>;
    })}
    <Appear t={t} at={panel.at + 3.0} until={sameModel.at + 0.4} x={nodeX(0) - 60} y={790} w={600}>
      <span style={{ fontFamily: fonts.sans, fontSize: 36, fontWeight: 650, color: palette.accent }}>Corrected analysis</span>
    </Appear>
    <Appear t={t} at={panel.at + 3.3} until={sameModel.at + 0.4} x={nodeX(2) - 60} y={790} w={900}>
      <span style={{ fontFamily: fonts.sans, fontSize: 36, fontWeight: 600, color: palette.secondary }}>Corrected replication pending</span>
    </Appear>

    <SameModel t={t}/>
    <Units t={t}/>
  </div>;
}

function SameModel({ t }: { t: number }) {
  const palette = usePalette();
  const opacity = presence(t, sameModel.at + 0.6, units.at, 0.6, 0.5);
  if (opacity <= 0) return null;
  const boxes = [{ label: "EU task", y: 520 }, { label: "Brazil task", y: 690 }];
  return <div style={{ position: "absolute", inset: 0, opacity }}>
    <Abs x={SINGLE.x - 150} y={SINGLE.y + 70} w={300} style={{ textAlign: "center" }}><Label size={30} color={palette.text}>Same model</Label></Abs>
    <Svg>
      {boxes.map((box, i) => <Draw key={box.label} d={`M${SINGLE.x + 54} ${SINGLE.y} C${SINGLE.x + 200} ${SINGLE.y} ${780} ${box.y + 60} ${900} ${box.y + 60}`} p={progress(t, sameModel.at + 1.0 + i * 0.25, 0.7)} stroke={palette.shape}/>)}
      {boxes.map((box, i) => <Draw key={`s${box.label}`} d={`M1380 ${box.y + 60} C1440 ${box.y + 60} 1440 ${SINGLE.y} 1500 ${SINGLE.y}`} p={progress(t, sameModel.at + 1.8 + i * 0.2, 0.6)} stroke={palette.accent}/>)}
    </Svg>
    {boxes.map((box, i) => <Appear key={box.label} t={t} at={sameModel.at + 1.2 + i * 0.25} x={900} y={box.y} w={480} h={120}
      style={{ border: `2px solid ${palette.shape}`, borderRadius: 12, display: "grid", placeItems: "center", background: palette.background }}>
      <span style={{ fontFamily: fonts.sans, fontSize: 44, fontWeight: 650, color: palette.text }}>{box.label}</span>
    </Appear>)}
    <Appear t={t} at={sameModel.at + 2.3} x={1500} y={SINGLE.y - 34} w={320}><Chip size={34}>Same scorer</Chip></Appear>
  </div>;
}

const SCENARIO = { x: 140, y: 450, w: 330, h: 360 };
const SAMPLE = { w: 320, h: 160 };
const samples = [
  { context: "Ambiguous context", question: "Negative question", x: 680, y: 470 },
  { context: "Ambiguous context", question: "Non-negative question", x: 1050, y: 470 },
  { context: "Disambiguated context", question: "Negative question", x: 680, y: 670 },
  { context: "Disambiguated context", question: "Non-negative question", x: 1050, y: 670 },
];

function Units({ t }: { t: number }) {
  const palette = usePalette();
  const opacity = presence(t, units.at + 0.5, C.end, 0.6, 0.5);
  if (opacity <= 0) return null;
  const stack = progress(t, repetitions.at + 0.6, 1.2, easeInOut);
  return <div style={{ position: "absolute", inset: 0, opacity }}>
    <Appear t={t} at={units.at + 0.6} x={SCENARIO.x} y={SCENARIO.y} w={SCENARIO.w} h={SCENARIO.h}
      style={{ border: `3px solid ${palette.shape}`, borderRadius: 14, background: palette.surface, padding: 28, boxSizing: "border-box" }}>
      <Label size={28} color={palette.text}>Scenario</Label>
      <div style={{ marginTop: 18, fontFamily: fonts.sans, fontSize: 32, lineHeight: 1.25, color: palette.text }}>One context template, one identity pair</div>
      <div style={{ position: "absolute", left: 28, right: 28, bottom: 30, display: "grid", gap: 14 }}>{[1, 0.8, 0.9, 0.6].map((w, i) => <span key={i} style={{ height: 6, width: `${w * 100}%`, background: palette.line, borderRadius: 3 }}/>)}</div>
    </Appear>
    <Svg>
      <Draw d={`M${SCENARIO.x + SCENARIO.w} 630 H610 M610 540 V740 M610 540 H${samples[0].x} M610 740 H${samples[2].x}`} p={progress(t, units.at + 1.2, 0.8)} stroke={palette.shape}/>
      {samples.map((sample, i) => Array.from({ length: 9 }, (_, k) => {
        const offset = (k + 1) * 4 * stack;
        return <rect key={`${i}-${k}`} x={sample.x + offset} y={sample.y - offset} width={SAMPLE.w} height={SAMPLE.h} rx={10} fill={palette.background} stroke={palette.secondary} strokeOpacity={0.55 - k * 0.04} strokeWidth={1.5} opacity={stack > 0 ? 1 : 0}/>;
      }).reverse())}
    </Svg>
    {samples.map((sample, i) => <Appear key={i} t={t} at={units.at + 1.5 + i * 0.2} x={sample.x} y={sample.y} w={SAMPLE.w} h={SAMPLE.h}
      style={{ border: `2px solid ${palette.shape}`, borderRadius: 10, background: palette.background, padding: "18px 22px", boxSizing: "border-box" }}>
      <div style={{ fontFamily: fonts.sans, fontSize: 30, fontWeight: 650, lineHeight: 1.15, color: palette.text }}>{sample.context}</div>
      <div style={{ marginTop: 6, fontFamily: fonts.sans, fontSize: 26, color: palette.secondary, whiteSpace: "nowrap" }}>{sample.question}</div>
    </Appear>)}
    <Appear t={t} at={units.at + 2.4} x={SCENARIO.x} y={850} w={400}><Counter value="100" unit="scenarios"/></Appear>
    <Appear t={t} at={units.at + 2.7} x={680} y={850} w={500}><Counter value="400" unit="samples"/></Appear>
    <Appear t={t} at={repetitions.at + 1.4} x={1050} y={850} w={760}><Counter value="4,000" unit="scored responses (×10)"/></Appear>
    <Appear t={t} at={repetitions.at + 2.0} x={SCENARIO.x} y={SCENARIO.y - 64} w={420}><Chip size={28} filled>Independent unit</Chip></Appear>
    <Legend t={t}/>
  </div>;
}

function Counter({ value, unit }: { value: string; unit: string }) {
  const palette = usePalette();
  return <span style={{ fontFamily: fonts.sans, color: palette.text }}>
    <span style={{ fontSize: 52, fontWeight: 700, letterSpacing: -1.5, fontVariantNumeric: "tabular-nums" }}>{value}</span>
    <span style={{ fontSize: 34, fontWeight: 550, marginLeft: 12, color: palette.secondary }}>{unit}</span>
  </span>;
}

function Legend({ t }: { t: number }) {
  const palette = usePalette();
  const rows = [
    { label: "Model", at: units.at + 2.0, icon: <span style={{ width: 30, height: 30, borderRadius: "50%", background: palette.shape }}/> },
    { label: "Scenario", at: units.at + 2.2, icon: <span style={{ width: 24, height: 32, borderRadius: 5, border: `3px solid ${palette.shape}`, background: palette.surface }}/> },
    { label: "Sample", at: units.at + 2.4, icon: <span style={{ width: 34, height: 20, borderRadius: 4, border: `2px solid ${palette.shape}` }}/> },
    { label: "Repetition", at: repetitions.at + 1.0, icon: <span style={{ width: 34, height: 20, borderRadius: 4, border: `1.5px solid ${palette.secondary}`, boxShadow: `4px -4px 0 -1.5px ${palette.background}, 4px -4px 0 0 ${palette.secondary}, 8px -8px 0 -1.5px ${palette.background}, 8px -8px 0 0 ${palette.secondary}` }}/> },
  ];
  return <>{rows.map((row, i) => <Appear key={row.label} t={t} at={row.at} x={1470} y={480 + i * 74} w={350}>
    <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
      <span style={{ width: 44, display: "grid", placeItems: "center" }}>{row.icon}</span>
      <span style={{ fontFamily: fonts.sans, fontSize: 34, fontWeight: 600, color: palette.text }}>{row.label}</span>
    </div>
  </Appear>)}</>;
}
