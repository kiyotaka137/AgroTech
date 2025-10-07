from typing import List, Dict, Any
from repository.record_repo import RecordsRepository

class RecordsService:
    def __init__(self, repo: RecordsRepository):
        self.repo = repo
        print("RecordsService: сервис создан с репозиторием", repo)

    async def add_records(self, items: List[Dict[str, Any]]):
        print(f"RecordsService.add_records: получено {len(items)} записей для добавления")
        # Простая валидация: каждый элемент должен быть мапой (dict/json)
        cleaned = []
        for idx, itm in enumerate(items, start=1):
            if not isinstance(itm, dict):
                print(f"RecordsService.add_records: ошибка в элементе {idx} - не dict:", itm)
                raise ValueError("Each item must be a JSON object (dict).")
            cleaned.append(itm)
        print(f"RecordsService.add_records: после валидации {len(cleaned)} записей готовы к вставке")
        await self.repo.insert_records(cleaned)
        print("RecordsService.add_records: вставка записей завершена")

    async def get_all(self):
        print("RecordsService.get_all: запрос всех записей")
        rows = await self.repo.fetch_all()
        print(f"RecordsService.get_all: получено {len(rows)} записей")
        return rows
