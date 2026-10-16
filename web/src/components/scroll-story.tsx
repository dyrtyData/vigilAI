"use client";

import { useRef, useState } from "react";
import { motion, useMotionValueEvent, useReducedMotion, useScroll } from "motion/react";
import { ArrowDown, ArrowUpRight, Check, FileText, Fingerprint, Languages, Layers3, ScanLine } from "lucide-react";
import { links } from "@/lib/content";
import { getTranslator, type Locale } from "@/lib/i18n";

const chapters = [
  { title: "Evaluation framework", label: "Evaluation framework", text: "The fork preserves all 30 COMPL-AI tasks and uses Inspect AI to evaluate model responses within a shared execution framework." },
  { title: "Brazil-specific instruments", label: "Brazil-specific instruments", text: "Five additional tasks operationalize disclosure, non-discrimination, explanation, contestation and impact-assessment criteria from the project’s legal mapping." },
  { title: "Measurement validation", label: "Measurement validation", text: "Language-specific targets, parser diagnostics, adversarial scorer probes and baseline composition checks support interpretation of the corrected results." },
];

export function ScrollStory({ locale = "en" }: { locale?: Locale }) {
  const t = getTranslator(locale);
  const container = useRef<HTMLElement>(null);
  const reduceMotion = useReducedMotion();
  const [chapter, setChapter] = useState(0);
  const { scrollYProgress } = useScroll({ target: container, offset: ["start start", "end end"] });
  useMotionValueEvent(scrollYProgress, "change", value => {
    if (!reduceMotion && window.matchMedia("(min-width: 801px)").matches) setChapter(Math.min(2, Math.floor(value * 3)));
  });

  function chooseChapter(index: number) {
    setChapter(index);
    if (!reduceMotion && window.matchMedia("(min-width: 801px)").matches && container.current) {
      const top = container.current.getBoundingClientRect().top + window.scrollY;
      const travel = Math.max(0, container.current.offsetHeight - window.innerHeight);
      window.scrollTo({ top: top + travel * ((index + 0.3) / 3), behavior: "instant" });
    }
  }

  return <section id="story" ref={container} className="scroll-story" aria-labelledby="story-heading">
    <div className="story-sticky">
      <div className="story-topline"><span className="eyebrow light">{t("01 / STUDY DESIGN")}</span><span className="story-scroll-hint">{t("SCROLL THROUGH THE METHODS")}{" "}<ArrowDown size={13}/></span></div>
      <div className="story-grid">
        <div className="story-copy">
          <h2 id="story-heading">{t("Study design.")}<br/><em>{t("Evidence and limits.")}</em></h2>
          <p className="story-intro">{t("Same-model comparisons control the model identity. They do not, by themselves, isolate language, legal framing or scenario difficulty.")}</p>
          <div className="chapters" aria-label={t("Story chapters")}>
            {chapters.map((item, i) => <button key={item.label} type="button" className={`chapter ${chapter === i ? "active" : ""}`} onClick={() => chooseChapter(i)} aria-pressed={chapter === i} aria-controls="story-scene">
              <span className="chapter-number">0{i + 1}</span><span><strong>{t(item.title)}</strong><span className="chapter-description">{t(item.text)}</span></span>
              {chapter === i && <span className="chapter-dot"/>}
            </button>)}
          </div>
        </div>
        <div className="story-visual" id="story-scene" role="region" aria-label={t(chapters[chapter].label)}>
          <div className="scene-top"><span><span className="status-dot"/>{" "}{t("EVALUATION METHODOLOGY")}</span><span>0{chapter + 1} / 03</span></div>
          <motion.div key={chapter} className="scene-content" initial={chapter === 0 || reduceMotion ? false : { opacity: .4, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : .3 }}>
            {chapter === 0 ? <>
              <div className="model-glyph"><Layers3 size={48} strokeWidth={1}/><span>{t("ONE MODEL")}</span></div>
              <div className="connector-line"/>
              <div className="foundation-card"><div><span className="mini-label">{t("THE FOUNDATION")}</span><h3>{t("COMPL-AI")}</h3></div><strong>30<span>{t("original tasks")}</span></strong></div>
              <div className="scene-tags"><span>{t("Inspect AI")}</span><span>{t("API or local model")}</span><span>{t("Open source")}</span></div>
            </> : chapter === 1 ? <>
              <div className="context-title"><Languages size={24} strokeWidth={1.2}/><span>{t("Language and rights-based criteria")}</span></div>
              <div className="context-pair"><span>{t("EN / EU BASELINE")}</span><span className="context-brazil">{t("PT-BR / BRAZIL")}</span></div>
              <div className="context-rows">{[["01", "AI disclosure", "Art. 5, I"], ["02", "Non-discrimination", "Art. 5, III"], ["03", "Explanation", "Art. 6, I"], ["04", "Contestation & review", "Art. 6, II–III"], ["05", "Impact assessment", "Arts. 25–28"]].map(row => <div key={row[0]}><span>{row[0]}</span><strong>{t(row[1])}</strong><small>{row[2]}</small></div>)}</div>
              <p className="scene-caption">{t("Five additions mapped to the project’s Brazilian reference framework.")}</p>
            </> : <>
              <div className="report-heading"><FileText size={25} strokeWidth={1.2}/><div><span className="mini-label">{t("ARTICLE-LEVEL EVIDENCE")}</span><h3>{t("Traceable evaluation records")}</h3></div></div>
              <div className="evidence-row"><Fingerprint size={18}/><span>{t("Model response")}</span><span className="evidence-pill">{t("TRACEABLE")}</span></div>
              <div className="evidence-row"><ScanLine size={18}/><span>{t("Published scoring rule")}</span><span className="evidence-pill">{t("EXPLICIT")}</span></div>
              <div className="evidence-row"><Check size={18}/><span>{t("Article mapping")}</span><span className="evidence-pill">{t("DOCUMENTED")}</span></div>
              <div className="report-note">{t("The unit of observation is a model response.")}<br/>{t("Legal compliance of a deployed system is outside this evaluation’s scope.")}</div>
              <a href={links.corrections} className="scene-link">{t("Read the methods and corrections")}{" "}<ArrowUpRight size={15}/></a>
            </>}
          </motion.div>
          <div className="scene-bottom"><span>{t(chapters[chapter].label)}</span><span>{t("ILLUSTRATED WORKFLOW")}</span></div>
        </div>
      </div>
      <div className="story-progress"><motion.div style={{ scaleX: scrollYProgress }}/></div>
    </div>
  </section>;
}
