"use client";

import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent } from "react";
import { Maximize2, Pause, Play, RotateCcw, Volume2, VolumeX, X } from "lucide-react";
import { formatTimestamp, overviewChapters, overviewFilm } from "@/lib/project-overview";
import { getTranslator, type Locale } from "@/lib/i18n";

const duration = overviewFilm.durationSeconds;
const SKIP = 5;

function chapterAt(seconds: number) {
  return overviewChapters.reduce((current, chapter, index) => (seconds >= chapter.start ? index : current), 0);
}

/** Poster-first player for the project-overview film. Nothing loads or plays until the visitor asks. */
export function ProjectFilm({ locale = "en" }: { locale?: Locale }) {
  const t = getTranslator(locale);
  const video = useRef<HTMLVideoElement>(null);
  const player = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const [opened, setOpened] = useState(false);
  const pendingSeek = useRef<number | null>(null);
  const [attached, setAttached] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [ended, setEnded] = useState(false);
  const [time, setTime] = useState(0);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [reducedMotion, setReducedMotion] = useState(false);
  const active = chapterAt(time);

  useEffect(() => {
    if (!opened) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previous; };
  }, [opened]);

  function openFilm() {
    player.current?.showModal();
    setOpened(true);
    void play();
  }

  function closeFilm() {
    video.current?.pause();
    if (document.fullscreenElement === player.current) void document.exitFullscreen().catch(() => {});
    player.current?.close();
  }

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  // With reduced motion the transcript is the primary way in, so it starts expanded.
  useEffect(() => {
    const transcript = document.getElementById("film-transcript");
    if (reducedMotion && transcript instanceof HTMLDetailsElement) transcript.open = true;
  }, [reducedMotion]);

  function element() {
    const current = video.current!;
    if (!attached) {
      const connection = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection;
      const compact = window.matchMedia("(max-width: 900px)").matches || connection?.saveData;
      current.src = compact ? overviewFilm.media.web : overviewFilm.media.full;
      current.volume = volume;
      setAttached(true);
    }
    return current;
  }

  function seek(seconds: number) {
    const target = Math.min(duration, Math.max(0, seconds));
    const current = element();
    if (current.readyState >= HTMLMediaElement.HAVE_METADATA) current.currentTime = target;
    else pendingSeek.current = target;
    setTime(target);
    setEnded(false);
  }

  async function play(from?: number) {
    const current = element();
    if (from !== undefined) seek(from);
    else if (current.ended) seek(0);
    try { await current.play(); } catch { setPlaying(false); }
  }

  function toggle() {
    if (playing) video.current?.pause();
    else void play();
  }

  function toggleMute() {
    const current = element();
    current.muted = !current.muted;
    if (!current.muted && current.volume === 0) current.volume = 0.6;
  }

  function changeVolume(value: number) {
    const current = element();
    current.volume = value;
    current.muted = value === 0;
  }

  async function fullscreen() {
    const target = player.current;
    // The viewport-sized dialog remains usable when native fullscreen is unavailable.
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else if (target?.requestFullscreen) await target.requestFullscreen();
    } catch { /* Keep the dialog and its chapter navigation open. */ }
  }

  function onKeyDown(event: KeyboardEvent<HTMLDialogElement>) {
    const target = event.target as HTMLElement;
    const onRange = target instanceof HTMLInputElement && target.type === "range";
    const onButton = target.tagName === "BUTTON";
    switch (event.key) {
      case " ":
        if (onButton) return;
        event.preventDefault();
        toggle();
        break;
      case "k": case "K":
        event.preventDefault();
        toggle();
        break;
      case "ArrowLeft": case "ArrowRight":
        if (onRange) return;
        event.preventDefault();
        seek(time + (event.key === "ArrowLeft" ? -SKIP : SKIP));
        break;
      case "m": case "M":
        event.preventDefault();
        toggleMute();
        break;
      case "f": case "F":
        event.preventDefault();
        void fullscreen();
        break;
    }
  }

  const chapter = overviewChapters[active];

  return <>
    <div id="overview" className="hero-film">
      <button ref={trigger} type="button" className="hero-film-preview" onClick={openFilm}
        aria-label={t("Play the overview")} aria-haspopup="dialog" aria-controls="film-dialog">
        {/* Local poster: no video download or audio before the visitor presses play. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={overviewFilm.media.poster} width={1920} height={1080} alt="" fetchPriority="high"/>
        <span className="hero-film-play"><Play size={22} fill="currentColor" aria-hidden="true"/></span>
        <span className="hero-film-caption"><strong>{t("Watch the research film")}</strong><span>{formatTimestamp(duration)} <span aria-hidden="true">↗</span></span></span>
      </button>
      {locale === "pt-br" && <p className="film-language-note">{t("Video in English · Portuguese transcript below.")}</p>}
      <div className="hero-film-note"><span>{t("THE QUESTION. THE EVIDENCE. THE LIMITS.")}</span><a href="#film-transcript">{t("Read transcript ↗")}</a></div>
    </div>
    <dialog id="film-dialog" className="film-dialog" ref={player} aria-labelledby="film-dialog-title"
      onKeyDown={onKeyDown} onCancel={closeFilm}
      onClose={() => { video.current?.pause(); setOpened(false); trigger.current?.focus({ preventScroll: true }); }}>
      <header className="film-dialog-header"><div><span className="eyebrow">{t("PROJECT OVERVIEW /")}{" "}{formatTimestamp(duration)}</span><h2 id="film-dialog-title">{t("The research film")}</h2></div>
        <button autoFocus type="button" className="film-close" onClick={closeFilm} aria-label={t("Close film")}><span>{t("Close")}</span><X size={21}/></button>
      </header>
      {locale === "pt-br" && <p className="film-language-note">{t("Video in English · Portuguese transcript below.")}</p>}
      <div className="film-dialog-content"><div className="film-layout">
    <div className={`film-player ${attached ? "is-attached" : ""}`}>
      <div className="film-frame">
        <video lang="en" ref={video} poster={overviewFilm.media.poster} preload="none" playsInline aria-label={t("Project overview film")}
          aria-describedby="film-keyboard-hint" onClick={toggle}
          onPlay={() => { setPlaying(true); setEnded(false); }} onPause={() => setPlaying(false)}
          onEnded={() => { setPlaying(false); setEnded(true); }}
          onTimeUpdate={event => setTime(event.currentTarget.currentTime)}
          onVolumeChange={event => { setMuted(event.currentTarget.muted); setVolume(event.currentTarget.volume); }}
          onLoadedMetadata={event => {
            if (pendingSeek.current !== null) { event.currentTarget.currentTime = pendingSeek.current; pendingSeek.current = null; }
          }}>{t("Your browser cannot play this video. The transcript below contains the complete narrative.")}</video>
        {ended && <div className="film-ended">
          <button type="button" onClick={() => void play(0)}><RotateCcw size={17} aria-hidden="true"/>{t("Replay the overview")}</button>
        </div>}
      </div>
      <div className="film-controls" role="group" aria-label={t("Film controls")}>
        <button type="button" className="film-button" onClick={toggle} aria-label={playing ? t("Pause") : t("Play")}>
          {playing ? <Pause size={18} aria-hidden="true"/> : <Play size={18} aria-hidden="true"/>}
        </button>
        <button type="button" className="film-button" onClick={() => void play(0)} aria-label={t("Replay from the beginning")}>
          <RotateCcw size={17} aria-hidden="true"/>
        </button>
        <span className="film-time"><span>{formatTimestamp(time)}</span> / {formatTimestamp(duration)}</span>
        <div className="film-seek">
          <input type="range" min={0} max={duration} step={1} value={Math.floor(time)} aria-label={t("Seek")}
            aria-valuetext={`${formatTimestamp(time)} ${t("of")} ${formatTimestamp(duration)}, ${t("chapter")} ${chapter.number}: ${t(chapter.title)}`}
            onChange={event => seek(Number(event.target.value))}
            style={{ "--film-progress": `${(time / duration) * 100}%` } as CSSProperties}/>
          <span className="film-ticks" aria-hidden="true">{overviewChapters.slice(1).map(item => <span key={item.id} style={{ left: `${(item.start / duration) * 100}%` }}/>)}</span>
        </div>
        <button type="button" className="film-button" onClick={toggleMute} aria-label={muted ? t("Unmute") : t("Mute")} aria-pressed={muted}>
          {muted || volume === 0 ? <VolumeX size={18} aria-hidden="true"/> : <Volume2 size={18} aria-hidden="true"/>}
        </button>
        <input type="range" className="film-volume" min={0} max={1} step={0.05} value={muted ? 0 : volume} aria-label={t("Volume")}
          aria-valuetext={`${Math.round((muted ? 0 : volume) * 100)}%`} onChange={event => changeVolume(Number(event.target.value))}/>
        <button type="button" className="film-button film-fullscreen" onClick={() => void fullscreen()} aria-label={t("Full screen")}>
          <Maximize2 size={16} aria-hidden="true"/>
        </button>
      </div>
      <p id="film-keyboard-hint" className="film-hint">{t("Keyboard: Space or K plays and pauses, ← and → move 5 seconds, M mutes, F toggles full screen, Esc closes the viewer. Sound starts only when you press play.")}{reducedMotion && <>{" "}{t("Reduced motion is on: the film contains animated transitions, and the transcript below is open with the complete narrative.")}</>}
      </p>
    </div>
    <nav className="film-chapters" aria-label={t("Film chapters")}>
      <span className="eyebrow film-chapters-label">{t("EXPLORE THE CHAPTERS")}</span>
      <ol>
        {overviewChapters.map((item, index) => <li key={item.id}>
          <button type="button" onClick={() => void play(item.start)} aria-current={attached && index === active ? "true" : undefined}
            aria-label={`${t("Play chapter")} ${item.number}, ${t(item.title)}, ${t("from")} ${formatTimestamp(item.start)}`}>
            <span className="film-chapter-number">{item.number}</span>
            <span className="film-chapter-title">{t(item.title)}</span>
            <span className="film-chapter-time">{formatTimestamp(item.start)}</span>
          </button>
        </li>)}
      </ol>
    </nav>
  </div></div>
    </dialog>
  </>;
}
