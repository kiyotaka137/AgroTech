# repository/record_repo.py
from typing import List, Dict, Any, Optional
import uuid
import json
from datetime import datetime, timezone

class RecordsRepository:
    def __init__(self, pool):
        self.pool = pool

    async def insert_records(self, items: List[Dict[str, Any]]) -> int:
        """
        items: список объектов, каждый объект должен содержать ключ 'name' и любые другие поля.
        Сохраняем name отдельно, а data — сериализованный весь объект (включая name).
        Возвращает количество фактически добавленных записей (исключая дубликаты).
        """
        if not items:
            return 0

        now = datetime.now(timezone.utc)
        params = []
        for idx, item in enumerate(items, start=1):
            record_id = uuid.uuid4()
            if "name" not in item:
                raise ValueError(f"Item at index {idx} has no 'name' field")
            name = item["name"]
            # Сохраняем весь объект как data (можно исключить name, если нужно)
            json_data = json.dumps(item, default=str)
            params.append((record_id, name, json_data, now))

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.executemany(
                    """
                    INSERT INTO records (id, name, data, created_at) 
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    params
                )
                # executemany возвращает строку вида "INSERT 0 2", где последнее число - количество вставленных строк
                if result and "INSERT" in result:
                    # Извлекаем количество вставленных строк из результата
                    parts = result.split()
                    if len(parts) >= 3:
                        return int(parts[2])
                return len(items)  # fallback

    async def fetch_all(self) -> List[Dict[str, Any]]:
        result = []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, name, data, created_at FROM records ORDER BY created_at DESC")
            for r in rows:
                data_dict = json.loads(r["data"])
                rec = {
                    "id": str(r["id"]),
                    "name": r["name"],
                    "data": data_dict,
                    "created_at": r["created_at"].isoformat()
                }
                result.append(rec)
        return result

    async def fetch_one(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает последнюю запись (по created_at DESC) с указанным name или None.
        """
        async with self.pool.acquire() as conn:
            r = await conn.fetchrow(
                "SELECT id, name, data, created_at FROM records WHERE name=$1 ORDER BY created_at DESC LIMIT 1",
                name
            )
            if not r:
                return None
            data_dict = json.loads(r["data"])
            return {
                "id": str(r["id"]),
                "name": r["name"],
                "data": data_dict,
                "created_at": r["created_at"].isoformat()
            }
    
    async def fetch_all_names(self) -> List[str]:
        """Возвращает список всех уникальных имен"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT name FROM records ORDER BY name")
            return [row["name"] for row in rows]