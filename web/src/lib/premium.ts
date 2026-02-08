// Premium feature gates and nudge logic
// During beta: all features are free
// After beta: gate certain features behind premium

export type PremiumFeature =
  | "unlimited_analysis"
  | "full_ranking"
  | "unlimited_business_plan"
  | "pdf_export"
  | "priority_support";

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
    features: [
      "기본 상권 분석",
      "TOP 5 추천",
      "사업계획서 1회/일",
      "프랜차이즈 비교",
      "지원금 매칭",
    ],
  },
  pro: {
    name: "Pro",
    price: 9900,
    features: [
      "무제한 상권 분석",
      "전체 상권 랭킹",
      "무제한 사업계획서 + PDF",
      "프랜차이즈 비교",
      "지원금 매칭",
      "우선 지원",
    ],
  },
} as const;
