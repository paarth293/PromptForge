from typing import AsyncGenerator

import aiosqlite

from ..config import settings

# Parse local sqlite path from settings or fallback
db_url = settings.database_url
if "sqlite" in db_url:
    DB_PATH = db_url.split("///")[-1]
else:
    DB_PATH = "promptforge.db"

async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Yield an async SQLite database connection."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        yield conn

async def init_db():
    """Initialize database and run migrations."""
    from .migrator import run_migrations
    await run_migrations(DB_PATH)
