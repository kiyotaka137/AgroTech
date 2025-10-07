# service/record_service.py
from typing import List, Dict, Any, Optional
from repository.record_repo import RecordsRepository

class RecordsService:
    def __init__(self, repo: RecordsRepository):
        self.repo = repo

    async def add_records(self, items: List[Dict[str, Any]]):
        # Валидация: каждый элемент должен быть dict и содержать поле 'name'
        if not isinstance(items, list):
            raise ValueError("Payload must be a list of objects")
        cleaned = []
        for idx, itm in enumerate(items, start=1):
            if not isinstance(itm, dict):
                raise ValueError(f"Each item must be a JSON object (dict). Error at index {idx}")
            if "name" not in itm:
                raise ValueError(f"Each item must contain 'name' field. Error at index {idx}")
            cleaned.append(itm)
        await self.repo.insert_records(cleaned)

    async def get_all(self) -> List[Dict[str, Any]]:
        return await self.repo.fetch_all()

    async def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает одну запись (последнюю по created_at) для указанного name.
        Если не найдено — возвращает None.
        """
        return await self.repo.fetch_one(name)
