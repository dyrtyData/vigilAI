import { Abs, Appear, Label, Rich, Svg, usePalette } from "../components/primitives";
import { beat, chapter } from "../script";
import { fonts, type } from "../theme";
import { progress, useTime } from "../time";

const C = chapter("limitations");
const unresolved = beat("limitations", "unresolved");
const close = beat("limitations", "close");

export const CREDITS = [
  "Hackathon team · Team OnçAI: Diana Chang, Ian Duhamel Hayes, Pedro Quezada",
  "Manuscript authors: Diana Chang, Ian Duhamel Hayes",
  "Fork of COMPL-AI (ETH Zurich, INSAIT, LatticeFlow AI) on Inspect AI · upstream credit, not endorsement",
  "Evidence snapshot 36d0030 · Original music composed for this film",
];

function ItemList({ t, at, until, heading, items, pending }: { t: number; at: number; until: number; heading: string; items: readonly string[]; pending: boolean }) {
  const palette = usePalette();
  return <>
    <Appear t={t} at={at + 0.3} until={until} x={120} y={170} w={1640}><Rich text={heading} size={type.statement} weight={600}/></Appear>
    {items.map((item, i) => {
      const start = at + 1.0 + i * 0.9;
      return <Appear key={item} t={t} at={start} until={until} x={120} y={360 + i * 170} w={1680}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 34 }}>
          <svg width={48} height={48} style={{ flexShrink: 0, marginTop: 10 }}>
            {pending
              ? <circle cx={24} cy={24} r={20} fill="none" stroke={palette.accent} strokeWidth={3} strokeDasharray="6 6"/>
              : <path d="M6 24 H38 M28 12 L40 24 L28 36" fill="none" stroke={palette.accent} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" opacity={progress(t, start, 0.6)}/>}
          </svg>
          <div style={{ maxWidth: 1520 }}><Rich text={item} size={58}/></div>
        </div>
      </Appear>;
    })}
  </>;
}

export function LimitationsScene() {
  const t = useTime();
  const palette = usePalette();
  return <>
    <ItemList t={t} at={unresolved.at} until={unresolved.end} heading={unresolved.heading!} items={unresolved.items!} pending/>
    <Appear t={t} at={close.at + 0.4} x={120} y={230} w={1680}><Rich text={close.text} size={116} weight={550} tracking={-4.5}/></Appear>
    <Appear t={t} at={close.at + 1.4} x={120} y={440} w={1200}><Rich text={close.items![0]} size={64} weight={700} tracking={-2}/></Appear>
    <Appear t={t} at={close.at + 1.8} x={120} y={530} w={1400}><Rich text={close.items![1]} size={52} color={palette.secondary}/></Appear>
    <Svg><line x1={120} x2={120 + 1680 * progress(t, close.at + 2.4, 1.0)} y1={680} y2={680} stroke={palette.line} strokeWidth={2}/></Svg>
    {CREDITS.map((line, i) => <Appear key={line} t={t} at={close.at + 2.6 + i * 0.2} x={120} y={708 + i * 52} w={1680} dy={10}>
      <span style={{ fontFamily: fonts.sans, fontSize: 30, color: palette.secondary }}>{line}</span>
    </Appear>)}
    <Abs x={120} y={1000} style={{ opacity: progress(t, close.at + 3.6, 0.8) }}>
      <Label size={24} tracking={2.4}>Research prototype · not a legal certification · PL 2338/2023 is a bill</Label>
    </Abs>
  </>;
}
