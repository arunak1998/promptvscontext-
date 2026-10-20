import { motion, useReducedMotion } from "framer-motion";
import type { TableInfo } from "../api/types";

interface Props {
  tables: TableInfo[];
  wrongTable: string;
  tokens: number;
}

/** 50 table names pour into the AI one by one; the table it wrongly picked lights up red. */
export function TableDump({ tables, wrongTable, tokens }: Props) {
  const reduced = useReducedMotion();
  const stagger = reduced ? 0 : 0.035;
  const pickDelay = reduced ? 0 : tables.length * stagger + 0.3;

  return (
    <div className="dump">
      <div className="dump-grid">
        {tables.map((t, i) => {
          const wrong = t.name === wrongTable;
          return (
            <motion.span
              key={t.name}
              className={`dump-chip ${wrong ? "wrong" : ""}`}
              initial={{ opacity: 0, y: -14, scale: 0.9 }}
              animate={{ opacity: wrong ? 1 : [0, 1, 0.45], y: 0, scale: wrong ? [0.9, 1, 1.08, 1] : 1 }}
              transition={{
                delay: i * stagger,
                duration: wrong ? 0.6 : 1.2,
                ...(wrong ? { scale: { delay: pickDelay, duration: 0.5 } } : {}),
              }}
            >
              {t.name}
            </motion.span>
          );
        })}
      </div>
      <motion.div
        className="dump-ai"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: pickDelay }}
      >
        <span className="ai-dot" aria-hidden="true" />
        <span>
          AI picked <b className="bad">{wrongTable}</b> out of {tables.length} tables
        </span>
        <em>~{tokens.toLocaleString()} tokens</em>
      </motion.div>
    </div>
  );
}
