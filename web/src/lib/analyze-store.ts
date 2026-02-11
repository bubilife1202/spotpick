import { create } from "zustand";

const INDUSTRY_NAMES: Record<string, string> = {
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

const INDUSTRY_ICONS: Record<string, string> = {
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

export type AnalyzeStep = 1 | 2 | 3;

export const ANALYZE_STEPS = [
  { num: 1 as const, label: "상담", short: "AI 코칭" },
  { num: 2 as const, label: "진단", short: "Go/No-Go" },
  { num: 3 as const, label: "실행", short: "체크리스트" },
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

export interface BenchmarkStore {
  name: string;
  category: string;
  address: string;
  placeUrl: string;
  industryCode: string;
  x?: number;
  y?: number;
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
  budget: number;
  experienceLevel: string;
  employeeCount: string;
  preferredDistricts: string[];
  benchmarkStore: BenchmarkStore | null;

  topDistricts: TopDistrict[];
  selectedDistrictCode: string;

  sectionData: SectionDataCache;
  sectionLoading: SectionLoadingState;

  setStep: (step: AnalyzeStep) => void;
  setIndustry: (code: string) => void;
  setBudget: (budget: number) => void;
  setExperienceLevel: (level: string) => void;
  setEmployeeCount: (count: string) => void;
  setPreferredDistricts: (districts: string[]) => void;
  setBenchmarkStore: (store: BenchmarkStore | null) => void;
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
  budget: 5000,
  experienceLevel: "",
  employeeCount: "",
  preferredDistricts: [],
  benchmarkStore: null,

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

  setBudget: (budget) => set({ budget }),

  setExperienceLevel: (level) => set({ experienceLevel: level }),

  setEmployeeCount: (count) => set({ employeeCount: count }),

  setPreferredDistricts: (districts) => set({ preferredDistricts: districts }),

  setBenchmarkStore: (benchmarkStore) => set({ benchmarkStore }),

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
      budget: 5000,
      experienceLevel: "",
      employeeCount: "",
      preferredDistricts: [],
      benchmarkStore: null,
      topDistricts: [],
      selectedDistrictCode: "",
      sectionData: {},
      sectionLoading: { ...DEFAULT_LOADING },
    }),

  getReportUrl: () => {
    const { industryCode, budget, experienceLevel, employeeCount } = get();
    const p = new URLSearchParams({
      industry_code: industryCode,
      budget: String(budget),
    });
    if (experienceLevel) p.set("experience_level", experienceLevel);
    if (employeeCount) p.set("employee_count", employeeCount);
    return `/analyze/report?${p.toString()}`;
  },

  getActionUrl: () => {
    const { industryCode, selectedDistrictCode, budget } = get();
    const p = new URLSearchParams({
      industry_code: industryCode,
      district_code: selectedDistrictCode,
      budget: String(budget),
    });
    return `/analyze/action?${p.toString()}`;
  },
}));
