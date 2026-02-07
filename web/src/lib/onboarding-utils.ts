/**
 * Shared onboarding/industry utilities.
 * Extracted from page.tsx so multiple route pages can reuse them.
 */

export const ONBOARDING_DONE_KEY = "builder_curation_onboarding_done";
export const ONBOARDING_CONTEXT_KEY = "builder_curation_onboarding_context";

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
