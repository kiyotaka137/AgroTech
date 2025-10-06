# app/repository/records_repo.py
from typing import List, Dict, Any
import uuid
from datetime import datetime, timezone

class RecordsRepository:
    def __init__(self, pool):
        self.pool = pool

    async def insert_records(self, items: List[Dict[str, Any]]):

        if not items:
            return

        now = datetime.now(timezone.utc)
        params = []
        for item in items:
            params.append((uuid.uuid4(), item, now))

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(
                    "INSERT INTO records (id, data, created_at) VALUES ($1, $2, $3)",
                    params
                )

    async def fetch_all(self):
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, data, created_at FROM records ORDER BY created_at DESC")
            result = []
            for r in rows:
                result.append({
                    "id": str(r["id"]),
                    "data": r["data"],
                    "created_at": r["created_at"].isoformat()
                })
            return result
