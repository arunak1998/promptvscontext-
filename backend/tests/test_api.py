import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_question():
    body = client.get("/api/question").json()
    assert body["question"] == "Snacks sales ean drop aachu?"
    assert [s["stage"] for s in body["stages"]] == [1, 2, 3, 4]


@pytest.mark.parametrize("stage", [1, 2, 3, 4])
def test_run_each_stage(stage):
    res = client.post("/api/run", json={"stage": stage})
    assert res.status_code == 200
    assert res.json()["answer_text"]


@pytest.mark.parametrize("stage", [0, 5, "3"])
def test_run_rejects_invalid_stage(stage):
    assert client.post("/api/run", json={"stage": stage}).status_code == 422


def test_tables():
    tables = client.get("/api/tables").json()["tables"]
    assert len(tables) == 50
    assert {t["name"] for t in tables if t["role"] == "decoy"} == {"sales_test", "sales_backup_2023"}


def test_dataset():
    body = client.get("/api/dataset").json()
    assert body["category"] == "Snacks"
    assert len(body["series"]) == 288
