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
    """Yield an async SQLite database connection with WAL mode and performance settings."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        await conn.execute("PRAGMA journal_mode = WAL;")
        await conn.execute("PRAGMA busy_timeout = 5000;")
        await conn.execute("PRAGMA synchronous = NORMAL;")
        yield conn

async def init_db():
    """Initialize database, run migrations, enforce WAL mode, and seed demo keys."""
    import hashlib

    from .migrator import run_migrations
    await run_migrations(DB_PATH)

    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("PRAGMA journal_mode = WAL;")
        await conn.execute("PRAGMA busy_timeout = 5000;")
        await conn.execute("PRAGMA synchronous = NORMAL;")
        await conn.execute("PRAGMA foreign_keys = ON;")

        # Seed default demo API keys if not present
        demo_key_hash = hashlib.sha256(b"pf-demo-key-2026").hexdigest()
        for t_id in ["tenant-demo", "tenant-default", "tenant-e2e-demo"]:
            await conn.execute(
                """
                INSERT OR IGNORE INTO api_keys (key_id, key_hash, tenant_id, scopes)
                VALUES (?, ?, ?, ?);
                """,
                (f"key-{t_id}-default", demo_key_hash, t_id, '["*"]')
            )
        await conn.commit()
