"""
Prediction Routes - ML 기반 창업 성공 예측 API
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.services.ml_service import get_ml_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prediction")


class PredictionRequest(BaseModel):
    """예측 요청 모델"""

    district_code: str | None = Field(
        default=None, description="상권 코드 (coffee_districts.json의 district_code)"
    )
    # 커스텀 피처 (district_code가 없을 경우 사용)
    monthly_sales: float | None = Field(default=None, description="월 매출")
    monthly_transactions: int | None = Field(default=None, description="월 거래수")
    store_count: int | None = Field(default=None, description="점포 수")
    franchise_stores: int | None = Field(default=None, description="프랜차이즈 수")
    new_stores: int | None = Field(default=None, description="신규 점포")
    closed_stores: int | None = Field(default=None, description="폐업 점포")
    weekday_ratio: float | None = Field(default=None, description="주중 비율 (0~1)")
    weekend_ratio: float | None = Field(default=None, description="주말 비율 (0~1)")
    male_ratio: float | None = Field(default=None, description="남성 비율 (0~1)")
    female_ratio: float | None = Field(default=None, description="여성 비율 (0~1)")
    age_10_ratio: float | None = Field(default=None, description="10대 매출 비율")
    age_20_ratio: float | None = Field(default=None, description="20대 매출 비율")
    age_30_ratio: float | None = Field(default=None, description="30대 매출 비율")
    age_40_ratio: float | None = Field(default=None, description="40대 매출 비율")
    age_50_ratio: float | None = Field(default=None, description="50대 매출 비율")
    age_60_ratio: float | None = Field(default=None, description="60대 매출 비율")
    time_06_11_ratio: float | None = Field(default=None, description="아침(6-11시) 매출 비율")
    time_11_14_ratio: float | None = Field(default=None, description="점심(11-14시) 매출 비율")
    time_14_17_ratio: float | None = Field(default=None, description="오후(14-17시) 매출 비율")
    time_17_21_ratio: float | None = Field(default=None, description="저녁(17-21시) 매출 비율")


class KeyFactor(BaseModel):
    """주요 영향 요인"""

    feature: str
    feature_name_ko: str
    importance: float
    value: float
    impact: str


class ModelMetrics(BaseModel):
    """모델 성능 지표"""

    r2_mean: float
    r2_std: float
    n_samples: int
    n_features: int


class PredictionResponse(BaseModel):
    """예측 응답 모델"""

    success_probability: float = Field(description="예측된 성공 확률 (0~1)")
    confidence_interval: list[float] = Field(description="95% 신뢰구간 [lower, upper]")
    key_factors: list[KeyFactor] = Field(description="주요 영향 요인")
    model_metrics: ModelMetrics = Field(description="모델 성능 지표")
    district_info: dict[str, Any] | None = Field(
        default=None, description="상권 정보 (district_code로 조회 시)"
    )


class FeatureImportanceItem(BaseModel):
    """피처 중요도 항목"""

    feature: str
    feature_name_ko: str
    importance: float
    rank: int


class FeatureImportanceResponse(BaseModel):
    """피처 중요도 응답 모델"""

    feature_importances: list[FeatureImportanceItem]
    model_type: str
    model_metrics: ModelMetrics
    total_features: int


@router.post("/predict", response_model=PredictionResponse)
async def predict_success(request: PredictionRequest) -> PredictionResponse:
    """
    커피숍 창업 성공 확률 예측

    - district_code로 기존 상권 데이터 기반 예측
    - 또는 커스텀 피처로 가상 시나리오 예측
    """
    ml_service = get_ml_service()

    # 요청 데이터를 딕셔너리로 변환 (None 값 제외)
    features: dict[str, Any] = {}

    if request.district_code:
        features["district_code"] = request.district_code
    else:
        # 커스텀 피처 수집
        request_dict = request.model_dump(exclude_none=True, exclude={"district_code"})
        features.update(request_dict)

    if not features:
        raise HTTPException(
            status_code=400,
            detail="district_code 또는 최소 하나의 피처를 제공해야 합니다",
        )

    try:
        result = ml_service.predict_success(features)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

    # 상권 정보 추가 (district_code로 조회한 경우)
    district_info = None
    if request.district_code:
        district = ml_service.get_district(request.district_code)
        if district:
            district_info = {
                "district_code": district["district_code"],
                "district_name": district["district_name"],
                "district_type": district["district_type"],
                "monthly_sales": district["monthly_sales"],
                "store_count": district["store_count"],
                "survival_rate_actual": district["survival_rate"],
            }

    return PredictionResponse(
        success_probability=result["success_probability"],
        confidence_interval=result["confidence_interval"],
        key_factors=[KeyFactor(**f) for f in result["key_factors"]],
        model_metrics=ModelMetrics(**result["model_metrics"]),
        district_info=district_info,
    )


@router.get("/importance", response_model=FeatureImportanceResponse)
async def get_feature_importance() -> FeatureImportanceResponse:
    """
    피처 중요도 조회

    모델 학습에 사용된 각 피처의 중요도를 반환합니다.
    중요도가 높을수록 성공 예측에 더 큰 영향을 미칩니다.
    """
    ml_service = get_ml_service()

    try:
        result = ml_service.get_feature_importance()
    except RuntimeError as e:
        logger.error(f"Feature importance error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

    return FeatureImportanceResponse(
        feature_importances=[FeatureImportanceItem(**f) for f in result["feature_importances"]],
        model_type=result["model_type"],
        model_metrics=ModelMetrics(**result["model_metrics"]),
        total_features=result["total_features"],
    )


@router.get("/districts/{district_code}/predict", response_model=PredictionResponse)
async def predict_by_district(district_code: str) -> PredictionResponse:
    """
    특정 상권의 성공 확률 예측 (GET 방식)

    URL 경로로 상권 코드를 받아 예측 결과를 반환합니다.
    """
    ml_service = get_ml_service()

    district = ml_service.get_district(district_code)
    if not district:
        raise HTTPException(status_code=404, detail=f"상권 코드 {district_code}를 찾을 수 없습니다")

    try:
        result = ml_service.predict_success({"district_code": district_code})
    except (ValueError, RuntimeError) as e:
        logger.error(f"District prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

    district_info = {
        "district_code": district["district_code"],
        "district_name": district["district_name"],
        "district_type": district["district_type"],
        "monthly_sales": district["monthly_sales"],
        "store_count": district["store_count"],
        "survival_rate_actual": district["survival_rate"],
    }

    return PredictionResponse(
        success_probability=result["success_probability"],
        confidence_interval=result["confidence_interval"],
        key_factors=[KeyFactor(**f) for f in result["key_factors"]],
        model_metrics=ModelMetrics(**result["model_metrics"]),
        district_info=district_info,
    )
