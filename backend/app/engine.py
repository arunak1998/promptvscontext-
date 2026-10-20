"""Analysis engine: one function per stage.

Every stage builds the exact prompt + context an AI would receive (`build_context`), then runs its own
analysis. The answer text shown in the app is the captured AI answer for that exact context
(see app/captures.py); the engine's computed answer is the fallback when no valid capture exists.
"""

from contextlib import closing
from dataclasses import dataclass, field
from datetime import date, timedelta
import sqlite3

import pandas as pd

from app.captures import find_capture
from app.db import column_names, connect, list_tables, read_sql, row_count, table_as_text
from app.metrics import WindowChange, window_change
from app.models import Badge, ContextInfo, ContextSource, EvidenceItem, RunResponse, StageInfo
from app.scenario import as_date, fmt_date, load_scenario

STAGES = [
    StageInfo(stage=1, title="Weak prompt", subtitle="Just the question. No data."),
    StageInfo(stage=2, title="Better prompt", subtitle="Role, task, format, rules. Still no data."),
    StageInfo(stage=3, title="Right context", subtitle="Same prompt + exactly 3 sources."),
    StageInfo(stage=4, title="Too much context", subtitle="Same prompt + all 50 tables."),
]

SOURCE_TABLES = ("daily_sales", "promo_calendar", "quarterly_report")
DECOY_TABLES = ("sales_test", "sales_backup_2023")
SALES_COLUMNS = {"date", "category", "units"}


# ---------- context ----------


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class Source:
    name: str
    kind: str
    detail: str
    text: str
    used: bool = True


@dataclass
class StageContext:
    prompt: str
    sources: list[Source] = field(default_factory=list)
    note: str = ""

    def full_text(self) -> str:
        """Exactly what the AI receives for this stage."""
        parts = ["=== PROMPT ===", self.prompt]
        if self.sources:
            parts += ["=== CONTEXT ==="] + [s.text for s in self.sources]
        if self.note:
            parts += ["=== PIPELINE NOTE ===", self.note]
        return "\n".join(parts)

    def info(self) -> ContextInfo:
        prompt = ContextSource(
            name="prompt", kind="prompt", detail="Your words", est_tokens=est_tokens(self.prompt + self.note), used=True
        )
        sources = [prompt] + [
            ContextSource(name=s.name, kind=s.kind, detail=s.detail, est_tokens=est_tokens(s.text), used=s.used)
            for s in self.sources
        ]
        return ContextInfo(sources=sources, total_est_tokens=sum(s.est_tokens for s in sources))


def weak_prompt(sc: dict) -> str:
    return sc["question"]["text"]


def structured_prompt(sc: dict) -> str:
    return "\n".join(sc["structured_prompt"]).format(question=sc["question"]["text"])


def right_sources(conn: sqlite3.Connection, sc: dict) -> list[Source]:
    cat = sc["analysis"]["category"]
    return [
        Source("daily_sales", "table", f"{cat} rows only", table_as_text(conn, "daily_sales", "WHERE category = ?", (cat,))),
        Source("promo_calendar", "table", "All promos", table_as_text(conn, "promo_calendar")),
        Source("quarterly_report", "report", "Past quarter notes", table_as_text(conn, "quarterly_report")),
    ]


def all_table_sources(conn: sqlite3.Connection, used_table: str) -> list[Source]:
    return [
        Source(t, "table", f"{row_count(conn, t):,} rows", table_as_text(conn, t), used=(t == used_table))
        for t in list_tables(conn)
    ]


def build_context(conn: sqlite3.Connection, sc: dict, stage: int, trap: str) -> StageContext:
    if stage == 1:
        return StageContext(weak_prompt(sc))
    if stage == 2:
        return StageContext(structured_prompt(sc))
    if stage == 3:
        return StageContext(structured_prompt(sc), right_sources(conn, sc))
    pick = pick_table_naively(conn, trap)
    note = f"Auto-selected analysis table: {pick.table} ({pick.reason})"
    return StageContext(structured_prompt(sc), all_table_sources(conn, pick.table), note)


# ---------- shared analysis ----------


@dataclass
class Analysis:
    answer_text: str
    badge: Badge
    takeaway: str
    evidence: list[EvidenceItem]
    steps: list[str]
    wrong_table: str | None = None
    headline_change_pct: float | None = None


@dataclass(frozen=True)
class PromoDropFacts:
    promo_name: str
    promo_start: date
    promo_end: date
    discount_pct: float
    change: WindowChange
    prev_promo_name: str
    prev_promo_end: date
    prev_change: WindowChange
    report_quarter: str
    report_text: str


def quarter_label(d: date) -> str:
    return f"Q{(d.month - 1) // 3 + 1} {d.year}"


def category_daily(conn: sqlite3.Connection, table: str, category: str) -> pd.DataFrame:
    df = read_sql(conn, f'SELECT date, units FROM "{table}" WHERE category = ? ORDER BY date', (category,))
    df["date"] = pd.to_datetime(df["date"])
    return df


def find_promo_drop(conn: sqlite3.Connection, sc: dict) -> PromoDropFacts:
    """Real analysis on the 3 right sources: latest ended promo -> drop after it -> previous promo -> report."""
    cat, window = sc["analysis"]["category"], sc["analysis"]["window_days"]
    daily = category_daily(conn, "daily_sales", cat)
    last_day = daily["date"].max().date().isoformat()
    promos = read_sql(
        conn,
        "SELECT promo_name, start_date, end_date, discount_pct FROM promo_calendar "
        "WHERE category = ? AND end_date < ? ORDER BY end_date DESC",
        (cat, last_day),
    )
    latest, prev = promos.iloc[0], promos.iloc[1]
    report = read_sql(
        conn,
        "SELECT quarter, summary_text FROM quarterly_report WHERE category = ? AND quarter = ? AND summary_text LIKE ?",
        (cat, quarter_label(as_date(prev["end_date"]) + timedelta(days=1)), f"%{prev['promo_name']}%"),
    ).iloc[0]
    return PromoDropFacts(
        promo_name=latest["promo_name"],
        promo_start=as_date(latest["start_date"]),
        promo_end=as_date(latest["end_date"]),
        discount_pct=float(latest["discount_pct"]),
        change=window_change(daily, as_date(latest["end_date"]), window),
        prev_promo_name=prev["promo_name"],
        prev_promo_end=as_date(prev["end_date"]),
        prev_change=window_change(daily, as_date(prev["end_date"]), window),
        report_quarter=report["quarter"],
        report_text=report["summary_text"],
    )


@dataclass(frozen=True)
class NaivePick:
    table: str
    reason: str
    candidates: list[str]
    first_date: date
    last_date: date


def date_bounds(conn: sqlite3.Connection, table: str) -> tuple[date, date]:
    lo, hi = conn.execute(f'SELECT MIN(date), MAX(date) FROM "{table}"').fetchone()
    return as_date(lo), as_date(hi)


def pick_table_naively(conn: sqlite3.Connection, trap: str) -> NaivePick:
    """The trap: match table names on 'sales', then trust a shallow signal instead of checking the data."""
    candidates = [t for t in list_tables(conn) if "sales" in t and SALES_COLUMNS <= set(column_names(conn, t))]
    if trap == "most_rows":
        table = max(candidates, key=lambda t: row_count(conn, t))
        reason = f"biggest 'sales' table, {row_count(conn, table):,} rows, so it must be the main one"
    else:
        table = max(candidates, key=lambda t: date_bounds(conn, t)[1])
        reason = f"newest dates, up to {fmt_date(date_bounds(conn, table)[1])}, so it must be the live one"
    first, last = date_bounds(conn, table)
    return NaivePick(table, reason, candidates, first, last)


def naive_pivot(sc: dict, last_date: date) -> date:
    """Same day-of-year as the real pivot, in the latest year the table covers. Never checks the year."""
    real = as_date(sc["analysis"]["pivot_date"])
    pivot = date(last_date.year, real.month, real.day)
    return pivot if pivot < last_date else date(last_date.year - 1, real.month, real.day)


def short(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def pct(value: float) -> str:
    return f"{value:.1f}%"


def signed_pct(value: float) -> str:
    return f"{'+' if value >= 0 else '−'}{abs(value):.1f}%"


# ---------- stages ----------


def stage1_weak_prompt(sc: dict, ctx: StageContext) -> Analysis:
    return Analysis(
        answer_text="Market conditions-nala irukkalam. Demand kammi aagirukkum, competition adhigam aagirukkum. "
        "Konjam offers kudunga, sales thirumba yerum.",
        badge=Badge(label="Guess", tone="red"),
        takeaway="No context, so the AI fills the gap with a confident guess.",
        evidence=[],
        steps=[
            f"Sent only the question (~{ctx.info().total_est_tokens} tokens).",
            "No role, no rules, no data.",
            "The model filled the gap with a generic, confident-sounding guess.",
        ],
    )


def stage2_better_prompt(sc: dict, ctx: StageContext) -> Analysis:
    return Analysis(
        answer_text="I don't know. I have no sales data, so I can't say why Snacks sales dropped, and I won't guess.\n"
        "1. Daily Snacks sales (units by date) to measure the drop: __%.\n"
        "2. The promo calendar to check if a Snacks promo ended on __ (date).\n"
        "3. Last quarter's report to compare with the previous drop of __%.",
        badge=Badge(label="Honest, but stuck", tone="amber"),
        takeaway="Perfect prompt, no data: that's the limit of prompt engineering.",
        evidence=[],
        steps=[
            f"Sent role + task + format + rules + question (~{ctx.info().total_est_tokens} tokens).",
            "Context: none. Zero rows of sales data.",
            "The model followed the rules and admitted it can't know.",
        ],
    )


def stage3_right_context(conn: sqlite3.Connection, sc: dict, ctx: StageContext) -> Analysis:
    cat = sc["analysis"]["category"]
    f = find_promo_drop(conn, sc)
    c = f.change
    before = f"{short(f.promo_end - timedelta(days=c.before_days - 1))} to {short(f.promo_end)}"
    after = f"{short(f.promo_end + timedelta(days=1))} to {short(f.promo_end + timedelta(days=c.after_days))}"
    answer = (
        f"The {f.promo_name} promo ended on {fmt_date(f.promo_end)}, so {cat} sales dropped ~{round(c.drop_pct)}%. "
        "Same pattern as last quarter.\n"
        f"1. Average {cat} units per day fell from {c.before_avg:.0f} ({before}) to {c.after_avg:.0f} ({after}): "
        f"a drop of {pct(c.drop_pct)}.\n"
        f"2. The promo gave {f.discount_pct:.0f}% off from {fmt_date(f.promo_start)} to {fmt_date(f.promo_end)}. "
        "Sales fell the very next day.\n"
        f"3. After the {f.prev_promo_name} ended on {fmt_date(f.prev_promo_end)}, {cat} fell {pct(f.prev_change.drop_pct)}. "
        f"The {f.report_quarter} report says the same."
    )
    return Analysis(
        answer_text=answer,
        badge=Badge(label="Fact", tone="green"),
        takeaway="Right context: 3 sources, real numbers, a real answer.",
        evidence=[
            EvidenceItem(label=f"Avg {cat} units/day, {before}", value=f"{c.before_avg:.0f}"),
            EvidenceItem(label=f"Avg {cat} units/day, {after}", value=f"{c.after_avg:.0f}"),
            EvidenceItem(label="Change", value=signed_pct(c.change_pct)),
            EvidenceItem(label="Promo that ended", value=f"{f.promo_name}, {f.discount_pct:.0f}% off, ended {fmt_date(f.promo_end)}"),
            EvidenceItem(label=f"Drop after {f.prev_promo_name}", value=signed_pct(f.prev_change.change_pct)),
            EvidenceItem(label=f"{f.report_quarter} report", value=f.report_text.split(",")[0] + "."),
        ],
        steps=[
            f"Context: exactly 3 sources (~{ctx.info().total_est_tokens:,} tokens).",
            f"SELECT date, units FROM daily_sales WHERE category = '{cat}'",
            f"SELECT promo_name, end_date FROM promo_calendar WHERE category = '{cat}' → {f.promo_name} ended {fmt_date(f.promo_end)}",
            f"Avg units/day, {c.before_days} days before vs {c.after_days} days after {fmt_date(f.promo_end)} → {signed_pct(c.change_pct)}",
            f"Same check after {f.prev_promo_name} ({fmt_date(f.prev_promo_end)}) → {signed_pct(f.prev_change.change_pct)}",
            f"Matched quarterly_report {f.report_quarter}: \"{f.report_text.split(',')[0]}\"",
        ],
        headline_change_pct=round(c.change_pct, 2),
    )


def stage4_too_much_context(conn: sqlite3.Connection, sc: dict, ctx: StageContext, trap: str) -> Analysis:
    cat, window = sc["analysis"]["category"], sc["analysis"]["window_days"]
    pick = pick_table_naively(conn, trap)
    pivot = naive_pivot(sc, pick.last_date)
    c = window_change(category_daily(conn, pick.table, cat), pivot, window)
    real = find_promo_drop(conn, sc).change
    if c.change_pct < 0:
        answer = (
            f"{cat} sales crashed {pct(c.drop_pct)} after {short(pivot)}. This is a serious demand collapse, act now.\n"
            f"1. Average {cat} units per day fell from {c.before_avg:.0f} to {c.after_avg:.0f}: a drop of {pct(c.drop_pct)}.\n"
            f"2. The fall started on {short(pivot + timedelta(days=1))} and has lasted {c.after_days} days.\n"
            f"3. Recommend a price cut of at least {round(c.drop_pct / 2)}% to win customers back."
        )
    else:
        answer = (
            f"{cat} sales did not drop. They went up {pct(c.change_pct)} after {short(pivot)}. The drop is a reporting error.\n"
            f"1. Average {cat} units per day rose from {c.before_avg:.0f} to {c.after_avg:.0f}: {signed_pct(c.change_pct)}.\n"
            f"2. The increase has held for {c.after_days} days.\n"
            f"3. Check the dashboard. {cat} demand is healthy at about {c.after_avg:.0f} units a day."
        )
    return Analysis(
        answer_text=answer,
        badge=Badge(label="Wrong table, wrong number", tone="red"),
        takeaway="More context is not better context.",
        evidence=[
            EvidenceItem(label="Table it used", value=pick.table),
            EvidenceItem(label="Dates in that table", value=f"{fmt_date(pick.first_date)} to {fmt_date(pick.last_date)}"),
            EvidenceItem(label="Number it reported", value=signed_pct(c.change_pct)),
            EvidenceItem(label="Real number (daily_sales)", value=signed_pct(real.change_pct)),
        ],
        steps=[
            f"Dumped all {len(ctx.sources)} tables into context (~{ctx.info().total_est_tokens:,} tokens).",
            f"Searched names for 'sales': {len(pick.candidates)} look like sales tables ({', '.join(pick.candidates)}).",
            f"Picked {pick.table}: {pick.reason}.",
            f"SELECT date, units FROM {pick.table} WHERE category = '{cat}'",
            f"Compared {window} days before vs after {fmt_date(pivot)} → {signed_pct(c.change_pct)}. Never checked the dates.",
            "Answered confidently, with the wrong number.",
        ],
        wrong_table=pick.table,
        headline_change_pct=round(c.change_pct, 2),
    )


# ---------- entry points ----------


def capture_key(stage: int, trap: str) -> str:
    return f"4:{trap}" if stage == 4 else str(stage)


def resolve_trap(sc: dict, trap: str | None) -> str:
    return trap or sc["stage4"]["default_trap"]


def stage_context(stage: int, trap: str | None = None) -> StageContext:
    sc = load_scenario()
    with closing(connect()) as conn:
        return build_context(conn, sc, stage, resolve_trap(sc, trap))


def analyse(conn: sqlite3.Connection, sc: dict, stage: int, ctx: StageContext, trap: str) -> Analysis:
    if stage == 1:
        return stage1_weak_prompt(sc, ctx)
    if stage == 2:
        return stage2_better_prompt(sc, ctx)
    if stage == 3:
        return stage3_right_context(conn, sc, ctx)
    return stage4_too_much_context(conn, sc, ctx, trap)


def run_stage(stage: int, trap: str | None = None) -> RunResponse:
    sc = load_scenario()
    trap = resolve_trap(sc, trap)
    with closing(connect()) as conn:
        ctx = build_context(conn, sc, stage, trap)
        result = analyse(conn, sc, stage, ctx, trap)
    capture = find_capture(capture_key(stage, trap), ctx.full_text())
    return RunResponse(
        stage=stage,
        title=STAGES[stage - 1].title,
        prompt=ctx.prompt,
        answer_text=capture.text or result.answer_text,
        answer_source="captured" if capture.text else "engine",
        capture_status=capture.status,
        captured_with=capture.model,
        badge=result.badge,
        takeaway=result.takeaway,
        evidence=result.evidence,
        context=ctx.info(),
        steps=result.steps,
        wrong_table=result.wrong_table,
        headline_change_pct=result.headline_change_pct,
    )
