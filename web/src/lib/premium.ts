// Premium feature gates and nudge logic
// During beta: all features are free
// After beta: gate certain features behind premium

export type PremiumFeature =
  | "unlimited_analysis"
  | "full_ranking"
  | "unlimited_business_plan"
  | "pdf_export"
  | "priority_support"
  // Report section features (v0.9+)
  | "detailed_scorecard"
  | "revenue_waterfall"
  | "competition_map"
  | "location_profile"
  | "full_customer_charts"
  | "rent_trend"
  | "franchise_comparison"
  | "simulator_full"
  | "risk_full";

interface PremiumConfig {
  isBeta: boolean;
  features: Record<PremiumFeature, { free: boolean; description: string }>;
}

const CONFIG: PremiumConfig = {
  isBeta: true, // Set to false when beta ends
  features: {
    unlimited_analysis: {
      free: false,
      description: "무제한 상권 분석",
    },
    full_ranking: {
      free: false,
      description: "전체 상권 랭킹 (TOP 5 → 전체)",
    },
    unlimited_business_plan: {
      free: false,
      description: "무제한 사업계획서 생성",
    },
    pdf_export: {
      free: false,
      description: "사업계획서 PDF 다운로드",
    },
    priority_support: {
      free: false,
      description: "우선 지원",
    },
    // Report section features
    detailed_scorecard: {
      free: false,
      description: "5대 카테고리 레이더 + 서울 평균 비교",
    },
    revenue_waterfall: {
      free: false,
      description: "워터폴 전체 + 투자회수 기간",
    },
    competition_map: {
      free: false,
      description: "LOCALDATA 경쟁점포 지도 + AI 차별화",
    },
    location_profile: {
      free: false,
      description: "용도지역 + 학교 + 주차장 전체",
    },
    full_customer_charts: {
      free: false,
      description: "전체 고객 분석 차트",
    },
    rent_trend: {
      free: false,
      description: "3년 임대료 트렌드",
    },
    franchise_comparison: {
      free: false,
      description: "프랜차이즈 AI 추천 포함",
    },
    simulator_full: {
      free: false,
      description: "3개 슬라이더 시뮬레이터",
    },
    risk_full: {
      free: false,
      description: "전체 리스크 + AI 판정",
    },
  },
};

export function isFeatureAvailable(feature: PremiumFeature): boolean {
  if (CONFIG.isBeta) return true; // All features free during beta
  return CONFIG.features[feature]?.free ?? false;
}

export function getPremiumNudgeMessage(feature: PremiumFeature): string | null {
  if (CONFIG.isBeta) return null; // No nudges during beta
  if (isFeatureAvailable(feature)) return null;

  const desc = CONFIG.features[feature]?.description || "프리미엄 기능";
  return `${desc}은 Pro 플랜에서 이용 가능합니다.`;
}

export function isBeta(): boolean {
  return CONFIG.isBeta;
}

export const PRICING = {
  free: {
    name: "무료",
    price: 0,
    description: "월 1회 기본 분석",
    features: [
      "기본 상권 분석 (TOP 3)",
      "종합점수 1개",
      "월매출/순이익 요약",
      "경쟁 점포수",
      "주요 연령/교통",
      "지원금 TOP 2",
    ],
  },
  pro_single: {
    name: "Pro 건당",
    price: 4900,
    description: "전체 리포트 1건",
    features: [
      "5대 카테고리 레이더",
      "워터폴 수익 구조",
      "경쟁 지도 + AI 차별화",
      "용도지역/학교/주차장",
      "전체 고객 차트",
      "3년 임대료 트렌드",
      "프랜차이즈 AI 추천",
      "3-슬라이더 시뮬레이터",
      "전체 리스크 + AI 판정",
      "전체 지원금",
    ],
  },
  pro_monthly: {
    name: "Pro 구독",
    price: 19900,
    description: "무제한 분석",
    features: [
      "Pro 건당 모든 기능",
      "무제한 분석",
      "PDF 다운로드",
      "우선 지원",
    ],
  },
} as const;
