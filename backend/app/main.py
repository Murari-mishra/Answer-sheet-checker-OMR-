import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import batches, exams
from app.db.base import Base
from app.db.session import engine
from app.services.jobs import requeue_stale_items, worker_loop
from app.services.storage import ensure_bucket_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_bucket_exists()
    worker_task = asyncio.create_task(worker_loop())
    await requeue_stale_items()
    yield
    worker_task.cancel()


app = FastAPI(title="OMR Track", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(exams.router, prefix="/api/v1")
app.include_router(batches.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
