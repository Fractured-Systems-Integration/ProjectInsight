import sqlite3
from datetime import datetime, timedelta

class LocalStore:
    def __init__(self, path: str = "insight.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics(
              id INTEGER PRIMARY KEY,
              ts TEXT NOT NULL,
              payload TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def append_json(self, ts_iso: str, payload_json: str):
        self.conn.execute(
            "INSERT INTO metrics(ts, payload) VALUES (?, ?)",
            (ts_iso, payload_json)
        )
        self.conn.commit()

    def prune_days(self, days: int = 14):
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        self.conn.execute("DELETE FROM metrics WHERE ts < ?", (cutoff,))
        self.conn.commit()

    def batch(self, limit: int = 200):
        cur = self.conn.execute(
            "SELECT id, payload FROM metrics ORDER BY id ASC LIMIT ?",
            (limit,)
        )
        return cur.fetchall()

    def delete_ids(self, ids):
        if not ids:
            return
        q = "DELETE FROM metrics WHERE id IN ({})".format(",".join("?" * len(ids)))
        self.conn.execute(q, ids)
        self.conn.commit()
