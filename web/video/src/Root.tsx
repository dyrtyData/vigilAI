import { Composition, Still } from "remotion";
import { brand } from "../../src/lib/content.ts";
import { Poster } from "./Poster";
import { ProjectOverview, type FilmProps } from "./ProjectOverview";
import { DURATION_FRAMES, FPS, overviewFilm } from "./script";

// The project name is a working name: override it at render time with
// --props='{"projectName":"…"}' or change `brand.name` in web/src/lib/content.ts.
const defaultProps: FilmProps = { projectName: brand.name, withAudio: true };

export function RemotionRoot() {
  return <>
    <Composition id="ProjectOverview" component={ProjectOverview} durationInFrames={DURATION_FRAMES} fps={FPS}
      width={overviewFilm.width} height={overviewFilm.height} defaultProps={defaultProps}/>
    <Still id="Poster" component={Poster} width={overviewFilm.width} height={overviewFilm.height} defaultProps={defaultProps}/>
  </>;
}
