import { AbsoluteFill } from "remotion";
import { Abs, Label, NameContext, PaletteContext, Rich } from "./components/primitives";
import { loadFonts } from "./fonts";
import type { FilmProps } from "./ProjectOverview";
import { LayeredModel } from "./scenes/s1-question";
import { beat, overviewFilm } from "./script";
import { light, palettes, type } from "./theme";

loadFonts();

const question = beat("question", "question");
const minutes = Math.floor(overviewFilm.durationSeconds / 60);
const seconds = overviewFilm.durationSeconds % 60;

/** Poster frame for the website player: the title, the research question and the layered model. */
export function Poster({ projectName }: FilmProps) {
  return <NameContext.Provider value={projectName}>
    <PaletteContext.Provider value={palettes.light}>
      <AbsoluteFill style={{ background: light.background }}>
        <LayeredModel t={9.6} layersAt={5.4} legendAt={99} end={99}/>
        <Abs x={120} y={200} w={900}><Label size={32}>Project overview · {minutes} min {seconds} s</Label></Abs>
        <Abs x={120} y={252} w={900}><Rich text="{name}" size={type.display} weight={650} tracking={-5.5}/></Abs>
        <Abs x={120} y={470} w={860}><Rich text={question.text} size={70}/></Abs>
      </AbsoluteFill>
    </PaletteContext.Provider>
  </NameContext.Provider>;
}
