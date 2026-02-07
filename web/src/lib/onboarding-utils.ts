/**
 * Shared onboarding/industry utilities.
 * Extracted from page.tsx so multiple route pages can reuse them.
 */

export const ONBOARDING_DONE_KEY = "builder_curation_onboarding_done";
export const ONBOARDING_CONTEXT_KEY = "builder_curation_onboarding_context";

export const CAFE_TYPE_LABELS: Record<string, string> = {
  takeout: "테이크아웃 카페",
  brunch: "브런치 카페",
  aesthetic: "감성 카페",
  study: "스터디 카페",
};

export const BUDGET_RENT_LABELS: Record<string, string> = {
  low: "월세 150~300만원",
  mid: "월세 200~500만원",
  high: "월세 300~800만원",
};

export const TARGET_LABELS: Record<string, string> = {
  office: "직장인",
  "20s_female": "20대 여성",
  "30s": "30~40대",
  student: "대학생",
  local: "동네 주민",
  tourist: "관광객",
};

export const INDUSTRY_NAMES: Record<string, string> = {
  CS100001: "한식",
  CS100002: "중식",
  CS100003: "일식",
  CS100004: "양식",
  CS100005: "베이커리",
  CS100006: "패스트푸드",
  CS100007: "치킨",
  CS100008: "분식",
  CS100009: "호프/주점",
  CS100010: "카페",
};

export const INDUSTRY_ICONS: Record<string, string> = {
  CS100001: "🍚",
  CS100002: "🥟",
  CS100003: "🍣",
  CS100004: "🍝",
  CS100005: "🍞",
  CS100006: "🍔",
  CS100007: "🍗",
  CS100008: "🍜",
  CS100009: "🍺",
  CS100010: "☕",
};

export function getStoredIndustry(): { code: string; name: string; icon: string } {
  if (typeof window === "undefined") return { code: "CS100010", name: "카페", icon: "☕" };
  const code = window.localStorage.getItem("builder_curation_industry_code") || "CS100010";
  return {
    code,
    name: INDUSTRY_NAMES[code] || "카페",
    icon: INDUSTRY_ICONS[code] || "☕",
  };
}

export interface OnboardingDataCompat {
  industryCode?: string;
  cafeType: string;
  budget: string;
  target: string;
  district: string | null;
}

export function buildAutoQuery(data: OnboardingDataCompat): string {
  const location = data.district ? `서울 ${data.district}` : "서울";
  const rent = BUDGET_RENT_LABELS[data.budget];
  const rentPart = rent ? ` ${rent}으로` : "";
  const industryName = INDUSTRY_NAMES[data.industryCode || "CS100010"] || "카페";
  const cafeLabel =
    data.industryCode === "CS100010"
      ? CAFE_TYPE_LABELS[data.cafeType] || industryName
      : industryName;
  const targetLabel = TARGET_LABELS[data.target];
  const targetPart = targetLabel ? `, ${targetLabel} 타겟` : "";

  return `${location}에서${rentPart}${targetPart} ${cafeLabel} 창업 추천해줘`;
}

export function rentDefaultsFromOnboarding(budgetId: string): {
  budgetMin: number;
  budgetMax: number;
} {
  switch (budgetId) {
    case "low":
      return { budgetMin: 1500000, budgetMax: 3000000 };
    case "mid":
      return { budgetMin: 2000000, budgetMax: 5000000 };
    case "high":
      return { budgetMin: 3000000, budgetMax: 8000000 };
    default:
      return { budgetMin: 2000000, budgetMax: 5000000 };
  }
}
