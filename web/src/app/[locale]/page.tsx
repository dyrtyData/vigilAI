import { ArrowDown, ArrowRight, ArrowUpRight, BookOpen, Braces, FileCheck2, Github, Globe2, Scale, Trophy } from "lucide-react";
import { BrandMark } from "@/components/identity";
import { Button } from "@/components/ui/button";
import { ScrollStory } from "@/components/scroll-story";
import { BenchmarkExplorer } from "@/components/benchmark-explorer";
import { FilmTranscript } from "@/components/film-transcript";
import { ProjectFilm } from "@/components/project-film";
import { brand, disclosureResults, links, researchRevision } from "@/lib/content";
import { getTranslator, isLocale } from "@/lib/i18n";
import { LanguageSwitch } from "@/components/language-switch";
import { notFound } from "next/navigation";

export default async function Home({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = getTranslator(locale);
  return <>
    <a href="#main" className="skip-link">{t("Skip to content")}</a>
    <header className="site-header shell">
      <a className="wordmark" href="#" aria-label={`${brand.name} — ${t("Home")}`}><BrandMark/><span>{brand.name}</span></a>
      <nav aria-label={t("Main navigation")}><a href="#overview">{t("Overview")}</a><a href="#story">{t("Methods")}</a><a href="#benchmarks">{t("Benchmarks")}</a><a href="#research">{t("Findings")}</a></nav>
      <div className="header-actions"><LanguageSwitch locale={locale}/><Button asChild variant="outline" size="sm"><a href={links.repository}><Github size={15}/><span>{t("View on GitHub")}</span><ArrowUpRight size={14}/></a></Button></div>
    </header>
    <main id="main">
      <section className="hero shell" aria-labelledby="hero-heading">
        <div className="hero-copy"><div className="eyebrow"><span className="status-dot"/>{t("RESEARCH SUMMARY / REVISED ANALYSIS")}</div>
          <h1 id="hero-heading">{t("Evaluating AI")}<br/>{t("against Brazil’s")}<br/><em>{t("rights framework.")}</em></h1>
          <p>{t("Vigil AI adapts COMPL-AI to evaluate language-model responses against criteria mapped to Brazil’s PL 2338/2023. The study examines both model behavior and the validity of the instruments used to measure it.")}</p>
          <div className="hero-actions"><Button asChild><a href="#research">{t("Read the findings")}{" "}<ArrowUpRight size={17}/></a></Button><a className="text-link" href="#benchmarks">{t("Explore the benchmarks")}{" "}<ArrowDown size={15}/></a></div>
        </div>
        <div className="hero-art hero-film-art"><div className="award-badge"><span className="award-icon"><Trophy size={17} strokeWidth={1.4}/></span><span><strong>{t("Top 25%")}</strong><small>{t("Global South AI Safety Hackathon")}</small></span><a href={links.project} aria-label={t("View the project submission on Apart Research")}><ArrowUpRight size={17}/></a></div><ProjectFilm locale={locale}/></div>
        <div className="hero-bottom"><span>{t("RESEARCH INFRASTRUCTURE")}</span><div><a href={links.complai}>{t("COMPL-AI")}{" "}<ArrowUpRight size={11}/></a><span className="foundation-divider"/><a href={links.inspect}>{t("Inspect AI")}{" "}<ArrowUpRight size={11}/></a></div><span className="hero-bottom-note">{t("Brazil PL 2338/2023 · English / Portuguese")}</span></div>
      </section>
      <section className="intro-strip shell" aria-label={t("Study scope")}><div><strong>30<span>+</span>5</strong><p>{t("Preserved upstream tasks")}<br/>{t("and Brazil-specific additions")}</p></div><div><strong>2</strong><p>{t("Models in the corrected")}<br/>{t("frontier-model analysis")}</p></div><div><Braces strokeWidth={1.2} size={33}/><p>{t("Deterministic scoring")}<br/>{t("with documented cross-checks")}</p></div><div><Globe2 strokeWidth={1.2} size={33}/><p>{t("English and Portuguese")}<br/>{t("evaluation conditions")}</p></div></section>
      <section className="abstract-section shell" aria-labelledby="abstract-heading">
        <div><span className="eyebrow">{t("STUDY OVERVIEW")}</span><h2 id="abstract-heading">{t("Abstract")}</h2></div>
        <div className="abstract-copy">
          <p>{t("This study investigates the adaptation of an EU-oriented language-model evaluation suite to Brazilian rights-based criteria. Vigil AI preserves 30 COMPL-AI tasks and introduces five instruments addressing disclosure, non-discrimination, explanation, contestation and algorithmic impact assessment. An audit of scoring targets, response parsing and baseline composition identified measurement defects that invalidated the originally reported disclosure and bias gaps.")}</p>
          <p>{t("Corrected evaluations of Claude Haiku 4.5 and Claude Sonnet 4.6 do not support the original large disclosure gap. Comparisons on matched demographic axes likewise do not establish greater bias on the Brazilian benchmark. The resulting contribution is a documented evaluation framework and an empirical account of how measurement errors can alter cross-context conclusions. Native-annotator validation and corrected replications on the four open-weight models remain outstanding.")}</p>
          <div className="abstract-keywords"><strong>{t("Keywords")}</strong>{" "}{t("AI evaluation · measurement validity · multilingual benchmarks · Brazilian AI governance")}</div>
        </div>
      </section>
      <section className="film-transcript-section shell" aria-label={t("Research film transcript")}>
        <FilmTranscript locale={locale}/>
      </section>
      <ScrollStory locale={locale}/>
      <section id="benchmarks" className="benchmarks-section shell" aria-labelledby="benchmarks-heading"><div className="section-heading"><div><span className="eyebrow">{t("02 / EVALUATION INSTRUMENTS")}</span><h2 id="benchmarks-heading">{t("Operationalizing")}<br/><em>{t("rights-based criteria.")}</em></h2></div><p>{t("Five tasks translate the project’s legal mapping into response-level evaluation criteria. The examples below illustrate each construct; they are not scored experimental observations.")}</p></div><BenchmarkExplorer locale={locale}/></section>
      <section id="research" className="research-section" aria-labelledby="research-heading"><div className="shell"><div className="section-heading"><div><span className="eyebrow">{t("03 / RESULTS AND INTERPRETATION")}</span><h2 id="research-heading">{t("Findings from")}<br/><em>{t("the corrected evaluation.")}</em></h2></div><p>{t("The results below summarize the documented reanalysis of two frontier models. They do not extend the corrected conclusions to the original six-model panel.")}</p></div>
        <div className="results-table-wrap" role="region" aria-label={t("Corrected disclosure results")} tabIndex={0}>
          <table className="results-table">
            <caption>{t("AI disclosure — corrected benchmark scores")}</caption>
            <thead><tr><th scope="col">{t("Model")}</th><th scope="col">{t("Brazil task")}</th><th scope="col">{t("EU task")}</th><th scope="col">{t("Δ Brazil − EU")}</th></tr></thead>
            <tbody>{disclosureResults.map(result => <tr key={result.model}><th scope="row"><a href={result.source}>{result.model} <ArrowUpRight size={12}/></a></th><td>{result.brazil}</td><td>{result.eu}</td><td>{result.delta}</td></tr>)}</tbody>
          </table>
        </div>
        <p className="results-note">{t("Values are means ± standard error as reported in the corrected run summaries; they are not confidence intervals. The Brazil task combines English and Portuguese items. Sonnet’s residual misses include disclosures rejected because of answer formatting. These scores do not establish legal compliance or equivalence between languages.")}</p>
        <div className="principles-grid">
          <article><span className="principle-icon"><Braces size={23} strokeWidth={1.3}/></span><span className="mini-label">{t("FINDING 01 / DISCLOSURE")}</span><h3>{t("The original gap was a scoring artifact.")}</h3><p>{t("The original disclosure-gap finding was retracted: Portuguese responses beginning with “NÃO” were compared with the English target “NO.” Language-specific targets removed the reported gap of approximately 0.45 in the corrected two-model analysis.")}</p><a href={links.corrections}>{t("Read the retraction and reanalysis")}{" "}<ArrowUpRight size={15}/></a></article>
          <article><span className="principle-icon"><Scale size={23} strokeWidth={1.3}/></span><span className="mini-label">{t("FINDING 02 / COMPARABILITY")}</span><h3>{t("Baseline composition changes the result.")}</h3><p>{t("After parser correction and demographic-axis matching, Brazil-minus-EU accuracy differences were +0.218 ± 0.030 for Haiku and +0.005 ± 0.026 for Sonnet (scenario-clustered standard errors). These are differences between benchmarks; item construction and language remain confounded.")}</p><a href={links.census}>{t("Inspect the matched-axis analysis")}{" "}<ArrowUpRight size={15}/></a></article>
          <article><span className="principle-icon"><FileCheck2 size={23} strokeWidth={1.3}/></span><span className="mini-label">{t("FINDING 03 / SCORER VALIDITY")}</span><h3>{t("Determinism does not establish validity.")}</h3><p>{t("Adversarial probes identified rubric credit for unrelated text, while the original impact-assessment prompt exposed much of its own answer key. Revised detectors and guided–unguided conditions address these defects; LLM-judge cross-checks remain separate from human validation.")}</p><a href={links.corrections}>{t("Review the measurement audit")}{" "}<ArrowUpRight size={15}/></a></article>
        </div>
        <div className="research-provenance"><span>{t("Evidence snapshot")}{" "}<code>{researchRevision.slice(0, 7)}</code>{" "}{t("· iteration-2 · Reanalysis dated July 26, 2026")}</span><a href={links.corrections}>{t("Versioned results")}{" "}<ArrowUpRight size={13}/></a></div>
        <div className="limitations-note"><strong>{t("Limits of inference.")}</strong>{" "}{t("The corrected results cover two models. The Brazilian bias scenarios have not undergone native-annotator validation. Matching demographic axes does not control item difficulty, and nationality is only an approximate counterpart to internal regional prejudice. Response-level rubric coverage does not demonstrate that an organization implements the corresponding rights.")}{" "}<a href={links.participation}>{t("Participation protocol")}{" "}<ArrowUpRight size={12}/></a></div>
      </div></section>
      <section className="origin-section shell" aria-labelledby="origin-heading"><div className="origin-seal"><Trophy size={31} strokeWidth={1}/><strong>{t("Top 25")}<span>%</span></strong><span>{t("GLOBAL SOUTH")}<br/>{t("AI SAFETY HACKATHON")}</span><small>{t("2026 · TEAM ONÇAI")}</small></div><div className="origin-copy"><span className="eyebrow">{t("04 / PROJECT PROVENANCE")}</span><h2 id="origin-heading">{t("Research context")}<br/><em>{t("and attribution.")}</em></h2><p>{t("Vigil AI was presented at the Global South AI Safety Hackathon in June 2026. The project submission lists Diana Chang, Ian Duhamel Hayes and Pedro Quezada as Team OnçAI. The Top 25% recognition refers to that submission; the corrected analysis is documented separately.")}</p><a className="text-link" href={links.project}>{t("View the original submission")}{" "}<ArrowUpRight size={16}/></a><div className="lineage-note"><BookOpen size={17}/><p>{t("The evaluation framework is a fork of")}{" "}<a href={links.complai}>{t("COMPL-AI")}</a>{t(", developed by ETH Zurich, INSAIT and LatticeFlow AI, and uses Inspect AI. Attribution identifies the upstream research infrastructure and does not imply institutional endorsement.")}</p></div></div></section>
      <section className="closing-section shell"><span className="eyebrow">{t("RESEARCH MATERIALS")}</span><h2>{t("Methods, results")}<br/><em>{t("and revision record.")}</em></h2><p>{t("Examine the source, corrected run summaries and measurement audit.")}<br/>{t("The manuscript remains under revision to reconcile historical claims with the corrected evidence.")}</p><div><Button asChild><a href={links.corrections}>{t("Read the corrected results")}{" "}<ArrowUpRight size={17}/></a></Button><Button asChild variant="ghost"><a href={links.repository}>{t("Inspect the source")}{" "}<ArrowRight size={17}/></a></Button></div><BrandMark className="closing-mark"/></section>
    </main>
    <footer className="site-footer shell"><div className="footer-top"><a className="wordmark" href="#"><BrandMark/><span>{brand.name}</span></a><p>{t(brand.descriptor)}</p><a href={links.repository}>{t("Research source")}{" "}<ArrowUpRight size={13}/></a></div><div className="footer-bottom"><span>{t("© 2026 · Vigil AI · Research summary")}</span><p>{t("Research prototype, not legal certification. PL 2338/2023 remains a bill; article references follow the project’s version-specific mapping.")}{" "}<a href={links.bill}>{t("Legislative status")}{" "}<ArrowUpRight size={11}/></a></p></div></footer>
  </>;
}
