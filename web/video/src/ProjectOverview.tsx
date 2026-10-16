import { AbsoluteFill, Html5Audio, staticFile } from "remotion";
import { Background, Chrome } from "./components/chrome";
import { NameContext, PaletteContext } from "./components/primitives";
import { loadFonts } from "./fonts";
import { QuestionScene } from "./scenes/s1-question";
import { OriginScene } from "./scenes/s2-origin";
import { BenchmarksScene } from "./scenes/s3-benchmarks";
import { DesignScene } from "./scenes/s4-design";
import { DisclosureScene } from "./scenes/s5-disclosure";
import { ValidityScene } from "./scenes/s6-validity";
import { ImplementationScene } from "./scenes/s7-implementation";
import { LimitationsScene } from "./scenes/s8-limitations";
import { chapter } from "./script";
import { palettes } from "./theme";
import { Span, useTime } from "./time";

loadFonts();

export type FilmProps = { projectName: string; withAudio: boolean };

const scenes = [
  { id: "question", Scene: QuestionScene },
  { id: "origin", Scene: OriginScene },
  { id: "benchmarks", Scene: BenchmarksScene },
  { id: "design", Scene: DesignScene },
  { id: "disclosure", Scene: DisclosureScene },
  { id: "validity", Scene: ValidityScene },
  { id: "implementation", Scene: ImplementationScene },
  { id: "limitations", Scene: LimitationsScene },
] as const;

export function ProjectOverview({ projectName, withAudio }: FilmProps) {
  const t = useTime();
  return <NameContext.Provider value={projectName}>
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <Background t={t}/>
      {scenes.map(({ id, Scene }) => {
        const owner = chapter(id);
        return <Span key={id} start={owner.start} end={owner.end} name={`${owner.number} ${owner.title}`}>
          <PaletteContext.Provider value={palettes[owner.theme]}><Scene/></PaletteContext.Provider>
        </Span>;
      })}
      <Chrome t={t}/>
      {withAudio && <Html5Audio src={staticFile("audio/soundtrack.wav")}/>}
    </AbsoluteFill>
  </NameContext.Provider>;
}
