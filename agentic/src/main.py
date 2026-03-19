"""Main application entry point."""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference

from src.api.routes import router
from src.settings import get_settings

load_dotenv()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.langsmith_tracing:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project

    async def setup_redis():
        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        return client

    async with asyncio.TaskGroup() as tg:
        redis_task = tg.create_task(setup_redis())

    app.state.redis = redis_task.result()

    try:
        from src.agent.tools.rag import VectorStore

        app.state.vector_store = VectorStore()
    except Exception:
        app.state.vector_store = None

    yield
    await app.state.redis.aclose()


app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    response: Response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


app.include_router(router)


@app.get("/docs", include_in_schema=False)
async def scalar_docs():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title=settings.app_name)
