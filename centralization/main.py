import os
import asyncio
from fastapi import FastAPI
from dotenv import load_dotenv
import asyncpg
from centralization.transport.routes import router as records_router

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set (see .env.example)")

app = FastAPI(title="Records API (MVP)")

@app.on_event("startup")
async def startup():
    # создаём пул соединений и сохраняем
    app.state.db_pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
    # Можно проверить соединение:
    async with app.state.db_pool.acquire() as conn:
        await conn.execute("SELECT 1")

@app.on_event("shutdown")
async def shutdown():
    pool = getattr(app.state, "db_pool", None)
    if pool:
        await pool.close()

# регистрируем маршруты
app.include_router(records_router, prefix="/records", tags=["records"])
