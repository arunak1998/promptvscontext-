import { useState } from "react";
import type { RunResponse, Stage } from "../api/types";

interface Props {
  stage: Stage;
  results: Partial<Record<Stage, RunResponse>>;
}

const STAGES: Stage[] = [1, 2, 3, 4];

/** Side panel on desktop, bottom sheet on mobile: how much context each stage sent and what was used. */
export function ContextInspector({ stage, results }: Props) {
  const [open, setOpen] = useState(false);
  const current = results[stage];
  const max = Math.max(1, ...STAGES.map((s) => results[s]?.context.total_est_tokens ?? 0));
  const sources = current?.context.sources.filter((s) => s.kind !== "prompt") ?? [];
  const used = sources.filter((s) => s.used);

  return (
    <aside className={`inspector ${open ? "open" : ""}`} aria-label="Context inspector">
      <button className="inspector-handle" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <span>Context inspector</span>
        <b>{current ? `~${current.context.total_est_tokens.toLocaleString()} tokens` : "–"}</b>
        <i aria-hidden="true">{open ? "▾" : "▴"}</i>
      </button>

      <div className="inspector-body">
        <div className="inspector-total">
          <span className="muted">Tokens in context</span>
          <b>{current ? `~${current.context.total_est_tokens.toLocaleString()}` : "—"}</b>
        </div>

        <div className="ctx-bars" role="img" aria-label="Tokens sent per stage">
          {STAGES.map((s) => {
            const tokens = results[s]?.context.total_est_tokens;
            const height = tokens ? Math.max(4, (Math.sqrt(tokens) / Math.sqrt(max)) * 100) : 0;
            return (
              <div key={s} className={`ctx-bar ${s === stage ? "on" : ""}`}>
                <span className="ctx-val">{tokens ? tokens.toLocaleString() : "·"}</span>
                <div className={`ctx-fill tone-${results[s]?.badge.tone ?? "none"}`} style={{ height: `${height}%` }} />
                <span className="ctx-label">0{s}</span>
              </div>
            );
          })}
        </div>
        <p className="muted tiny">Bar height uses a square-root scale so small stages stay visible.</p>

        <div className="inspector-sources">
          <div className="block-title">
            Sources {current ? `· ${used.length} used of ${sources.length}` : ""}
          </div>
          {!current && <p className="muted">Run a stage to see its context.</p>}
          {current && sources.length === 0 && <p className="muted">None. Just the prompt.</p>}
          {sources.length > 0 && sources.length <= 10 && (
            <ul className="src-list">
              {sources.map((s) => (
                <li key={s.name} className="used-good">
                  <span>{s.name}</span>
                  <em>~{s.est_tokens.toLocaleString()}</em>
                </li>
              ))}
            </ul>
          )}
          {sources.length > 10 && (
            <>
              <div className="dot-grid" role="img" aria-label={`${sources.length} tables, ${used.map((u) => u.name).join(", ")} used`}>
                {sources.map((s) => (
                  <span key={s.name} className={s.used ? "dot used-bad" : "dot"} title={s.name} />
                ))}
              </div>
              <p className="tiny">
                Used: <b className="bad">{used.map((u) => u.name).join(", ")}</b>. The real table, <b>daily_sales</b>, was in
                there too.
              </p>
            </>
          )}
        </div>
      </div>
    </aside>
  );
}
