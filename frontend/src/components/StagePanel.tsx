import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { RunResponse, StageInfo, TableInfo } from "../api/types";
import { TypingText } from "./TypingText";
import { TableDump } from "./TableDump";

interface Props {
  info: StageInfo;
  result: RunResponse | undefined;
  loading: boolean;
  error: string | undefined;
  tables: TableInfo[];
  onRetry: () => void;
}

export function StagePanel({ info, result, loading, error, tables, onRetry }: Props) {
  // Remember which answers already finished typing, so revisiting a stage doesn't retype it.
  const [typed, setTyped] = useState<Record<string, boolean>>({});
  const key = result ? `${result.stage}:${result.answer_text}` : "";
  const done = result ? typed[key] : false;

  if (error) {
    return (
      <div className="stage-card error-card" role="alert">
        <b>Couldn't run stage {info.stage}</b>
        <p>{error}</p>
        <button className="btn" onClick={onRetry}>
          Try again
        </button>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="stage-card empty-card">
        <span className="stage-num">0{info.stage}</span>
        <h3>{info.title}</h3>
        <p className="soft">{info.subtitle}</p>
        <p className="muted">
          {loading ? "Sending to the AI…" : "Press Run (or Space) to send it to the AI."}
        </p>
        {loading && <div className="thinking" aria-label="Loading" />}
      </div>
    );
  }

  return (
    <motion.div className="stage-card" key={result.stage} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
      <div className="block">
        <div className="block-title">What we gave the AI</div>
        <pre className="prompt-box">{result.prompt}</pre>
        <ContextChips result={result} />
      </div>

      <div className="block">
        <div className="block-title">
          AI answer
          <span className="source-tag">
            {result.answer_source === "captured" ? `captured from ${result.captured_with}` : `engine answer (${result.capture_status} capture)`}
          </span>
        </div>
        <div className={`answer tone-${result.badge.tone}`}>
          {loading ? (
            <div className="thinking" aria-label="Thinking" />
          ) : (
            <TypingText
              key={key}
              text={result.answer_text}
              animate={!done}
              onDone={() => setTyped((t) => ({ ...t, [key]: true }))}
            />
          )}
        </div>
      </div>

      <AnimatePresence>
        {done && !loading && (
          <motion.div className="reveal" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <motion.div
              className={`verdict-badge tone-${result.badge.tone}`}
              initial={{ scale: 0.7, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 380, damping: 18 }}
            >
              {result.badge.label}
            </motion.div>
            <p className="takeaway">{result.takeaway}</p>

            {result.evidence.length > 0 && (
              <div className="block">
                <div className="block-title">{result.stage === 4 ? "What went wrong" : "Evidence from the data"}</div>
                <ul className="evidence">
                  {result.evidence.map((e, i) => (
                    <motion.li
                      key={e.label}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.08 }}
                      className={e.value === result.wrong_table ? "bad" : ""}
                    >
                      <span>{e.label}</span>
                      <b>{e.value}</b>
                    </motion.li>
                  ))}
                </ul>
              </div>
            )}

            <details className="steps">
              <summary>What the engine did ({result.steps.length} steps)</summary>
              <ol>
                {result.steps.map((s) => (
                  <li key={s}>{s.startsWith("SELECT") ? <code>{s}</code> : s}</li>
                ))}
              </ol>
            </details>
          </motion.div>
        )}
      </AnimatePresence>

      {result.stage === 4 && result.wrong_table && (
        <div className="block">
          <div className="block-title">All 50 tables, dumped into the AI</div>
          <TableDump tables={tables} wrongTable={result.wrong_table} tokens={result.context.total_est_tokens} />
        </div>
      )}
    </motion.div>
  );
}

function ContextChips({ result }: { result: RunResponse }) {
  const sources = result.context.sources.filter((s) => s.kind !== "prompt");
  if (sources.length === 0) {
    return <p className="no-context">No data attached. ~{result.context.total_est_tokens} tokens total.</p>;
  }
  if (sources.length > 10) {
    return (
      <div className="chips">
        <span className="ctx-chip heavy">
          {sources.length} tables <em>~{result.context.total_est_tokens.toLocaleString()} tokens</em>
        </span>
      </div>
    );
  }
  return (
    <div className="chips">
      {sources.map((s) => (
        <span key={s.name} className="ctx-chip">
          {s.name}
          <em>~{s.est_tokens.toLocaleString()} tok</em>
        </span>
      ))}
    </div>
  );
}
