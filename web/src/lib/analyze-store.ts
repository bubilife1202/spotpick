import { create } from "zustand";
import { INDUSTRY_NAMES, INDUSTRY_ICONS } from "./journey-store";

export type AnalyzeStep = 1 | 2 | 3;

export const ANALYZE_STEPS = [
  { num: 1 as const, label: "입력", short: "업종/예산" },
  { num: 2 as const, label: "AI 리포트", short: "종합 분석" },
  { num: 3 as const, label: "액션 플랜", short: "사업계획서" },
] as const;

export interface TopDistrict {
  district_code: string;
  district_name: string;
  district_type: string;
  success_probability: number;
  estimated_rent: number;
  monthly_sales: number;
  store_count: number;
  survival_rate: number;
  scorecard_total: number;
  key_factors: string[];
  coordinates?: { lat: number; lng: number };
}

// Section-level loading states
export interface SectionLoadingState {
  top3: boolean;
  scorecard: boolean;
  simulation: boolean;
  competition: boolean;
  location: boolean;
  customer: boolean;
  rent: boolean;
  franchise: boolean;
  risk: boolean;
  support: boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type SectionDataCache = Record<string, Record<string, any>>;

interface AnalyzeState {
  step: AnalyzeStep;
  industryCode: string;
  industryName: string;
  industryIcon: string;
  budgetMin: number;
  budgetMax: number;
  preferredDistricts: string[];

  topDistricts: TopDistrict[];
  selectedDistrictCode: string;

  sectionData: SectionDataCache;
  sectionLoading: SectionLoadingState;

  setStep: (step: AnalyzeStep) => void;
  setIndustry: (code: string) => void;
  setBudget: (min: number, max: number) => void;
  setPreferredDistricts: (districts: string[]) => void;
  setTopDistricts: (districts: TopDistrict[]) => void;
  setSelectedDistrict: (code: string) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setSectionData: (districtCode: string, section: string, data: any) => void;
  getSectionData: (districtCode: string, section: string) => unknown;
  setSectionLoading: (section: keyof SectionLoadingState, loading: boolean) => void;
  reset: () => void;
  getReportUrl: () => string;
  getActionUrl: () => string;
}

const DEFAULT_LOADING: SectionLoadingState = {
  top3: false,
  scorecard: false,
  simulation: false,
  competition: false,
  location: false,
  customer: false,
  rent: false,
  franchise: false,
  risk: false,
  support: false,
};

export const useAnalyzeStore = create<AnalyzeState>((set, get) => ({
  step: 1,
  industryCode: "CS100010",
  industryName: "카페",
  industryIcon: "☕",
  budgetMin: 3000,
  budgetMax: 10000,
  preferredDistricts: [],

  topDistricts: [],
  selectedDistrictCode: "",

  sectionData: {},
  sectionLoading: { ...DEFAULT_LOADING },

  setStep: (step) => set({ step }),

  setIndustry: (code) => {
    const name = INDUSTRY_NAMES[code] || "카페";
    const icon = INDUSTRY_ICONS[code] || "☕";
    set({ industryCode: code, industryName: name, industryIcon: icon });
  },

  setBudget: (min, max) => set({ budgetMin: min, budgetMax: max }),

  setPreferredDistricts: (districts) => set({ preferredDistricts: districts }),

  setTopDistricts: (districts) => set({ topDistricts: districts }),

  setSelectedDistrict: (code) => set({ selectedDistrictCode: code }),

  setSectionData: (districtCode, section, data) => {
    const prev = get().sectionData;
    set({
      sectionData: {
        ...prev,
        [districtCode]: {
          ...prev[districtCode],
          [section]: data,
        },
      },
    });
  },

  getSectionData: (districtCode, section) => {
    return get().sectionData[districtCode]?.[section];
  },

  setSectionLoading: (section, loading) => {
    set({ sectionLoading: { ...get().sectionLoading, [section]: loading } });
  },

  reset: () =>
    set({
      step: 1,
      industryCode: "CS100010",
      industryName: "카페",
      industryIcon: "☕",
      budgetMin: 3000,
      budgetMax: 10000,
      preferredDistricts: [],
      topDistricts: [],
      selectedDistrictCode: "",
      sectionData: {},
      sectionLoading: { ...DEFAULT_LOADING },
    }),

  getReportUrl: () => {
    const { industryCode, budgetMin, budgetMax } = get();
    const p = new URLSearchParams({
      industry_code: industryCode,
      budget_min: String(budgetMin),
      budget_max: String(budgetMax),
    });
    return `/analyze/report?${p.toString()}`;
  },

  getActionUrl: () => {
    const { industryCode, selectedDistrictCode, budgetMin, budgetMax } = get();
    const p = new URLSearchParams({
      industry_code: industryCode,
      district_code: selectedDistrictCode,
      budget_min: String(budgetMin),
      budget_max: String(budgetMax),
    });
    return `/analyze/action?${p.toString()}`;
  },
}));
