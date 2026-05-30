"""CredChain Python AI Service — FastAPI application factory.

Single uvicorn worker, models loaded once via lifespan, structured JSON
logging, unified error envelope. Reachable only inside the Docker
backend network — never exposed to the public internet.
"""

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app import codes
from app.config import settings
from app.errors import AppError, http_status_for
from app.logger import get_logger
from app.routes import router

log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load all ML models once at startup, free them at shutdown."""
    log.info(
        "loading models",
        extra={"extra_fields": {"phase": "startup", "model_dir": settings.model_dir}},
    )
    app.state.models_loaded = False

    import easyocr
    from llama_cpp import Llama
    from sentence_transformers import SentenceTransformer

    app.state.easyocr_reader = easyocr.Reader(
        settings.easyocr_langs,
        gpu=(settings.llm_device != "cpu"),
        model_storage_directory=f"{settings.model_dir}/easyocr",
    )
    app.state.embedding_model = SentenceTransformer(
        f"{settings.model_dir}/labse",
        device=settings.llm_device,
    )
    app.state.llm = Llama(
        model_path=f"{settings.model_dir}/qwen/{settings.llm_model_file}",
        n_ctx=2048,
        n_threads=8,
        chat_format="chatml",
        verbose=False,
    )
    app.state.llm_lock = asyncio.Lock()

    app.state.models_loaded = True
    log.info("models ready", extra={"extra_fields": {"phase": "ready"}})

    yield

    log.info("shutting down", extra={"extra_fields": {"phase": "shutdown"}})


def register_error_handlers(app: FastAPI) -> None:
    """Wire AppError, validation, and unhandled-exception handlers to the
    unified Response envelope shape."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=http_status_for(exc.code),
            content={
                "code": exc.code,
                "message": exc.message,
                "errors": exc.errors,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"][1:]) or "body"
            field_errors.setdefault(loc, []).append(err["msg"])
        return JSONResponse(
            status_code=400,
            content={
                "code": codes.CODE_AI_VALIDATION,
                "message": "Validation failed",
                "errors": field_errors,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception(
            "unhandled error",
            extra={"extra_fields": {"path": request.url.path}},
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": codes.CODE_AI_INTERNAL,
                "message": "Internal server error",
            },
        )


def create_app() -> FastAPI:
    app = FastAPI(
        title="CredChain Python AI Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def request_logging_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.request_id = str(uuid.uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000
        status_code = response.status_code
        outcome = (
            "success" if 200 <= status_code < 300
            else "client_error" if 400 <= status_code < 500
            else "server_error"
        )
        log.info(
            "request completed",
            extra={"extra_fields": {
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": round(latency_ms, 2),
                "outcome": outcome,
            }},
        )
        return response

    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
