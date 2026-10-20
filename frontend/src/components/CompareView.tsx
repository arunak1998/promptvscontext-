import { useEffect } from "react";
import { motion } from "framer-motion";
import type { RunResponse, Stage, StageInfo } from "../api/types";

interface Props {
  stages: StageInfo[];
  results: Partial<Record<Stage, RunResponse>>;
  errors: Partial<Record<Stage, string>>;
  onNeedResults: () => void;
}

/** Closing shot: same question, four answers side by side. */
export function CompareView({ stages, results, errors, onNeedResults }: Props) {
  useEffect(onNeedResults, [onNeedResults]);

  return (
    <div className="compare-grid">
      {stages.map((info, i) => {
        const r = results[info.stage];
        const [headline, ...rest] = (r?.answer_text ?? "").split("\n");
        return (
          <motion.article
            key={info.stage}
            className={`compare-card tone-${r?.badge.tone ?? "none"}`}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.12 }}
          >
            <header>
              <span className="stage-num">0{info.stage}</span>
              <div>
                <b>{info.title}</b>
                <span className="muted">{info.subtitle}</span>
              </div>
            </header>
            {errors[info.stage] && <p className="bad">{errors[info.stage]}</p>}
            {!r && !errors[info.stage] && <div className="thinking" aria-label="Loading" />}
            {r && (
              <>
                <span className={`verdict-badge small tone-${r.badge.tone}`}>{r.badge.label}</span>
                <p className="compare-headline">{headline}</p>
                {rest.length > 0 && (
                  <ul className="compare-points">
                    {rest.map((line) => (
                      <li key={line}>{line.replace(/^\d\.\s*/, "")}</li>
                    ))}
                  </ul>
                )}
                <footer>
                  <span>~{r.context.total_est_tokens.toLocaleString()} tokens</span>
                  {r.wrong_table && <span className="bad">used {r.wrong_table}</span>}
                </footer>
              </>
            )}
          </motion.article>
        );
      })}
    </div>
  );
}
