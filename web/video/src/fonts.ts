import { cancelRender, continueRender, delayRender, staticFile } from "remotion";

// Same files and unicode ranges as the website's @fontsource packages (copied by `pnpm fonts`).
const LATIN = "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD";
const LATIN_EXT = "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF";
const GREEK = "U+0370-0377,U+037A-037F,U+0384-038A,U+038C,U+038E-03A1,U+03A3-03FF";

const faces = [
  { family: "Manrope Film", file: "fonts/manrope-latin.woff2", weight: "200 800", style: "normal", unicodeRange: LATIN },
  { family: "Manrope Film", file: "fonts/manrope-latin-ext.woff2", weight: "200 800", style: "normal", unicodeRange: LATIN_EXT },
  { family: "Manrope Film", file: "fonts/manrope-greek.woff2", weight: "200 800", style: "normal", unicodeRange: GREEK },
  { family: "Instrument Serif Film", file: "fonts/instrument-serif-latin-italic.woff2", weight: "400", style: "italic", unicodeRange: LATIN },
  { family: "Instrument Serif Film", file: "fonts/instrument-serif-latin-ext-italic.woff2", weight: "400", style: "italic", unicodeRange: LATIN_EXT },
];

let loaded = false;

export function loadFonts() {
  if (loaded || typeof document === "undefined") return;
  loaded = true;
  const handle = delayRender("Loading local fonts");
  Promise.all(faces.map(face => {
    const font = new FontFace(face.family, `url(${staticFile(face.file)}) format("woff2")`, { weight: face.weight, style: face.style, unicodeRange: face.unicodeRange });
    document.fonts.add(font);
    return font.load();
  })).then(() => continueRender(handle)).catch(error => cancelRender(error)); // never fall back silently
}
