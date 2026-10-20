"""FastAPI app. Run from backend/:  uvicorn app.main:app --reload"""

from contextlib import closing

from fastapi import FastAPI

from app.db import connect, list_tables, read_sql, row_count
from app.engine import DECOY_TABLES, SOURCE_TABLES, STAGES, category_daily, run_stage
from app.models import (
    DailyPoint,
    DatasetResponse,
    Promo,
    QuestionResponse,
    RunRequest,
    RunResponse,
    TableInfo,
    TablesResponse,
)
from app.scenario import load_scenario

app = FastAPI(title="Prompt vs Context")


def table_role(name: str) -> str:
    if name in SOURCE_TABLES:
        return "source"
    if name in DECOY_TABLES:
        return "decoy"
    return "other"


@app.get("/api/question", response_model=QuestionResponse)
def get_question() -> QuestionResponse:
    q = load_scenario()["question"]
    return QuestionResponse(question=q["text"], english=q["english"], stages=STAGES)


@app.post("/api/run", response_model=RunResponse)
def post_run(req: RunRequest) -> RunResponse:
    return run_stage(req.stage, req.trap)


@app.get("/api/tables", response_model=TablesResponse)
def get_tables() -> TablesResponse:
    with closing(connect()) as conn:
        tables = [TableInfo(name=t, rows=row_count(conn, t), role=table_role(t)) for t in list_tables(conn)]
    return TablesResponse(tables=tables)


@app.get("/api/dataset", response_model=DatasetResponse)
def get_dataset() -> DatasetResponse:
    """The real data behind stage 3, for the 'See the data' chart."""
    analysis = load_scenario()["analysis"]
    cat = analysis["category"]
    with closing(connect()) as conn:
        daily = category_daily(conn, "daily_sales", cat)
        promos = read_sql(
            conn,
            "SELECT promo_name, start_date, end_date, discount_pct FROM promo_calendar WHERE category = ? ORDER BY start_date",
            (cat,),
        )
    return DatasetResponse(
        category=cat,
        series=[DailyPoint(date=d.date().isoformat(), units=int(u)) for d, u in zip(daily["date"], daily["units"])],
        promos=[Promo(**row) for row in promos.to_dict("records")],
        pivot_date=analysis["pivot_date"],
        window_days=analysis["window_days"],
    )
