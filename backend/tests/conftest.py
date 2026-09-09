import pytest

from backend.app.db.session import init_db


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    await init_db()
