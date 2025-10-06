from typing import List, Dict, Any
from centralization.repository.record_repo import RecordsRepository

class RecordsService:
    def __init__(self, repo: RecordsRepository):
        self.repo = repo

    async def add_records(self, items: List[Dict[str, Any]]):
        # Простая валидация: каждый элемент должен быть мапой (dict/json)
        cleaned = []
        for itm in items:
            if not isinstance(itm, dict):
                # можно добавить более точные ошибки; пока просто приводим
                raise ValueError("Each item must be a JSON object (dict).")
            cleaned.append(itm)
        await self.repo.insert_records(cleaned)

    async def get_all(self):
        return await self.repo.fetch_all()
