import { useCallback, useEffect, useState } from "react";
import { MotionConfig } from "framer-motion";
import type { Stage } from "./api/types";
import { useDemo } from "./hooks/useDemo";
import { StagePanel } from "./components/StagePanel";
import { ContextInspector } from "./components/ContextInspector";
import { CompareView } from "./components/CompareView";
import { DataSection } from "./components/DataSection";

type View = "demo" | "compare";

const TONES: Record<Stage, string> = { 1: "red", 2: "amber", 3: "green", 4: "red" };

function isTyping(target: EventTarget | null) {
  return target instanceof HTMLElement && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

export default function App() {
  const demo = useDemo();
  const [view, setView] = useState<View>("demo");
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const onScroll = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(max > 0 ? window.scrollY / max : 0);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey || view !== "demo") return;
      if (e.code === "Space") {
        e.preventDefault();
        demo.run();
      } else if (e.key === "ArrowRight") {
        demo.next();
      } else if (e.key === "ArrowLeft") {
        demo.prev();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [demo, view]);

  const reset = useCallback(() => {
    demo.reset();
    setView("demo");
    document.getElementById("demo")?.scrollIntoView({ behavior: "smooth" });
  }, [demo]);

  const stages = demo.question?.stages ?? [];
  const info = stages[demo.stage - 1];

  return (
    <MotionConfig reducedMotion="user">
      <div className="progress" style={{ transform: `scaleX(${progress})` }} />

      <header className="topbar">
        <a className="brand" href="#top">
          <b>✦</b> Prompt vs Context
        </a>
        <div className="view-toggle" role="tablist" aria-label="View">
          <button role="tab" aria-selected={view === "demo"} className={view === "demo" ? "on" : ""} onClick={() => setView("demo")}>
            <span>01</span> Demo
          </button>
          <button role="tab" aria-selected={view === "compare"} className={view === "compare" ? "on" : ""} onClick={() => setView("compare")}>
            <span>02</span> Compare
          </button>
          <i className={`view-thumb ${view === "compare" ? "right" : ""}`} aria-hidden="true" />
        </div>
        <div className="top-actions">
          <button className="btn ghost small" onClick={reset}>
            Reset
          </button>
        </div>
      </header>

      <header className="hero" id="top">
        <div className="aurora" aria-hidden="true">
          <span className="orb o1" />
          <span className="orb o2" />
          <span className="orb o3" />
        </div>
        <div className="hero-grid-bg" aria-hidden="true" />
        <div className="hero-main">
          <div className="badge">✦ One question. Four ways to ask it.</div>
          <h1>
            Prompt vs <span className="grad">Context</span>
          </h1>
          <p className="hero-sub">
            A better prompt makes the AI more honest. Only the right data makes it right. Watch one question go through four
            stages, from a weak prompt to the right context to too much context.
          </p>
          <div className="hero-cta">
            <a className="btn big" href="#demo">
              Run the demo →
            </a>
            <a className="btn ghost big" href="#data">
              See the data
            </a>
          </div>
          <div className="hero-stats">
            <div>
              <b>1</b>
              <span>question</span>
            </div>
            <div>
              <b>4</b>
              <span>stages</span>
            </div>
            <div>
              <b>50</b>
              <span>tables</span>
            </div>
          </div>
        </div>
      </header>

      <main>
        <section id="demo" className="section">
          <div className="section-head">
            <div className="section-num">{view === "demo" ? "01" : "02"}</div>
            <div>
              <div className="kicker">{view === "demo" ? "Live demo · the experiment" : "The closing shot"}</div>
              <h2>{view === "demo" ? "Same question, four stages" : "Four answers, side by side"}</h2>
            </div>
          </div>

          {demo.bootError && (
            <div className="stage-card error-card" role="alert">
              <b>Can't load the demo</b>
              <p>{demo.bootError}</p>
              <button className="btn" onClick={demo.boot}>
                Try again
              </button>
            </div>
          )}

          {demo.question && (
            <div className="question-bubble" aria-label="The question">
              <span className="who">You asked</span>
              <p>{demo.question.question}</p>
              <span className="translation">{demo.question.english}</span>
            </div>
          )}

          {demo.question && view === "compare" && (
            <CompareView stages={stages} results={demo.results} errors={demo.errors} onNeedResults={demo.runMissing} />
          )}

          {demo.question && view === "demo" && info && (
            <div className="demo-layout">
              <div className="demo-main">
                <ol className="stepper" aria-label="Stages">
                  {stages.map((s) => (
                    <li key={s.stage}>
                      <button
                        className={`step ${s.stage === demo.stage ? "active" : ""} ${demo.results[s.stage] ? `ran tone-${TONES[s.stage]}` : ""}`}
                        aria-current={s.stage === demo.stage ? "step" : undefined}
                        onClick={() => demo.setStage(s.stage)}
                      >
                        <span className="step-num">0{s.stage}</span>
                        <span className="step-title">{s.title}</span>
                      </button>
                    </li>
                  ))}
                </ol>

                <div className="controls">
                  <button className="btn big run" onClick={demo.run} disabled={demo.status[demo.stage] === "loading"}>
                    {demo.status[demo.stage] === "loading" ? "Running…" : demo.results[demo.stage] ? "↻ Run again" : "▶ Run"}
                    <kbd>Space</kbd>
                  </button>
                  <button className="btn ghost big" onClick={demo.next} disabled={demo.stage === 4}>
                    Next stage →<kbd>→</kbd>
                  </button>
                  {demo.stage === 4 && (
                    <div className="trap">
                      <span className="muted">Trap:</span>
                      <div className="tabs">
                        <button className={demo.trap === "most_rows" ? "active" : ""} onClick={() => demo.changeTrap("most_rows")}>
                          biggest table
                        </button>
                        <button className={demo.trap === "newest_dates" ? "active" : ""} onClick={() => demo.changeTrap("newest_dates")}>
                          newest dates
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <StagePanel
                  info={info}
                  result={demo.results[demo.stage]}
                  loading={demo.status[demo.stage] === "loading"}
                  error={demo.errors[demo.stage]}
                  tables={demo.tables}
                  onRetry={demo.run}
                />
              </div>
              <ContextInspector stage={demo.stage} results={demo.results} />
            </div>
          )}
        </section>

        <section id="data" className="section">
          <div className="section-head">
            <div className="section-num">03</div>
            <div>
              <div className="kicker">Under the hood</div>
              <h2>See the data the AI was given</h2>
            </div>
          </div>
          <p className="lead">
            This is the real data behind stage 3. It is generated from an editable file. The AI answers were captured once from the
            exact prompt and context each stage shows, and the app replays them.
          </p>
          <DataSection tables={demo.tables} />
        </section>
      </main>

      <footer className="footer">
        <span>
          <b>✦</b> Prompt vs Context
        </span>
        <span className="muted">Space = run · → = next stage · ← = back</span>
      </footer>
    </MotionConfig>
  );
}
