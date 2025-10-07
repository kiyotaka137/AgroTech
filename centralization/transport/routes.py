from fastapi import APIRouter, Depends, Request, status, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from uuid import UUID
from repository.record_repo import RecordsRepository
from service.record_service import RecordsService

router = APIRouter()

# request для POST
class RecordsInModel(BaseModel):
    root: List[Dict[str, Any]]

    def to_list(self):
        return self.root

# response для GET
class RecordOut(BaseModel):
    id: UUID
    data: Dict[str, Any]
    created_at: str

# зависимость: собираем сервис с pool из app.state
def get_service(request: Request) -> RecordsService:
    print("get_service: создаем сервис с пулом из app.state")
    pool = request.app.state.db_pool
    repo = RecordsRepository(pool)
    service = RecordsService(repo)
    print("get_service: сервис создан")
    return service

@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_records(payload: RecordsInModel, service: RecordsService = Depends(get_service)):
    print("POST /records: получен payload:", payload)
    try:
        items = payload.to_list()
        print(f"POST /records: преобразованный список записей ({len(items)} шт.):", items)
        await service.add_records(items)
        print(f"POST /records: успешно добавлено {len(items)} записей")
        return {"inserted": len(items)}
    except ValueError as e:
        print("POST /records: ошибка при добавлении записей:", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print("POST /records: непредвиденная ошибка:", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/", response_model=List[RecordOut])
async def get_records(service: RecordsService = Depends(get_service)):
    print("GET /records: запрос на получение всех записей")
    try:
        rows = await service.get_all()
        print(f"GET /records: получено {len(rows)} записей")
        return rows
    except Exception as e:
        print("GET /records: ошибка при получении записей:", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
