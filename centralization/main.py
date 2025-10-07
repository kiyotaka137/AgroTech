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

app = FastAPI(title="Records API", lifespan=lifespan)

app.include_router(records_router, prefix="/records", tags=["records"])