import sqlite3
from contextlib import contextmanager
from .config import DATABASE_PATH


def init_db() -> None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                discord_id TEXT PRIMARY KEY,
                discord_username TEXT NOT NULL,
                riot_name TEXT NOT NULL,
                riot_tag TEXT NOT NULL,
                region TEXT NOT NULL,
                rank_name TEXT NOT NULL,
                tier_name TEXT NOT NULL,
                rr INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_link(
    discord_id: str,
    discord_username: str,
    riot_name: str,
    riot_tag: str,
    region: str,
    rank_name: str,
    tier_name: str,
    rr: int,
    last_updated: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO links (
                discord_id, discord_username, riot_name, riot_tag,
                region, rank_name, tier_name, rr, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET
                discord_username=excluded.discord_username,
                riot_name=excluded.riot_name,
                riot_tag=excluded.riot_tag,
                region=excluded.region,
                rank_name=excluded.rank_name,
                tier_name=excluded.tier_name,
                rr=excluded.rr,
                last_updated=excluded.last_updated
            """,
            (
                discord_id,
                discord_username,
                riot_name,
                riot_tag,
                region,
                rank_name,
                tier_name,
                rr,
                last_updated,
            ),
        )


def get_link(discord_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM links WHERE discord_id = ?", (discord_id,)).fetchone()
        return dict(row) if row else None


def delete_link(discord_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM links WHERE discord_id = ?", (discord_id,))
