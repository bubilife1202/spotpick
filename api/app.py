from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
import time
from collections import defaultdict

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .routes.health import router as health_router
from .routes.recommendations import router as recommendations_router
from .routes.chat import router as chat_router
from .routes.prediction import router as prediction_router
from .routes.simulation import router as simulation_router
from .routes.nearby import router as nearby_router
from .routes.districts import router as districts_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    from .services.data_service import get_data_service

    _ = get_data_service()
    yield


class RateLimitMiddleware:
    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        self.app = app
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            client_ip = scope.get("client", ("unknown", 0))[0]
            now = time.time()
            # Clean old entries
            self.requests[client_ip] = [
                t for t in self.requests[client_ip] if now - t < self.window
            ]
            if len(self.requests[client_ip]) >= self.max_requests:
                response = JSONResponse(
                    {"detail": "Too many requests. Please try again later."},
                    status_code=429,
                )
                await response(scope, receive, send)
                return
            self.requests[client_ip].append(now)
        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Builder Curation API",
        description="창업 위치 추천 및 성공 분석 API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        # Dev mode: allow all origins. For production, restrict to deployed domain(s).
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    app.add_middleware(RateLimitMiddleware, max_requests=60, window_seconds=60)

    app.include_router(health_router, tags=["Health"])
    app.include_router(recommendations_router, prefix="/api/v1", tags=["Recommendations"])
    app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
    app.include_router(prediction_router, prefix="/api/v1", tags=["Prediction"])
    app.include_router(simulation_router, prefix="/api/v1", tags=["Simulation"])
    app.include_router(nearby_router, prefix="/api/v1", tags=["Nearby"])
    app.include_router(districts_router, prefix="/api/v1", tags=["Districts"])

    # Imported via importlib to avoid type-checker import resolution issues
    # in some local environments.
    from importlib import import_module
    from typing import cast

    competitive_router = cast(APIRouter, import_module("api.routes.competitive").router)
    app.include_router(competitive_router, prefix="/api/v1", tags=["Competitive"])

    scorecard_router = cast(APIRouter, import_module("api.routes.scorecard").router)
    app.include_router(scorecard_router, prefix="/api/v1", tags=["Scorecard"])

    industries_router = cast(APIRouter, import_module("api.routes.industries").router)
    app.include_router(industries_router, prefix="/api/v1", tags=["Industries"])

    trademark_router = cast(APIRouter, import_module("api.routes.trademark").router)
    app.include_router(trademark_router, prefix="/api/v1", tags=["Trademark"])

    pdf_router = cast(APIRouter, import_module("api.routes.pdf").router)
    app.include_router(pdf_router, prefix="/api/v1", tags=["PDF"])

    support_router = cast(APIRouter, import_module("api.routes.support").router)
    app.include_router(support_router, prefix="/api/v1", tags=["Support"])

    trends_router = cast(APIRouter, import_module("api.routes.trends").router)
    app.include_router(trends_router, prefix="/api/v1", tags=["Trends"])

    franchise_router = cast(APIRouter, import_module("api.routes.franchise").router)
    app.include_router(franchise_router, prefix="/api/v1", tags=["Franchise"])

    kosis_router = cast(APIRouter, import_module("api.routes.kosis").router)
    app.include_router(kosis_router, prefix="/api/v1", tags=["KOSIS"])

    income_router = cast(APIRouter, import_module("api.routes.income").router)
    app.include_router(income_router, prefix="/api/v1", tags=["Income"])

    report_router = cast(APIRouter, import_module("api.routes.report").router)
    app.include_router(report_router, prefix="/api/v1", tags=["Report"])

    dashboard_router = cast(APIRouter, import_module("api.routes.dashboard").router)
    app.include_router(dashboard_router, prefix="/api/v1", tags=["Dashboard"])

    business_plan_router = cast(APIRouter, import_module("api.routes.business_plan").router)
    app.include_router(business_plan_router, prefix="/api/v1", tags=["BusinessPlan"])

    explore_router = cast(APIRouter, import_module("api.routes.explore").router)
    app.include_router(explore_router, prefix="/api/v1", tags=["Explore"])

    location_router = cast(APIRouter, import_module("api.routes.location").router)
    app.include_router(location_router, prefix="/api/v1", tags=["Location"])

    compare_router = cast(APIRouter, import_module("api.routes.compare").router)
    app.include_router(compare_router, prefix="/api/v1", tags=["Compare"])

    timeline_router = cast(APIRouter, import_module("api.routes.timeline").router)
    app.include_router(timeline_router, prefix="/api/v1", tags=["Timeline"])

    analytics_router = cast(APIRouter, import_module("api.routes.analytics").router)
    app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])

    property_router = cast(APIRouter, import_module("api.routes.property").router)
    app.include_router(property_router, prefix="/api/v1", tags=["Property"])

    verdict_router = cast(APIRouter, import_module("api.routes.verdict").router)
    app.include_router(verdict_router, prefix="/api/v1", tags=["Verdict"])

    cafe_type_router = cast(APIRouter, import_module("api.routes.cafe_type").router)
    app.include_router(cafe_type_router, prefix="/api/v1", tags=["CafeType"])

    tax_router = cast(APIRouter, import_module("api.routes.tax").router)
    app.include_router(tax_router, prefix="/api/v1", tags=["Tax"])

    labor_router = cast(APIRouter, import_module("api.routes.labor").router)
    app.include_router(labor_router, prefix="/api/v1", tags=["Labor"])

    lease_router = cast(APIRouter, import_module("api.routes.lease").router)
    app.include_router(lease_router, prefix="/api/v1", tags=["Lease"])

    compliance_router = cast(APIRouter, import_module("api.routes.compliance").router)
    app.include_router(compliance_router, prefix="/api/v1", tags=["Compliance"])

    return app


app = create_app()
