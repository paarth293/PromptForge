import os

import aiosqlite
import pytest

from backend.app.db.migrator import run_migrations

TEST_DB_PATH = "test_promptforge.db"

@pytest.mark.asyncio
async def test_database_migrations_and_ping_table():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    try:
        # Run migrations on fresh database
        await run_migrations(TEST_DB_PATH)

        async with aiosqlite.connect(TEST_DB_PATH) as conn:
            # Check schema_migrations table
            cursor = await conn.execute("SELECT version, name FROM schema_migrations;")
            rows = await cursor.fetchall()
            assert len(rows) >= 1
            assert rows[0][0] == 1

            # Check ping table insertion and query
            await conn.execute("INSERT INTO ping (id, message) VALUES (?, ?);", ("p1", "database connection alive"))
            await conn.commit()

            cursor = await conn.execute("SELECT id, message FROM ping WHERE id = ?;", ("p1",))
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "p1"
            assert row[1] == "database connection alive"
    finally:
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
