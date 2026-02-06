from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from .routes.health import router as health_router
from .routes.recommendations import router as recommendations_router
from .routes.chat import router as chat_router
from .routes.prediction import router as prediction_router
from .routes.simulation import router as simulation_router
from .routes.nearby import router as nearby_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    from .services.data_service import get_data_service

    _ = get_data_service()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Builder Curation API",
        description="창업 위치 추천 및 성공 분석 API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, tags=["Health"])
    app.include_router(recommendations_router, prefix="/api/v1", tags=["Recommendations"])
    app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
    app.include_router(prediction_router, prefix="/api/v1", tags=["Prediction"])
    app.include_router(simulation_router, prefix="/api/v1", tags=["Simulation"])
    app.include_router(nearby_router, prefix="/api/v1", tags=["Nearby"])

    # Imported via importlib to avoid type-checker import resolution issues
    # in some local environments.
    from importlib import import_module
    from typing import cast

    competitive_router = cast(APIRouter, import_module("api.routes.competitive").router)
    app.include_router(competitive_router, prefix="/api/v1", tags=["Competitive"])

    return app


app = create_app()
