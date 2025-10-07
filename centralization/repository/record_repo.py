from typing import List, Dict, Any
import uuid
from datetime import datetime, timezone

class RecordsRepository:
    def __init__(self, pool):
        self.pool = pool
        print("RecordsRepository: репозиторий создан с пулом", pool)

    async def insert_records(self, items: List[Dict[str, Any]]):
        print(f"RecordsRepository.insert_records: получено {len(items)} записей для вставки")
        
        if not items:
            print("RecordsRepository.insert_records: список пустой, ничего не вставляем")
            return

        now = datetime.now(timezone.utc)
        params = []
        for idx, item in enumerate(items, start=1):
            record_id = uuid.uuid4()
            params.append((record_id, item, now))
            print(f"RecordsRepository.insert_records: подготовлена запись {idx}: id={record_id}, data={item}")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                print("RecordsRepository.insert_records: начинаем вставку в БД")
                await conn.executemany(
                    "INSERT INTO records (id, data, created_at) VALUES ($1, $2, $3)",
                    params
                )
                print(f"RecordsRepository.insert_records: вставлено {len(params)} записей")

    async def fetch_all(self):
        print("RecordsRepository.fetch_all: получаем все записи из БД")
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, data, created_at FROM records ORDER BY created_at DESC")
            result = []
            for idx, r in enumerate(rows, start=1):
                rec = {
                    "id": str(r["id"]),
                    "data": r["data"],
                    "created_at": r["created_at"].isoformat()
                }
                result.append(rec)
                print(f"RecordsRepository.fetch_all: запись {idx}: {rec}")
            print(f"RecordsRepository.fetch_all: всего получено {len(result)} записей")
            return result
