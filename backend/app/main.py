"""
AuricVision — Defense Intelligence Platform
Main FastAPI application
"""
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.registry import ModelRegistry
from app.api.v1.routes import detect, fuse, geolocate, prioritize, change, pipeline, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AuricVision — starting up")
    logger.info(f"  env={settings.ENV}  device={settings.device}  v={settings.VERSION}")
    registry = ModelRegistry()
    await registry.load_all()
    app.state.registry = registry
    logger.info("✅  All systems ready")
    yield
    logger.info("Shutting down…")
    await registry.release()


def build_app() -> FastAPI:
    app = FastAPI(
        title="AuricVision API",
        description="AI-powered defense intelligence: detect · fuse · geolocate · prioritize · change-detect",
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.middleware("http")
    async def timing(request: Request, call_next):
        t0 = time.perf_counter()
        resp = await call_next(request)
        resp.headers["X-Process-Time-Ms"] = str(round((time.perf_counter()-t0)*1000, 2))
        return resp

    @app.exception_handler(Exception)
    async def catch_all(request: Request, exc: Exception):
        logger.error(f"Unhandled: {request.url}  {exc}")
        return JSONResponse(500, {"error": str(exc)})

    v = f"/api/{settings.API_VERSION}"
    app.include_router(health.router)
    app.include_router(detect.router,     prefix=f"{v}/detect",     tags=["Detection"])
    app.include_router(fuse.router,       prefix=f"{v}/fuse",       tags=["Fusion"])
    app.include_router(geolocate.router,  prefix=f"{v}/geolocate",  tags=["Geospatial"])
    app.include_router(prioritize.router, prefix=f"{v}/prioritize", tags=["Prioritization"])
    app.include_router(change.router,     prefix=f"{v}/change",     tags=["Change Detection"])
    app.include_router(pipeline.router,   prefix=f"{v}/pipeline",   tags=["Pipeline"])
    return app


app = build_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000,
                reload=settings.ENV == "development")
