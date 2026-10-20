// Mirrors backend/app/models.py

export type Stage = 1 | 2 | 3 | 4;
export type Trap = "most_rows" | "newest_dates";
export type Tone = "red" | "amber" | "green";

export interface StageInfo {
  stage: Stage;
  title: string;
  subtitle: string;
}

export interface QuestionResponse {
  question: string;
  english: string;
  stages: StageInfo[];
}

export interface Badge {
  label: string;
  tone: Tone;
}

export interface EvidenceItem {
  label: string;
  value: string;
}

export interface ContextSource {
  name: string;
  kind: "prompt" | "table" | "report";
  detail: string;
  est_tokens: number;
  used: boolean;
}

export interface ContextInfo {
  sources: ContextSource[];
  total_est_tokens: number;
}

export interface RunResponse {
  stage: Stage;
  title: string;
  prompt: string;
  answer_text: string;
  answer_source: "captured" | "engine";
  capture_status: "captured" | "stale" | "missing";
  captured_with: string | null;
  badge: Badge;
  takeaway: string;
  evidence: EvidenceItem[];
  context: ContextInfo;
  steps: string[];
  wrong_table: string | null;
  headline_change_pct: number | null;
}

export interface TableInfo {
  name: string;
  rows: number;
  role: "source" | "decoy" | "other";
}

export interface TablesResponse {
  tables: TableInfo[];
}

export interface DailyPoint {
  date: string;
  units: number;
}

export interface Promo {
  promo_name: string;
  start_date: string;
  end_date: string;
  discount_pct: number;
}

export interface DatasetResponse {
  category: string;
  series: DailyPoint[];
  promos: Promo[];
  pivot_date: string;
  window_days: number;
}
