# records_router.py
from fastapi import APIRouter, Depends, Request, status, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from repository.record_repo import RecordsRepository
from service.record_service import RecordsService

router = APIRouter(tags=["records"])

# request для POST
class RecordsInModel(BaseModel):
    """Модель для добавления записей"""
    root: List[Dict[str, Any]] = Field(
        ...,
        example=[
            {"name": "John", "age": 30, "email": "john@example.com"},
            {"name": "Alice", "age": 25, "email": "alice@example.com"}
        ],
        description="Список записей для добавления"
    )

    def to_list(self):
        return self.root

# response для GET
class RecordOut(BaseModel):
    """Модель возвращаемой записи"""
    id: UUID = Field(..., description="UUID записи")
    name: str = Field(..., example="user_complex", description="уникальное имя записи")
    data: Dict[str, Any] = Field(
        ...,
        example={"name": "John", "age": 30, "email": "john@example.com"},
        description="Данные записи в формате JSON"
    )
    created_at: str = Field(..., description="Время создания записи в ISO формате")

# response для POST
class RecordsInsertedResponse(BaseModel):
    """Модель ответа после добавления записей"""
    inserted: int = Field(..., example=2, description="Количество добавленных записей")

# зависимость: собираем сервис с pool из app.state
def get_service(request: Request) -> RecordsService:
    """Зависимость для получения сервиса работы с записями"""
    pool = request.app.state.db_pool
    repo = RecordsRepository(pool)
    service = RecordsService(repo)
    return service

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=RecordsInsertedResponse,
    summary="Добавить записи",
    description="Добавляет одну или несколько записей в базу данных",
    response_description="Количество успешно добавленных записей"
)
async def add_records(
    payload: RecordsInModel,
    service: RecordsService = Depends(get_service)
):
    try:
        items = payload.to_list()
        await service.add_records(items)
        return {"inserted": len(items)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get(
    "/",
    response_model=List[RecordOut],
    summary="Получить все записи",
    description="Возвращает все записи из базы данных в порядке убывания времени создания",
    response_description="Список всех записей"
)
async def get_records(service: RecordsService = Depends(get_service)):
    try:
        rows = await service.get_all()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get(
    "/{name}",
    response_model=RecordOut,
    summary="Получить запись по name",
    description="Возвращает последнюю (по created_at) запись для заданного поля name",
    response_description="Запись с указанным name"
)
async def get_record(name: str, service: RecordsService = Depends(get_service)):
    """
    Получение одной записи по полю name.
    - **name**: значение поля name, по которому ищем запись.
    Возвращаем последнюю по времени создания запись с таким name.
    """
    try:
        row = await service.get_by_name(name)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Record with name '{name}' not found")
        return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
