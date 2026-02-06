"""
ML Service - sklearn 기반 커피숍 창업 성공 예측 서비스
GradientBoostingRegressor를 사용한 survival_rate 예측
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler


class MLService:
    """커피숍 창업 성공 예측 ML 서비스 (싱글톤)"""

    _instance: "MLService | None" = None

    # 학습에 사용할 피처 목록 (15개 이상)
    FEATURE_COLUMNS = [
        "monthly_sales",
        "monthly_transactions",
        "store_count",
        "franchise_stores",
        "new_stores",
        "closed_stores",
        "weekday_ratio",
        "weekend_ratio",
        "male_ratio",
        "female_ratio",
        # 연령대별 매출 비율
        "age_10_ratio",
        "age_20_ratio",
        "age_30_ratio",
        "age_40_ratio",
        "age_50_ratio",
        "age_60_ratio",
        # 시간대별 매출 비율
        "time_06_11_ratio",
        "time_11_14_ratio",
        "time_14_17_ratio",
        "time_17_21_ratio",
    ]

    # 피처 한글 이름 매핑
    FEATURE_NAMES_KO = {
        "monthly_sales": "월 매출",
        "monthly_transactions": "월 거래수",
        "store_count": "점포 수",
        "franchise_stores": "프랜차이즈 수",
        "new_stores": "신규 점포",
        "closed_stores": "폐업 점포",
        "weekday_ratio": "주중 비율",
        "weekend_ratio": "주말 비율",
        "male_ratio": "남성 비율",
        "female_ratio": "여성 비율",
        "age_10_ratio": "10대 비율",
        "age_20_ratio": "20대 비율",
        "age_30_ratio": "30대 비율",
        "age_40_ratio": "40대 비율",
        "age_50_ratio": "50대 비율",
        "age_60_ratio": "60대 비율",
        "time_06_11_ratio": "아침(6-11시) 비율",
        "time_11_14_ratio": "점심(11-14시) 비율",
        "time_14_17_ratio": "오후(14-17시) 비율",
        "time_17_21_ratio": "저녁(17-21시) 비율",
    }

    def __new__(cls) -> "MLService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self.model: GradientBoostingRegressor | None = None
        self.scaler: StandardScaler | None = None
        self.feature_importances: dict[str, float] = {}
        self.model_metrics: dict[str, float] = {}
        self.districts: list[dict[str, Any]] = []
        self._district_by_code: dict[str, dict[str, Any]] = {}

        self._load_data()
        self._train_model()

    def _load_data(self) -> None:
        """coffee_districts.json 데이터 로드"""
        data_path = (
            Path(__file__).parent.parent.parent / "data" / "processed" / "coffee_districts.json"
        )

        with open(data_path, encoding="utf-8") as f:
            self.districts = json.load(f)

        self._district_by_code = {d["district_code"]: d for d in self.districts}
        print(f"[MLService] 데이터 로드 완료: {len(self.districts)}개 상권")

    def _extract_features(self, district: dict[str, Any]) -> dict[str, float]:
        """상권 데이터에서 피처 추출"""
        monthly_sales = max(1, district.get("monthly_sales", 1))

        features = {
            "monthly_sales": district.get("monthly_sales", 0),
            "monthly_transactions": district.get("monthly_transactions", 0),
            "store_count": district.get("store_count", 0),
            "franchise_stores": district.get("franchise_stores", 0),
            "new_stores": district.get("new_stores", 0),
            "closed_stores": district.get("closed_stores", 0),
            "weekday_ratio": district.get("weekday_ratio", 0.7),
            "weekend_ratio": district.get("weekend_ratio", 0.3),
            "male_ratio": district.get("male_ratio", 0.5),
            "female_ratio": district.get("female_ratio", 0.5),
            # 연령대별 매출 비율
            "age_10_ratio": district.get("age_10_sales", 0) / monthly_sales,
            "age_20_ratio": district.get("age_20_sales", 0) / monthly_sales,
            "age_30_ratio": district.get("age_30_sales", 0) / monthly_sales,
            "age_40_ratio": district.get("age_40_sales", 0) / monthly_sales,
            "age_50_ratio": district.get("age_50_sales", 0) / monthly_sales,
            "age_60_ratio": district.get("age_60_sales", 0) / monthly_sales,
            # 시간대별 매출 비율
            "time_06_11_ratio": district.get("time_06_11_sales", 0) / monthly_sales,
            "time_11_14_ratio": district.get("time_11_14_sales", 0) / monthly_sales,
            "time_14_17_ratio": district.get("time_14_17_sales", 0) / monthly_sales,
            "time_17_21_ratio": district.get("time_17_21_sales", 0) / monthly_sales,
        }

        return features

    def _prepare_training_data(self) -> tuple[np.ndarray, np.ndarray]:
        """학습 데이터 준비"""
        X_list: list[list[float]] = []
        y_list: list[float] = []

        for district in self.districts:
            # survival_rate 이상치 제거 (0~1 범위만)
            survival_rate = district.get("survival_rate", 0)
            if survival_rate < 0 or survival_rate > 1:
                # 1 초과 시 1로 클리핑
                survival_rate = min(1.0, max(0.0, survival_rate))

            features = self._extract_features(district)
            feature_values = [features[col] for col in self.FEATURE_COLUMNS]

            X_list.append(feature_values)
            y_list.append(survival_rate)

        return np.array(X_list), np.array(y_list)

    def _train_model(self) -> None:
        """모델 학습"""
        X, y = self._prepare_training_data()

        # 데이터 정규화
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # GradientBoostingRegressor 모델 학습
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=4,
            min_samples_split=5,
            min_samples_leaf=3,
            random_state=42,
        )
        self.model.fit(X_scaled, y)

        # 교차 검증 점수
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=5, scoring="r2")
        self.model_metrics = {
            "r2_mean": float(np.mean(cv_scores)),
            "r2_std": float(np.std(cv_scores)),
            "n_samples": len(y),
            "n_features": len(self.FEATURE_COLUMNS),
        }

        # 피처 중요도 저장
        importances = self.model.feature_importances_
        self.feature_importances = {
            col: float(imp) for col, imp in zip(self.FEATURE_COLUMNS, importances)
        }

        print(
            f"[MLService] 모델 학습 완료 - R² Score: {self.model_metrics['r2_mean']:.4f} (±{self.model_metrics['r2_std']:.4f})"
        )

    def predict_success(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        성공 확률 예측

        Args:
            features: 피처 딕셔너리 (district_code 또는 커스텀 피처)

        Returns:
            - success_probability: 예측된 성공 확률 (0~1)
            - confidence_interval: 신뢰구간 [lower, upper]
            - key_factors: 주요 영향 요인 리스트
        """
        if self.model is None or self.scaler is None:
            raise RuntimeError("모델이 학습되지 않았습니다")

        # district_code로 조회하는 경우
        if "district_code" in features:
            district = self._district_by_code.get(features["district_code"])
            if district is None:
                raise ValueError(f"상권 코드 {features['district_code']}를 찾을 수 없습니다")
            extracted_features = self._extract_features(district)
        else:
            # 커스텀 피처 사용
            extracted_features = self._fill_missing_features(features)

        # 피처 배열 생성
        feature_values = [extracted_features.get(col, 0) for col in self.FEATURE_COLUMNS]
        X = np.array([feature_values])
        X_scaled = self.scaler.transform(X)

        # 예측
        prediction = float(self.model.predict(X_scaled)[0])
        # 0~1 범위로 클리핑
        prediction = max(0.0, min(1.0, prediction))

        # 신뢰구간 계산 (staged_predict 활용)
        staged_predictions = list(self.model.staged_predict(X_scaled))
        predictions_std = np.std([p[0] for p in staged_predictions[-20:]])
        confidence_interval = [
            max(0.0, prediction - 1.96 * predictions_std),
            min(1.0, prediction + 1.96 * predictions_std),
        ]

        # 주요 영향 요인 추출
        key_factors = self._extract_key_factors(extracted_features)

        return {
            "success_probability": round(prediction, 4),
            "confidence_interval": [round(ci, 4) for ci in confidence_interval],
            "key_factors": key_factors,
            "model_metrics": self.model_metrics,
        }

    def _fill_missing_features(self, features: dict[str, Any]) -> dict[str, float]:
        """누락된 피처를 기본값으로 채움"""
        defaults = {
            "monthly_sales": 50000000,
            "monthly_transactions": 5000,
            "store_count": 5,
            "franchise_stores": 2,
            "new_stores": 1,
            "closed_stores": 1,
            "weekday_ratio": 0.7,
            "weekend_ratio": 0.3,
            "male_ratio": 0.4,
            "female_ratio": 0.6,
            "age_10_ratio": 0.02,
            "age_20_ratio": 0.2,
            "age_30_ratio": 0.25,
            "age_40_ratio": 0.2,
            "age_50_ratio": 0.18,
            "age_60_ratio": 0.15,
            "time_06_11_ratio": 0.15,
            "time_11_14_ratio": 0.35,
            "time_14_17_ratio": 0.3,
            "time_17_21_ratio": 0.2,
        }

        result: dict[str, float] = {}
        for col in self.FEATURE_COLUMNS:
            if col in features:
                result[col] = float(features[col])
            else:
                result[col] = defaults.get(col, 0.0)

        return result

    def _extract_key_factors(self, features: dict[str, float]) -> list[dict[str, Any]]:
        """주요 영향 요인 추출"""
        # 피처 중요도 기준 상위 5개
        sorted_importance = sorted(
            self.feature_importances.items(), key=lambda x: x[1], reverse=True
        )[:5]

        key_factors = []
        for feature_name, importance in sorted_importance:
            value = features.get(feature_name, 0)
            korean_name = self.FEATURE_NAMES_KO.get(feature_name, feature_name)

            # 해당 피처 값의 상대적 위치 판단
            if feature_name in ["store_count", "closed_stores"]:
                impact = "negative" if value > 10 else "positive"
            elif feature_name in ["monthly_sales", "monthly_transactions"]:
                impact = "positive" if value > 30000000 else "neutral"
            else:
                impact = "positive" if value > 0.3 else "neutral"

            key_factors.append(
                {
                    "feature": feature_name,
                    "feature_name_ko": korean_name,
                    "importance": round(importance, 4),
                    "value": round(value, 4) if isinstance(value, float) else value,
                    "impact": impact,
                }
            )

        return key_factors

    def get_feature_importance(self) -> dict[str, Any]:
        """피처 중요도 반환"""
        if not self.feature_importances:
            raise RuntimeError("모델이 학습되지 않았습니다")

        sorted_importance = sorted(
            self.feature_importances.items(), key=lambda x: x[1], reverse=True
        )

        return {
            "feature_importances": [
                {
                    "feature": name,
                    "feature_name_ko": self.FEATURE_NAMES_KO.get(name, name),
                    "importance": round(imp, 4),
                    "rank": idx + 1,
                }
                for idx, (name, imp) in enumerate(sorted_importance)
            ],
            "model_type": "GradientBoostingRegressor",
            "model_metrics": self.model_metrics,
            "total_features": len(self.FEATURE_COLUMNS),
        }

    def get_district(self, district_code: str) -> dict[str, Any] | None:
        """상권 코드로 상권 데이터 조회"""
        return self._district_by_code.get(district_code)


def get_ml_service() -> MLService:
    """MLService 싱글톤 인스턴스 반환"""
    return MLService()
