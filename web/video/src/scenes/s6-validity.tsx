import { Abs, Appear, Arrow, Cross, Draw, Label, Rich, Svg, usePalette } from "../components/primitives";
import { beat, chapter } from "../script";
import { fonts, type } from "../theme";
import { easeInOut, mix, presence, progress, useTime } from "../time";
import { BenchmarkTag } from "./s5-disclosure";

const C = chapter("validity");
const parser = beat("validity", "parser");
const baseline = beat("validity", "baseline");
const differences = beat("validity", "differences");
const detectors = beat("validity", "detectors");
const answerKey = beat("validity", "answer-key");
const message = beat("validity", "message");

export function ValidityScene() {
  const t = useTime();
  const statements = [parser, baseline, differences, detectors, answerKey];
  return <>
    <BenchmarkTag t={t} at={parser.at + 0.6} until={detectors.at} number="02" text="Non-discrimination · Art. 5, III"/>
    <BenchmarkTag t={t} at={detectors.at + 0.2} until={detectors.end} number="04" text="Contestation and human review · rubric detector"/>
    <BenchmarkTag t={t} at={answerKey.at + 0.2} until={answerKey.end} number="05" text="Algorithmic impact assessment · Arts. 25–28"/>
    {statements.map(item => <Appear key={item.id} t={t} at={item.at + (item === parser ? 0.8 : 0.3)} until={item.end} x={120} y={232} w={1640}><Rich text={item.text} size={type.statement}/></Appear>)}
    <Parser t={t}/>
    <Baseline t={t}/>
    <Differences t={t}/>
    <Detectors t={t}/>
    <AnswerKey t={t}/>
    <Message t={t}/>
  </>;
}

function Parser({ t }: { t: number }) {
  const palette = usePalette();
  const opacity = presence(t, parser.at + 1.2, parser.end);
  if (opacity <= 0) return null;
  const box = { border: `2px solid ${palette.line}`, borderRadius: 14, background: palette.surface, padding: "26px 30px", boxSizing: "border-box" } as const;
  return <div style={{ position: "absolute", inset: 0, opacity }}>
    <Appear t={t} at={parser.at + 1.3} x={120} y={500} w={460} h={200} style={box}>
      <Label size={26}>Model answer</Label>
      <div style={{ marginTop: 22, fontFamily: fonts.sans, fontSize: 58, fontWeight: 650, color: palette.text }}>ANSWER: <span style={{ color: palette.accent }}>$</span>B</div>
    </Appear>
    <Appear t={t} at={parser.at + 1.8} x={700} y={500} w={520} h={200} style={{ ...box, background: "transparent", border: `2px solid ${palette.accent}` }}>
      <Label size={26}>Multiple-choice parser</Label>
      <div style={{ marginTop: 22, fontFamily: fonts.sans, fontSize: 40, fontWeight: 600, color: palette.text }}>Expects “ANSWER: B”</div>
      <div style={{ marginTop: 8, fontFamily: fonts.sans, fontSize: 30, color: palette.secondary }}>The “$” prevents a match</div>
    </Appear>
    <Svg>
      <Arrow x1={596} y1={600} x2={684} y2={600} p={progress(t, parser.at + 1.7, 0.4)} stroke={palette.accent}/>
      <Arrow x1={1236} y1={600} x2={1324} y2={600} p={progress(t, parser.at + 2.4, 0.4)} stroke={palette.accent}/>
      <Cross x={1350} y={546} size={50} p={progress(t, parser.at + 2.7, 0.5)} color={palette.text}/>
    </Svg>
    <Appear t={t} at={parser.at + 2.7} x={1420} y={530} w={400}>
      <div style={{ fontFamily: fonts.sans, fontSize: 50, fontWeight: 650, color: palette.text }}>Unreadable</div>
      <div style={{ fontFamily: fonts.sans, fontSize: 36, color: palette.secondary }}>scored incorrect</div>
    </Appear>
    <Appear t={t} at={parser.at + 3.5} x={120} y={772} w={1680}>
      <div style={{ display: "inline-flex", gap: 18, alignItems: "center", padding: "16px 24px", background: palette.surface, borderLeft: `5px solid ${palette.accent}`, borderRadius: 6 }}>
        <span style={{ fontFamily: fonts.sans, fontSize: 34, fontWeight: 650, color: palette.accent }}>Fixed</span>
        <span style={{ fontFamily: fonts.sans, fontSize: 34, color: palette.text }}>Stored answers were re-scored with a tolerant parser; the model outputs did not change.</span>
      </div>
    </Appear>
  </div>;
}

const ROW_Y = [560, 648, 736, 824];
const TILE = 16;
const STEP = 22;
const AXES = [
  { eu: "Race / ethnicity", br: "Race (IBGE)", note: "" },
  { eu: "Religion", br: "Religion", note: "" },
  { eu: "SES", br: "Class", note: "" },
  { eu: "Nationality", br: "Region", note: "approximate" },
];

function Baseline({ t }: { t: number }) {
  const palette = usePalette();
  const opacity = presence(t, baseline.at + 0.6, baseline.end);
  if (opacity <= 0) return null;
  const reform = progress(t, baseline.at + 3.6, 1.6, easeInOut);
  const revised = progress(t, baseline.at + 4.6, 0.8);
  const original = 1 - progress(t, baseline.at + 3.4, 0.5);
  return <div style={{ position: "absolute", inset: 0, opacity }}>
    <Abs x={120} y={496} style={{ opacity: progress(t, baseline.at + 1.0, 0.5) * original }}><Label size={28}>Original EU baseline</Label></Abs>
    <Abs x={120} y={496} style={{ opacity: revised }}><Label size={28}>Revised EU baseline · BBQ subset</Label></Abs>
    <Abs x={1340} y={496} style={{ opacity: revised }}><Label size={28}>Brazilian axis</Label></Abs>
    <Abs x={120} y={ROW_Y[0] + 2} style={{ opacity: progress(t, baseline.at + 1.6, 0.5) * original }}>
      <span style={{ fontFamily: fonts.sans, fontSize: 40, fontWeight: 650, color: palette.text }}>Age only</span>
      <div style={{ fontFamily: fonts.sans, fontSize: 30, color: palette.secondary }}>100 samples</div>
    </Abs>
    <Svg>
      {Array.from({ length: 192 }, (_, j) => {
        const group = Math.floor(j / 48);
        const k = j % 48;
        const to = { x: 520 + (k % 24) * STEP, y: ROW_Y[group] + Math.floor(k / 24) * STEP };
        if (j < 100) {
          const from = { x: 520 + (j % 25) * STEP, y: ROW_Y[Math.floor(j / 25)] + STEP / 2 };
          const appear = progress(t, baseline.at + 1.2 + j * 0.008, 0.4);
          return <rect key={j} x={mix(from.x, to.x, reform)} y={mix(from.y, to.y, reform)} width={TILE} height={TILE} rx={3} fill={reform > 0.5 ? palette.accent : palette.secondary} opacity={appear}/>;
        }
        return <rect key={j} x={to.x} y={to.y} width={TILE} height={TILE} rx={3} fill={palette.accent} opacity={progress(t, baseline.at + 4.6 + (j - 100) * 0.006, 0.4)}/>;
      })}
      {AXES.map((_, i) => <Draw key={i} d={`M1080 ${ROW_Y[i] + 19} H1310`} p={progress(t, baseline.at + 5.2 + i * 0.12, 0.5)} stroke={palette.line} width={2}/>)}
    </Svg>
    {AXES.map((axis, i) => <Appear key={axis.eu} t={t} at={baseline.at + 4.8 + i * 0.12} x={120} y={ROW_Y[i] - 2} w={380}>
      <span style={{ fontFamily: fonts.sans, fontSize: 36, fontWeight: 600, color: palette.text }}>{axis.eu}</span>
    </Appear>)}
    {AXES.map((axis, i) => <Appear key={axis.br} t={t} at={baseline.at + 5.4 + i * 0.12} x={1340} y={ROW_Y[i] - 2} w={480}>
      <span style={{ fontFamily: fonts.sans, fontSize: 36, fontWeight: 600, color: palette.text }}>{axis.br}</span>
      {axis.note && <span style={{ fontFamily: fonts.sans, fontSize: 28, color: palette.secondary, marginLeft: 14 }}>{axis.note}</span>}
    </Appear>)}
    <Appear t={t} at={baseline.at + 6.0} x={120} y={912} w={1680}>
      <span style={{ fontFamily: fonts.sans, fontSize: 32, color: palette.secondary }}>48 samples per axis · 192 in total. </span>
      <span style={{ fontFamily: fonts.sans, fontSize: 32, color: palette.text }}>Intersectional (Brazil) has no counterpart.</span>
    </Appear>
  </div>;
}

const CHART = { left: 560, right: 1380, min: -0.1, max: 0.3, axisY: 800 };
const xOf = (value: number) => CHART.left + ((value - CHART.min) / (CHART.max - CHART.min)) * (CHART.right - CHART.left);

function Differences({ t }: { t: number }) {
  const palette = usePalette();
  const opacity = presence(t, differences.at + 0.6, differences.end);
  if (opacity <= 0) return null;
  const rows = [
    { model: "Claude Haiku 4.5", value: 0.218, se: 0.030, label: "+0.218 ± 0.030", y: 590, at: differences.at + 1.6 },
    { model: "Claude Sonnet 4.6", value: 0.005, se: 0.026, label: "+0.005 ± 0.026", y: 720, at: differences.at + 2.2 },
  ];
  const axis = progress(t, differences.at + 0.8, 0.8);
  return <div style={{ position: "absolute", inset: 0, opacity }}>
    <Svg>
      <Draw d={`M${CHART.left} ${CHART.axisY} H${CHART.right}`} p={axis} stroke={palette.secondary} width={2}/>
      {[-0.1, 0, 0.1, 0.2, 0.3].map(tick => <line key={tick} x1={xOf(tick)} x2={xOf(tick)} y1={CHART.axisY} y2={CHART.axisY + 12} stroke={palette.secondary} strokeWidth={2} opacity={axis}/>)}
      <line x1={xOf(0)} x2={xOf(0)} y1={530} y2={CHART.axisY} stroke={palette.text} strokeWidth={2} strokeDasharray="8 8" opacity={progress(t, differences.at + 1.1, 0.5)}/>
      {rows.map(row => {
        const reveal = progress(t, row.at, 0.6);
        return <g key={row.model} opacity={reveal}>
          <line x1={xOf(row.value - row.se)} x2={xOf(row.value + row.se)} y1={row.y} y2={row.y} stroke={palette.accent} strokeWidth={4}/>
          {[row.value - row.se, row.value + row.se].map(edge => <line key={edge} x1={xOf(edge)} x2={xOf(edge)} y1={row.y - 16} y2={row.y + 16} stroke={palette.accent} strokeWidth={4}/>)}
          <circle cx={xOf(row.value)} cy={row.y} r={14} fill={palette.accent}/>
        </g>;
      })}
    </Svg>
    {[-0.1, 0, 0.1, 0.2, 0.3].map(tick => <Abs key={tick} x={xOf(tick) - 60} y={CHART.axisY + 20} w={120} style={{ textAlign: "center", opacity: axis }}>
      <span style={{ fontFamily: fonts.sans, fontSize: 32, fontVariantNumeric: "tabular-nums", color: palette.secondary }}>{tick === 0 ? "0" : `${tick > 0 ? "+" : "−"}${Math.abs(tick).toFixed(1)}`}</span>
    </Abs>)}
    <Abs x={xOf(0) + 14} y={496} style={{ opacity: progress(t, differences.at + 1.2, 0.5) }}><Label size={24} tracking={2}>No difference</Label></Abs>
    <Abs x={1452} y={496} style={{ opacity: progress(t, differences.at + 1.4, 0.5) }}><Label size={26} tracking={2}>Δ ± SE</Label></Abs>
    {rows.map(row => <div key={row.model}>
      <Appear t={t} at={row.at - 0.2} x={120} y={row.y - 28} w={440}><span style={{ fontFamily: fonts.sans, fontSize: 42, fontWeight: 600, color: palette.text }}>{row.model}</span></Appear>
      <Appear t={t} at={row.at + 0.3} x={1452} y={row.y - 30} w={348}>
        <span style={{ fontFamily: fonts.sans, fontSize: 46, fontWeight: 700, fontVariantNumeric: "tabular-nums", color: palette.text, whiteSpace: "nowrap" }}>{row.label}</span>
      </Appear>
    </div>)}
    <Appear t={t} at={differences.at + 1.0} x={CHART.left} y={CHART.axisY + 68} w={1280}>
      <span style={{ fontFamily: fonts.sans, fontSize: 32, color: palette.text }}>Brazil − EU accuracy difference, matched-axis baseline</span>
    </Appear>
    <Appear t={t} at={differences.at + 3.0} x={CHART.left} y={CHART.axisY + 112} w={1280}>
      <span style={{ fontFamily: fonts.sans, fontSize: 28, color: palette.secondary }}>Dot: difference in benchmark accuracy · whiskers: ± 1 scenario-clustered standard error</span>
    </Appear>
  </div>;
}

function Detectors({ t }: { t: number }) {
  const palette = usePalette();
  const opacity = presence(t, detectors.at + 0.6, detectors.end);
  if (opacity <= 0) return null;
  const mark = progress(t, detectors.at + 1.5, 0.6);
  return <div style={{ position: "absolute", inset: 0, opacity }}>
    <Appear t={t} at={detectors.at + 0.7} x={120} y={440} w={700}><Label size={28}>Cue: “form”</Label></Appear>
    <Appear t={t} at={detectors.at + 0.8} x={120} y={490} w={1680}>
      <span style={{ fontFamily: fonts.sans, fontSize: 150, fontWeight: 600, letterSpacing: -4, color: palette.secondary }}>
        in<span style={{ color: palette.text, background: `rgba(208, 223, 173, ${0.22 * mark})`, borderBottom: `6px solid rgba(208, 223, 173, ${mark})`, borderRadius: 6 }}>form</span>ação
      </span>
    </Appear>
    <Appear t={t} at={detectors.at + 2.0} x={120} y={720} w={1680}>
      <span style={{ fontFamily: fonts.sans, fontSize: 42, fontWeight: 600, color: palette.text }}>Matched inside an unrelated word and credited as rubric evidence.</span>
    </Appear>
    <Appear t={t} at={detectors.at + 2.8} x={120} y={810} w={1680}>
      <span style={{ fontFamily: fonts.sans, fontSize: 36, fontWeight: 600, color: palette.accent }}>Revised detectors match whole words.</span>
    </Appear>
  </div>;
}

function PromptPanel({ t, at, x, title, lines, score, note }: { t: number; at: number; x: number; title: string; lines: number; score: string; note: string }) {
  const palette = usePalette();
  return <Appear t={t} at={at} x={x} y={530} w={780} h={360} style={{ border: `2px solid ${palette.line}`, borderRadius: 14, background: palette.surface, padding: "30px 34px", boxSizing: "border-box" }}>
    <Label size={28} color={palette.text}>{title}</Label>
    <div style={{ marginTop: 10, fontFamily: fonts.sans, fontSize: 30, color: palette.secondary }}>{note}</div>
    <div style={{ position: "absolute", left: 34, top: 140, width: 300, display: "grid", gap: 14 }}>
      {Array.from({ length: lines }, (_, i) => <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, opacity: progress(t, at + 0.4 + i * 0.1, 0.4) }}>
        {lines > 2 && <span style={{ width: 10, height: 10, borderRadius: 2, background: palette.accent }}/>}
        <span style={{ height: 8, flex: 1, borderRadius: 4, background: lines > 2 ? palette.accent : palette.secondary, opacity: lines > 2 ? 0.75 : 0.45, maxWidth: `${70 + ((i * 37) % 30)}%` }}/>
      </div>)}
    </div>
    <div style={{ position: "absolute", right: 34, bottom: 30, textAlign: "right" }}>
      <div style={{ fontFamily: fonts.sans, fontSize: 28, color: palette.secondary }}>Prompt text alone scores</div>
      <div style={{ fontFamily: fonts.sans, fontSize: 92, fontWeight: 700, letterSpacing: -3, fontVariantNumeric: "tabular-nums", color: palette.accent }}>{score}</div>
    </div>
  </Appear>;
}

function AnswerKey({ t }: { t: number }) {
  const palette = usePalette();
  const opacity = presence(t, answerKey.at + 0.8, answerKey.end);
  if (opacity <= 0) return null;
  return <div style={{ position: "absolute", inset: 0, opacity }}>
    <PromptPanel t={t} at={answerKey.at + 1.0} x={120} title="Guided prompt" note="Lists the obligations it scores" lines={6} score="0.944"/>
    <PromptPanel t={t} at={answerKey.at + 1.7} x={1020} title="Unguided prompt" note="States the legal basis only" lines={2} score="0.000"/>
    <Appear t={t} at={answerKey.at + 2.6} x={120} y={914} w={1680}>
      <span style={{ fontFamily: fonts.sans, fontSize: 30, color: palette.secondary }}>Echo floor: what the scorer credits to the prompt text itself, before any model answers.</span>
    </Appear>
  </div>;
}

function Message({ t }: { t: number }) {
  const [first, second] = message.text.split(/(?<=\.) /);
  return <>
    <Appear t={t} at={message.at + 0.3} until={C.end - 0.35} x={120} y={380} w={1680} style={{ textAlign: "center" }}><Rich text={first} size={112} weight={550} tracking={-4}/></Appear>
    <Appear t={t} at={message.at + 1.1} until={C.end - 0.35} x={120} y={512} w={1680} style={{ textAlign: "center" }}><Rich text={second} size={112} tracking={-4}/></Appear>
  </>;
}
