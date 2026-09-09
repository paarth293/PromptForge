import glob
import logging
import os

import aiosqlite

logger = logging.getLogger("promptforge.db.migrator")

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

async def run_migrations(db_path: str):
    """Discovers and runs pending SQL migrations in order."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)) if os.path.dirname(db_path) else ".", exist_ok=True)

    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await conn.commit()

        # Fetch applied migrations
        cursor = await conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC;")
        rows = await cursor.fetchall()
        applied_versions = {row[0] for row in rows}

        migration_files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))
        for filepath in migration_files:
            filename = os.path.basename(filepath)
            try:
                version_str = filename.split("_")[0]
                version = int(version_str)
            except ValueError:
                logger.warning(f"Skipping migration with invalid version format: {filename}")
                continue

            if version not in applied_versions:
                logger.info(f"Applying migration {filename}...")
                with open(filepath, "r", encoding="utf-8") as f:
                    sql_content = f.read()

                await conn.executescript(sql_content)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?);",
                    (version, filename)
                )
                await conn.commit()
                logger.info(f"Migration {filename} applied successfully.")
