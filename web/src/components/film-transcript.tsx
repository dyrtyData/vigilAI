import { brand, links, researchRevision } from "@/lib/content";
import { emphasisRuns, fillName, formatTimestamp, overviewChapters, type OverviewTable } from "@/lib/project-overview";
import { getTranslator, type Locale } from "@/lib/i18n";

function Narrative({ text }: { text: string }) {
  return <>{emphasisRuns(fillName(text, brand.name)).map((run, index) => run.em ? <em key={index}>{run.text}</em> : <span key={index}>{run.text}</span>)}</>;
}

function Table({ table, locale }: { table: OverviewTable; locale: Locale }) {
  const t = getTranslator(locale);
  return <div className="transcript-table-wrap">
    <table className="transcript-table">
      <caption>{t(table.caption)}</caption>
      <thead><tr>{table.columns.map((column, index) => <th key={index} scope="col">{t(column) || <span className="visually-hidden">{t("Measure")}</span>}</th>)}</tr></thead>
      <tbody>{table.rows.map(row => <tr key={t(row[0])}><th scope="row">{t(row[0])}</th>{row.slice(1).map((cell, index) => <td key={index}>{cell}</td>)}</tr>)}</tbody>
    </table>
    <p className="transcript-visual">{t(table.note)}</p>
  </div>;
}

/** The complete on-screen narrative of the film as HTML, generated from the same script as the video. */
export function FilmTranscript({ locale = "en" }: { locale?: Locale }) {
  const t = getTranslator(locale);
  return <details id="film-transcript" className="film-transcript">
    <summary><span>{t("Transcript")}</span><small>{t("Complete on-screen narrative, figures and credits")}</small></summary>
    {locale === "pt-br" && <p className="film-language-note">{t("Video in English · Portuguese transcript below.")}</p>}
    <div className="transcript-body">
      {overviewChapters.map(chapter => <section key={chapter.id} aria-labelledby={`transcript-${chapter.id}`}>
        <h3 id={`transcript-${chapter.id}`}><span>{chapter.number}</span>{t(chapter.title)}<time dateTime={`PT${chapter.start}S`}>{formatTimestamp(chapter.start)}–{formatTimestamp(chapter.end)}</time></h3>
        {chapter.beats.map(beat => <div key={beat.id} className="transcript-beat">
          {beat.heading && <h4>{fillName(t(beat.heading), brand.name)}</h4>}
          {beat.text && <p><Narrative text={t(beat.text)}/></p>}
          {beat.items && <ul>{beat.items.map(item => <li key={item}><Narrative text={t(item)}/></li>)}</ul>}
          {beat.table && <Table table={beat.table} locale={locale}/>}
          {beat.visual && <p className="transcript-visual"><span>{t("On screen")}</span>{fillName(t(beat.visual), brand.name)}</p>}
        </div>)}
      </section>)}
      <p className="transcript-sources">{t("Figures are transcribed from versioned research artifacts at evidence snapshot")}<code>{researchRevision.slice(0, 7)}</code>:{" "}
        <a href={links.corrections}>{t("results and retractions")}</a>, <a href={links.haiku}>{t("Haiku 4.5")}</a>{" "}{t("and")}{" "}<a href={links.sonnet}>{t("Sonnet 4.6")}</a>{" "}{t("run summaries, and the")}{" "}<a href={links.census}>{t("matched-axis census")}</a>{t(". The source code is in the")}<a href={links.repository}>{t("repository")}</a>{t(". Music: original instrumental composition, synthesized in code for this film.")}</p>
    </div>
  </details>;
}
