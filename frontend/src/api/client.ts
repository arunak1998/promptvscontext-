import type { DatasetResponse, QuestionResponse, RunResponse, Stage, TablesResponse, Trap } from "./types";

// The demo is fully static: every response was exported from the backend into public/data/
// by backend/scripts/export_static.py. No server and no AI model is called at runtime.

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function load<T>(file: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/data/${file}`);
  } catch {
    throw new ApiError(0, "Couldn't load the demo data. Check your connection and try again.");
  }
  if (!res.ok) throw new ApiError(res.status, `Demo data file ${file} is missing.`);
  return (await res.json()) as T;
}

export const api = {
  question: () => load<QuestionResponse>("question.json"),
  run: (stage: Stage, trap: Trap = "most_rows") => load<RunResponse>(stage === 4 ? `run-4-${trap}.json` : `run-${stage}.json`),
  tables: () => load<TablesResponse>("tables.json"),
  dataset: () => load<DatasetResponse>("dataset.json"),
};
