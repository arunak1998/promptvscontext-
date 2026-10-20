import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { QuestionResponse, RunResponse, Stage, TableInfo, Trap } from "../api/types";

type Status = "idle" | "loading" | "done" | "error";

const STAGES: Stage[] = [1, 2, 3, 4];
const THINKING_MS = 700;

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong. Try again.";
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** All demo state: current stage, results per stage, loading and error states. */
export function useDemo() {
  const [question, setQuestion] = useState<QuestionResponse | null>(null);
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [bootError, setBootError] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>(1);
  const [trap, setTrap] = useState<Trap>("most_rows");
  const [results, setResults] = useState<Partial<Record<Stage, RunResponse>>>({});
  const [status, setStatus] = useState<Partial<Record<Stage, Status>>>({});
  const [errors, setErrors] = useState<Partial<Record<Stage, string>>>({});

  const boot = useCallback(() => {
    setBootError(null);
    Promise.all([api.question(), api.tables()])
      .then(([q, t]) => {
        setQuestion(q);
        setTables(t.tables);
      })
      .catch((err) => setBootError(errorMessage(err)));
  }, []);

  useEffect(boot, [boot]);

  const fetchStage = useCallback(
    async (s: Stage, withPause: boolean) => {
      setStatus((prev) => ({ ...prev, [s]: "loading" }));
      setErrors((prev) => ({ ...prev, [s]: undefined }));
      try {
        const [res] = await Promise.all([api.run(s, s === 4 ? trap : undefined), withPause ? wait(THINKING_MS) : null]);
        setResults((prev) => ({ ...prev, [s]: res }));
        setStatus((prev) => ({ ...prev, [s]: "done" }));
      } catch (err) {
        setErrors((prev) => ({ ...prev, [s]: errorMessage(err) }));
        setStatus((prev) => ({ ...prev, [s]: "error" }));
      }
    },
    [trap],
  );

  const run = useCallback(() => {
    if (status[stage] !== "loading") void fetchStage(stage, true);
  }, [fetchStage, stage, status]);

  const runMissing = useCallback(() => {
    STAGES.filter((s) => !results[s] && status[s] !== "loading").forEach((s) => void fetchStage(s, false));
  }, [fetchStage, results, status]);

  const next = useCallback(() => setStage((s) => (s < 4 ? ((s + 1) as Stage) : s)), []);
  const prev = useCallback(() => setStage((s) => (s > 1 ? ((s - 1) as Stage) : s)), []);

  const changeTrap = useCallback((t: Trap) => {
    setTrap(t);
    setResults((prev) => ({ ...prev, 4: undefined }));
    setStatus((prev) => ({ ...prev, 4: "idle" }));
  }, []);

  const reset = useCallback(() => {
    setResults({});
    setStatus({});
    setErrors({});
    setStage(1);
  }, []);

  return {
    question,
    tables,
    bootError,
    boot,
    stage,
    setStage,
    trap,
    changeTrap,
    results,
    status,
    errors,
    run,
    runMissing,
    next,
    prev,
    reset,
  };
}

export type Demo = ReturnType<typeof useDemo>;
