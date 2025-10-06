from fastapi import APIRouter, Depends, Request, status, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel
from uuid import UUID
from centralization.repository.record_repo import RecordsRepository
from centralization.service.record_service import RecordsService

router = APIRouter()
#request для post
class RecordsInModel(BaseModel):
    __root__: List[Dict[str, Any]]

    def to_list(self):
        return self.__root__

#response для GET
class RecordOut(BaseModel):
    id: UUID
    data: Dict[str, Any]
    created_at: str

# зависимость: собираем сервис с pool из app.state
def get_service(request: Request) -> RecordsService:
    pool = request.app.state.db_pool
    repo = RecordsRepository(pool)
    service = RecordsService(repo)
    return service

@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_records(payload: RecordsInModel, service: RecordsService = Depends(get_service)):
    try:
        items = payload.to_list()
        await service.add_records(items)
        return {"inserted": len(items)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[RecordOut])
async def get_records(service: RecordsService = Depends(get_service)):
    rows = await service.get_all()
    return rows
