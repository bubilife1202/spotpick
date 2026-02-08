import { create } from "zustand";

export type JourneyStep = 1 | 2 | 3 | 4 | 5 | 6 | 7;

export const JOURNEY_STEPS = [
  { num: 1 as const, label: "업종", short: "업종선택" },
  { num: 2 as const, label: "비교", short: "프랜차이즈비교" },
  { num: 3 as const, label: "입지", short: "입지추천" },
  { num: 4 as const, label: "분석", short: "상세분석" },
  { num: 5 as const, label: "시뮬", short: "수익시뮬" },
  { num: 6 as const, label: "지원", short: "지원금매칭" },
  { num: 7 as const, label: "플랜", short: "사업계획서" },
] as const;

export const INDUSTRY_NAMES: Record<string, string> = {
  CS100001: "한식", CS100002: "중식", CS100003: "일식", CS100004: "양식",
  CS100005: "베이커리", CS100006: "패스트푸드", CS100007: "치킨",
  CS100008: "분식", CS100009: "호프/주점", CS100010: "카페",
};

export const INDUSTRY_ICONS: Record<string, string> = {
  CS100001: "🍚", CS100002: "🥟", CS100003: "🍣", CS100004: "🍝",
  CS100005: "🍞", CS100006: "🍔", CS100007: "🍗",
  CS100008: "🍜", CS100009: "🍺", CS100010: "☕",
};

export interface SelectedDistrict {
  district_code: string;
  district_name: string;
  district_type: string;
  success_probability: number;
  estimated_rent: number;
  monthly_sales?: number;
  store_count?: number;
  survival_rate?: number;
  peak_time?: string;
  main_age_group?: string;
  coordinates?: { lat: number; lng: number };
}

interface JourneyState {
  step: JourneyStep;
  industryCode: string;
  industryName: string;
  industryIcon: string;
  budgetMin: number;
  budgetMax: number;
  districts: string[];
  selectedDistrict: SelectedDistrict | null;
  franchiseChoice: "franchise" | "independent" | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  matchedPrograms: any[];

  setStep: (step: JourneyStep) => void;
  setIndustry: (code: string) => void;
  setBudget: (min: number, max: number) => void;
  setDistricts: (districts: string[]) => void;
  selectDistrict: (district: SelectedDistrict) => void;
  setFranchiseChoice: (choice: "franchise" | "independent") => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setMatchedPrograms: (programs: any[]) => void;
  goToFranchise: () => string;
  goToSupport: () => string;
  goToReport: () => string;
  goToSimulator: () => string;
  goToBusinessPlan: () => string;
  goToSummary: () => string;
  reset: () => void;
  initFromLocalStorage: () => void;
}

export const useJourneyStore = create<JourneyState>((set, get) => ({
  step: 1,
  industryCode: "CS100010",
  industryName: "카페",
  industryIcon: "☕",
  budgetMin: 3000,
  budgetMax: 20000,
  districts: [],
  selectedDistrict: null,
  franchiseChoice: null,
  matchedPrograms: [],

  setStep: (step) => set({ step }),

  setIndustry: (code) => {
    const name = INDUSTRY_NAMES[code] || "카페";
    const icon = INDUSTRY_ICONS[code] || "☕";
    set({ industryCode: code, industryName: name, industryIcon: icon });
    if (typeof window !== "undefined") {
      window.localStorage.setItem("builder_curation_industry_code", code);
    }
  },

  setBudget: (min, max) => set({ budgetMin: min, budgetMax: max }),

  setDistricts: (districts) => set({ districts }),

  selectDistrict: (district) => set({ selectedDistrict: district, step: 4 }),

  setFranchiseChoice: (choice) => set({ franchiseChoice: choice }),

  setMatchedPrograms: (programs) => set({ matchedPrograms: programs }),

  goToFranchise: () => {
    const { industryCode } = get();
    return `/franchise?industry_code=${industryCode}`;
  },

  goToSupport: () => {
    const { selectedDistrict, industryCode, budgetMin, budgetMax } = get();
    const params = new URLSearchParams();
    params.set("industry_code", industryCode);
    if (selectedDistrict) params.set("district_code", selectedDistrict.district_code);
    params.set("budget_min", String(budgetMin));
    params.set("budget_max", String(budgetMax));
    return `/support?${params.toString()}`;
  },

  goToReport: () => {
    const { selectedDistrict, industryCode } = get();
    if (!selectedDistrict) return "/explore";
    return `/report?district_code=${selectedDistrict.district_code}&industry_code=${industryCode}`;
  },

  goToSimulator: () => {
    const { selectedDistrict, industryCode } = get();
    if (!selectedDistrict) return "/simulator";
    return `/simulator?district_code=${selectedDistrict.district_code}&industry_code=${industryCode}`;
  },

  goToBusinessPlan: () => {
    const { selectedDistrict, industryCode } = get();
    if (!selectedDistrict) return "/business-plan";
    return `/business-plan?district_code=${selectedDistrict.district_code}&industry_code=${industryCode}`;
  },

  goToSummary: () => {
    const { selectedDistrict, industryCode } = get();
    if (!selectedDistrict) return "/summary";
    return `/summary?district_code=${selectedDistrict.district_code}&industry_code=${industryCode}`;
  },

  reset: () => set({
    step: 1,
    industryCode: "CS100010",
    industryName: "카페",
    industryIcon: "☕",
    budgetMin: 3000,
    budgetMax: 20000,
    districts: [],
    selectedDistrict: null,
    franchiseChoice: null,
    matchedPrograms: [],
  }),

  initFromLocalStorage: () => {
    if (typeof window === "undefined") return;
    const code = window.localStorage.getItem("builder_curation_industry_code") || "CS100010";
    const name = INDUSTRY_NAMES[code] || "카페";
    const icon = INDUSTRY_ICONS[code] || "☕";
    set({ industryCode: code, industryName: name, industryIcon: icon });
  },
}));
