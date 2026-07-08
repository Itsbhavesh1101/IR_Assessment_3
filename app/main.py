from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.services.database import Database
from app.utils.config import get_settings
from app.utils.errors import AppError
from app.utils.seed_db import ensure_seed_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    database = Database(settings)
    if settings.auto_seed:
        ensure_seed_data(database, settings.mock_data_dir)
    else:
        database.ensure_schema()
    yield


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="AI School ERP Assistant", version="1.0.0", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "error_code": "INVALID_REQUEST",
            "message": "The request payload is invalid or missing required fields.",
            "details": {"errors": exc.errors()},
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_code": "UNEXPECTED_ERROR",
            "message": "An unexpected server error occurred.",
            "details": {},
        },
    )
