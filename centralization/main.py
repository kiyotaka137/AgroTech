import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
import asyncpg
from transport.routes import router as records_router

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set (see .env)")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db_pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
    async with app.state.db_pool.acquire() as conn:
        await conn.execute("SELECT 1")
    yield
    # Shutdown
    await app.state.db_pool.close()
'''
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db_pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
    
    # Создаем таблицу если не существует
    async with app.state.db_pool.acquire() as conn:
        try:
            # Проверяем существование таблицы
            table_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'records')"
            )
            
            if not table_exists:
                await conn.execute("""
                    CREATE TABLE records (
                        id UUID PRIMARY KEY,
                        data JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                """)
                print("Таблица records создана")
            else:
                print("Таблица records уже существует")
                
        except Exception as e:
            print(f" Ошибка при работе с таблицей: {e}")
            raise
    
    yield
    
    # Shutdown
    await app.state.db_pool.close()
'''

app = FastAPI(title="Records API", lifespan=lifespan)

app.include_router(records_router, prefix="/records", tags=["records"])