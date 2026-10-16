import { Abs, Appear, Arrow, Chip, Draw, Label, Rich, Svg, usePalette } from "../components/primitives";
import { beat, chapter } from "../script";
import { fonts, type } from "../theme";
import { presence, progress, useTime } from "../time";

const C = chapter("implementation");
const pipeline = beat("implementation", "pipeline");
const report = beat("implementation", "report");

const STEPS = [
  { title: "Python", sub: "vigilai package" },
  { title: "Inspect AI", sub: "evaluation framework" },
  { title: "Models", sub: "Anthropic API or local Ollama" },
  { title: "Scoring", sub: "Scores ± standard errors" },
  { title: "Reports", sub: "Article-level research reports" },
];
const NODE = { y: 500, w: 290, h: 190, step: 347.5 };

export function ImplementationScene() {
  const t = useTime();
  return <>
    <Appear t={t} at={pipeline.at + 0.8} until={pipeline.end} x={120} y={170} w={1640}><Rich text={pipeline.text} size={type.statement}/></Appear>
    <Appear t={t} at={report.at + 0.3} until={C.end} x={120} y={170} w={1640}><Rich text={report.text} size={type.statement}/></Appear>
    <Pipeline t={t}/>
    <Report t={t}/>
  </>;
}

function Pipeline({ t }: { t: number }) {
  const palette = usePalette();
  const opacity = presence(t, pipeline.at + 0.9, pipeline.end);
  if (opacity <= 0) return null;
  return <div style={{ position: "absolute", inset: 0, opacity }}>
    <Svg>{STEPS.slice(0, -1).map((_, i) => {
      const x1 = 120 + i * NODE.step + NODE.w + 6;
      return <Arrow key={i} x1={x1} y1={NODE.y + NODE.h / 2} x2={x1 + NODE.step - NODE.w - 12} y2={NODE.y + NODE.h / 2} p={progress(t, pipeline.at + 1.4 + i * 0.35, 0.35)} stroke={palette.shape}/>;
    })}</Svg>
    {STEPS.map((step, i) => <Appear key={step.title} t={t} at={pipeline.at + 1.1 + i * 0.35} x={120 + i * NODE.step} y={NODE.y} w={NODE.w} h={NODE.h}
      style={{ border: `2px solid ${i === 3 ? palette.accent : palette.shape}`, borderRadius: 14, background: i === 3 ? palette.surface : palette.background, padding: "24px 24px", boxSizing: "border-box" }}>
      <div style={{ fontFamily: fonts.sans, fontSize: 40, fontWeight: 650, letterSpacing: -1, color: palette.text }}>{step.title}</div>
      <div style={{ marginTop: 10, fontFamily: fonts.sans, fontSize: 27, lineHeight: 1.25, color: palette.secondary }}>{step.sub}</div>
    </Appear>)}
    <Appear t={t} at={pipeline.at + 3.2} x={120 + 3 * NODE.step} y={NODE.y + NODE.h + 34} w={560}>
      <div style={{ display: "grid", gap: 14 }}>
        <span><Chip size={28} filled>Primary · deterministic</Chip></span>
        <span><Chip size={28}>Supplementary · LLM judge</Chip></span>
      </div>
    </Appear>
    <Appear t={t} at={pipeline.at + 3.6} x={120} y={NODE.y + NODE.h + 40} w={900}>
      <span style={{ fontFamily: fonts.sans, fontSize: 32, color: palette.secondary }}>Human and community validation: not yet performed.</span>
    </Appear>
  </div>;
}

function Report({ t }: { t: number }) {
  const palette = usePalette();
  const opacity = presence(t, report.at + 0.5, C.end);
  if (opacity <= 0) return null;
  const fields = [
    ["Model", "anthropic/claude-haiku-4-5"],
    ["Configuration", "10 epochs · temperature 1.0 · seed 42"],
    ["Scoring method", "Deterministic · mean ± standard error"],
    ["Limitations", "Stated alongside each result"],
  ];
  const card = { x: 300, y: 386, w: 1100, h: 590 };
  return <div style={{ position: "absolute", inset: 0, opacity }}>
    <Appear t={t} at={report.at + 0.6} x={card.x} y={card.y} w={card.w} h={card.h} style={{ border: `2px solid ${palette.shape}`, borderRadius: 16, background: palette.background, boxShadow: "0 30px 60px rgba(36, 57, 46, 0.08)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "24px 40px", borderBottom: `2px solid ${palette.line}` }}>
        <Label size={26}>Research report · article level</Label>
        <Label size={26} color={palette.accent}>Traceable record</Label>
      </div>
      <div style={{ padding: "26px 40px 0", fontFamily: fonts.sans, fontSize: 44, fontWeight: 650, letterSpacing: -1, color: palette.text }}>Art. 5, I · AI disclosure</div>
    </Appear>
    <Svg><Draw d={`M${card.x + 52} ${card.y + 226} V${card.y + 226 + 3 * 82}`} p={progress(t, report.at + 1.2, 1.2)} stroke={palette.accent} width={2}/></Svg>
    {fields.map(([label, value], i) => <Appear key={label} t={t} at={report.at + 1.2 + i * 0.35} x={card.x + 40} y={card.y + 204 + i * 82} w={card.w - 80} dy={10}>
      <div style={{ display: "flex", alignItems: "center", gap: 26 }}>
        <span style={{ width: 24, height: 24, borderRadius: "50%", border: `3px solid ${palette.accent}`, background: palette.background, flexShrink: 0 }}/>
        <span style={{ width: 260, fontFamily: fonts.sans, fontSize: 30, fontWeight: 600, color: palette.secondary }}>{label}</span>
        <span style={{ fontFamily: fonts.sans, fontSize: 32, fontWeight: 600, color: palette.text, whiteSpace: "nowrap" }}>{value}</span>
      </div>
    </Appear>)}
    <Appear t={t} at={report.at + 2.8} x={1460} y={card.y + 10} w={360}>
      <Label size={26}>Paper workflow</Label>
      <div style={{ marginTop: 10, fontFamily: fonts.sans, fontSize: 38, fontWeight: 650, color: palette.text }}>Pandoc · XeLaTeX</div>
    </Appear>
    <Appear t={t} at={report.at + 2.4} x={card.x + 40} y={card.y + card.h - 62} w={card.w - 80}>
      <span style={{ fontFamily: fonts.sans, fontSize: 30, color: palette.secondary }}>Formats: Markdown · JSON · HTML</span>
    </Appear>
  </div>;
}
