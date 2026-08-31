from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat, files
from app.rerank import get_cross_encoder
from app.sem_search import get_embedder


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.get_running_loop().run_in_executor(None, get_embedder)
    asyncio.get_running_loop().run_in_executor(None, get_cross_encoder)
    yield


app = FastAPI(title="RAG Portal API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(files.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
