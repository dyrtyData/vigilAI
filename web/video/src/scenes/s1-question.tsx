import { Abs, Appear, Draw, Label, Rich, Svg, usePalette } from "../components/primitives";
import { beat, chapter } from "../script";
import { type } from "../theme";
import { keyframes, presence, progress, useTime } from "../time";

const C = chapter("question");
const title = beat("question", "title");
const question = beat("question", "question");
const scope = beat("question", "scope");

export const FRAME = { x: 1080, y: 330, w: 580, h: 450 };
const NODE = { x: FRAME.x + FRAME.w / 2, y: FRAME.y + 212, r: 62 };
const OFFSET = 56;

/** The model inside an evaluation framework, with language and jurisdiction as layers behind it. */
export function LayeredModel({ t, layersAt, legendAt, end }: { t: number; layersAt: number; legendAt: number; end: number }) {
  const palette = usePalette();
  const frameDraw = progress(t, 0.3, 1.1);
  const node = progress(t, 1.0, 0.8);
  const fade = presence(t, 0, end, 0.01, 0.5);
  const sheets = [
    { label: "Jurisdiction · Brazil", at: layersAt + 0.9, depth: 2, fill: "rgba(102, 128, 88, 0.10)", stroke: "rgba(102, 128, 88, 0.55)" },
    { label: "Language · EN / PT-BR", at: layersAt, depth: 1, fill: palette.surface, stroke: palette.line },
  ];
  const validity = progress(t, legendAt + 0.6, 0.8);

  return <div style={{ position: "absolute", inset: 0, opacity: fade }}>
    {sheets.map(sheet => {
      const shift = keyframes(t, [[sheet.at, 0], [sheet.at + 1.1, OFFSET * sheet.depth]]);
      const visible = progress(t, sheet.at, 0.3);
      if (visible <= 0) return null;
      return <Abs key={sheet.label} x={FRAME.x + shift} y={FRAME.y - shift} w={FRAME.w} h={FRAME.h}
        style={{ background: sheet.fill, border: `2px solid ${sheet.stroke}`, borderRadius: 14, opacity: visible }}>
        <div style={{ position: "absolute", left: 22, top: 12, opacity: progress(t, sheet.at + 0.8, 0.5) }}>
          <Label size={28} tracking={2.6} color={palette.text}>{sheet.label}</Label>
        </div>
      </Abs>;
    })}
    <Abs x={FRAME.x} y={FRAME.y} w={FRAME.w} h={FRAME.h} style={{ background: palette.background, borderRadius: 14, opacity: frameDraw > 0 ? 1 : 0 }}/>
    <Svg>
      <Draw d={`M${FRAME.x + 14} ${FRAME.y} H${FRAME.x + FRAME.w - 14} Q${FRAME.x + FRAME.w} ${FRAME.y} ${FRAME.x + FRAME.w} ${FRAME.y + 14} V${FRAME.y + FRAME.h - 14} Q${FRAME.x + FRAME.w} ${FRAME.y + FRAME.h} ${FRAME.x + FRAME.w - 14} ${FRAME.y + FRAME.h} H${FRAME.x + 14} Q${FRAME.x} ${FRAME.y + FRAME.h} ${FRAME.x} ${FRAME.y + FRAME.h - 14} V${FRAME.y + 14} Q${FRAME.x} ${FRAME.y} ${FRAME.x + 14} ${FRAME.y}`}
        p={frameDraw} stroke={validity > 0 ? palette.accent : palette.shape} width={2 + validity}/>
      <circle cx={NODE.x} cy={NODE.y} r={NODE.r + 26} fill="none" stroke={palette.shape} strokeOpacity={0.3 * node} strokeWidth={1.5}/>
      <circle cx={NODE.x} cy={NODE.y} r={NODE.r * (0.7 + 0.3 * node)} fill={palette.shape} opacity={node}/>
    </Svg>
    <Abs x={FRAME.x + 26} y={FRAME.y + 22} style={{ opacity: progress(t, 1.2, 0.6) }}><Label size={28} tracking={2.6}>Evaluation framework</Label></Abs>
    <Abs x={NODE.x - 150} y={NODE.y + NODE.r + 42} w={300} style={{ textAlign: "center", opacity: node }}><Label size={30} color={palette.text}>Model</Label></Abs>
    <Appear t={t} at={legendAt} until={end} x={FRAME.x} y={FRAME.y + FRAME.h + 48} w={700}>
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <span style={{ width: 30, height: 30, borderRadius: "50%", background: palette.shape }}/>
        <Rich text="Model behavior" size={40} weight={600}/>
      </div>
    </Appear>
    <Appear t={t} at={legendAt + 0.6} until={end} x={FRAME.x} y={FRAME.y + FRAME.h + 108} w={700}>
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <span style={{ width: 30, height: 30, borderRadius: 7, border: `3px solid ${palette.accent}` }}/>
        <Rich text="Measurement validity" size={40} weight={600}/>
      </div>
    </Appear>
  </div>;
}

export function QuestionScene() {
  const t = useTime();
  const palette = usePalette();
  return <>
    <LayeredModel t={t} layersAt={question.at + 0.9} legendAt={scope.at + 0.8} end={C.end}/>
    <Appear t={t} at={0.5} until={title.end} x={120} y={330} w={900}><Label size={34}>Project overview</Label></Appear>
    <Appear t={t} at={0.8} until={title.end} x={120} y={384} w={900}>
      <Rich text={title.heading!} size={type.display} weight={650} tracking={-5.5}/>
    </Appear>
    <Appear t={t} at={1.5} until={title.end} x={120} y={560} w={820}>
      <Rich text={title.text} size={type.body} color={palette.secondary}/>
    </Appear>
    <Appear t={t} at={question.at + 0.25} until={question.end} x={120} y={300} w={860}>
      <Rich text={question.text} size={78} weight={500}/>
    </Appear>
    <Appear t={t} at={scope.at + 0.25} until={C.end} x={120} y={330} w={860}>
      <Rich text={scope.text} size={type.statement}/>
    </Appear>
  </>;
}
