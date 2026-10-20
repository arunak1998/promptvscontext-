import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "scripts"))


@pytest.fixture(scope="session", autouse=True)
def seeded_db(tmp_path_factory):
    """Seed a fresh database for the test session so tests never depend on a local demo.db."""
    import seed

    path = tmp_path_factory.mktemp("db") / "demo.db"
    os.environ["DEMO_DB_PATH"] = str(path)
    seed.main()
    return path
