"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { cn, formatMoney } from "@/lib/utils";
import { useAnalyzeStore } from "@/lib/analyze-store";
import { AnalyzeStepper } from "@/components/AnalyzeStepper";
import {
  MapPin,
  Loader2,
  ExternalLink,
  RefreshCw,
  ChevronLeft,
  Check,
  Briefcase,
  DollarSign,
  User,
  Building2,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// ── Checklist Data ──────────────────────────────────────────────

interface ChecklistItem {
  id: string;
  step: number;
  title: string;
  description: string;
  link: { label: string; url: string } | null;
  estimate: string;
  category: string;
}

const CHECKLIST_ITEMS: ChecklistItem[] = [
  {
    id: "market-research",
    step: 1,
    title: "상권 현장 답사",
    description:
      "AI 분석 결과를 확인했으니, 직접 현장을 방문하세요. 평일/주말, 점심/저녁 시간대별로 최소 3회 방문을 권장합니다.",
    link: null,
    estimate: "1-2주",
    category: "조사",
  },
  {
    id: "business-registration",
    step: 2,
    title: "사업자등록 신청",
    description:
      "관할 세무서 또는 홈택스에서 사업자등록을 신청하세요. 업종코드와 사업장 주소가 필요합니다.",
    link: { label: "홈택스 바로가기", url: "https://www.hometax.go.kr" },
    estimate: "1-3일",
    category: "행정",
  },
  {
    id: "hygiene-education",
    step: 3,
    title: "위생교육 수료",
    description:
      "식품위생법에 따라 영업 전 위생교육을 반드시 이수해야 합니다. 한국식품산업협회에서 온라인 수강 가능합니다.",
    link: { label: "한국식품산업협회", url: "https://www.kfia.or.kr" },
    estimate: "1일 (온라인)",
    category: "행정",
  },
  {
    id: "business-permit",
    step: 4,
    title: "영업신고증 발급",
    description:
      "관할 구청 위생과에서 영업신고를 하세요. 사업자등록증, 위생교육수료증, 임대차계약서가 필요합니다.",
    link: { label: "정부24", url: "https://www.gov.kr" },
    estimate: "3-7일",
    category: "행정",
  },
  {
    id: "funding",
    step: 5,
    title: "자금 확보 & 지원금 신청",
    description:
      "소상공인시장진흥공단에서 정책자금 대출 및 창업 지원금을 확인하세요. 사업계획서 제출이 필요할 수 있습니다.",
    link: { label: "소상공인시장진흥공단", url: "https://www.semas.or.kr" },
    estimate: "2-4주",
    category: "자금",
  },
  {
    id: "location",
    step: 6,
    title: "매물 계약",
    description:
      "AI가 추천한 상권 내 매물을 탐색하세요. 권리금, 보증금, 월세를 꼼꼼히 비교하고 반드시 등기부등본을 확인하세요.",
    link: { label: "네이버 부동산", url: "https://land.naver.com" },
    estimate: "2-8주",
    category: "매장",
  },
  {
    id: "interior",
    step: 7,
    title: "인테리어 & 설비",
    description:
      "최소 3곳 이상 견적을 받으세요. 주방 설비는 업종 특성에 맞게 배치하고, 소방 설비 기준도 확인하세요.",
    link: null,
    estimate: "4-8주",
    category: "매장",
  },
  {
    id: "menu-pricing",
    step: 8,
    title: "메뉴 & 가격 설정",
    description:
      "원가율 30-35%를 기준으로 메뉴 가격을 설정하세요. 주변 경쟁 매장의 가격대도 참고하세요.",
    link: null,
    estimate: "1-2주",
    category: "운영",
  },
  {
    id: "staff-hiring",
    step: 9,
    title: "직원 채용 & 교육",
    description:
      "오픈 2주 전까지 직원을 확보하고 교육을 완료하세요. 4대보험 가입도 잊지 마세요.",
    link: { label: "사람인", url: "https://www.saramin.co.kr" },
    estimate: "2-3주",
    category: "운영",
  },
  {
    id: "opening",
    step: 10,
    title: "오픈 준비 & 프리오픈",
    description:
      "정식 오픈 전 지인 초대 프리오픈으로 운영 동선을 점검하세요. 배달앱 등록, SNS 개설도 이 시기에 하세요.",
    link: null,
    estimate: "1주",
    category: "운영",
  },
];

const CATEGORIES = [
  { key: "조사", emoji: "📋", label: "조사" },
  { key: "행정", emoji: "🏛️", label: "행정" },
  { key: "자금", emoji: "💰", label: "자금" },
  { key: "매장", emoji: "🏪", label: "매장" },
  { key: "운영", emoji: "🔧", label: "운영" },
];

const USEFUL_LINKS = [
  { label: "소진공 창업교육", url: "https://edu.semas.or.kr", icon: "🎓" },
  {
    label: "서울신용보증재단",
    url: "https://www.seoulshinbo.co.kr",
    icon: "🏦",
  },
  { label: "네이버 부동산", url: "https://land.naver.com", icon: "🏠" },
  { label: "홈택스", url: "https://www.hometax.go.kr", icon: "📋" },
  { label: "정부24", url: "https://www.gov.kr", icon: "🏛️" },
  { label: "소상공인마당", url: "https://www.sbiz.or.kr", icon: "📊" },
];

const EXPERIENCE_LABELS: Record<string, string> = {
  beginner: "🌱 처음이에요",
  experienced: "💼 경험 있어요",
  expert: "🏆 전문가예요",
};

const EMPLOYEE_LABELS: Record<string, string> = {
  solo: "👤 1인 운영",
  "1-2": "👥 1-2명 고용",
  "3+": "👥👥 3명 이상",
};

// ── Cost breakdown helpers ──────────────────────────────────────

interface CostRow {
  label: string;
  ratio: number;
  amount: number;
}

function computeCosts(budgetManwon: number): CostRow[] {
  const budgetWon = budgetManwon * 10000;
  return [
    { label: "보증금/권리금", ratio: 0.25, amount: Math.round(budgetWon * 0.25) },
    { label: "인테리어", ratio: 0.35, amount: Math.round(budgetWon * 0.35) },
    { label: "설비/장비", ratio: 0.15, amount: Math.round(budgetWon * 0.15) },
    { label: "초기 재료비", ratio: 0.05, amount: Math.round(budgetWon * 0.05) },
    {
      label: "운영자금(3개월)",
      ratio: 0.15,
      amount: Math.round(budgetWon * 0.15),
    },
    { label: "기타(예비비)", ratio: 0.05, amount: Math.round(budgetWon * 0.05) },
  ];
}

function buildChecklistItems(params: {
  experienceLevel: string;
  employeeCount: string;
}): ChecklistItem[] {
  const items: ChecklistItem[] = CHECKLIST_ITEMS.map((i) => ({ ...i }));

  if (params.experienceLevel === "beginner") {
    const education: ChecklistItem = {
      id: "education",
      step: 0,
      title: "기초 교육 & 벤치마킹",
      description:
        "초보라면 오픈 전에 기본 교육을 먼저 끝내세요. 성공 매장 5곳 + 실패 매장 5곳을 직접 방문해서 메뉴·동선·피크 타임을 기록하면 시행착오를 크게 줄일 수 있습니다.",
      link: { label: "소진공 창업교육", url: "https://edu.semas.or.kr" },
      estimate: "2-3일",
      category: "조사",
    };

    // Insert after market-research (step 1)
    const idx = items.findIndex((i) => i.id === "market-research");
    items.splice(Math.max(0, idx + 1), 0, education);
  }

  if (params.employeeCount === "solo") {
    const idx = items.findIndex((i) => i.id === "staff-hiring");
    if (idx >= 0) {
      items[idx] = {
        ...items[idx],
        title: "1인 운영 동선 & 자동화",
        description:
          "1인 운영이면 채용보다 동선·메뉴·자동화를 먼저 설계해야 합니다. 키오스크/POS, 배치프렙, 메뉴 단순화(핵심 10개 이하)로 피크 타임 병목을 없애세요.",
        link: null,
        estimate: "1-2주",
      };
    }
  } else if (params.employeeCount && params.employeeCount !== "solo") {
    const idx = items.findIndex((i) => i.id === "staff-hiring");
    if (idx >= 0) {
      const labor: ChecklistItem = {
        id: "labor-contracts",
        step: 0,
        title: "근로계약서 & 4대보험",
        description:
          "오픈 전 근로계약서를 준비하고, 급여·근무표·4대보험/원천징수까지 체크하세요. 인건비는 매출의 25~30% 안쪽에서 설계하는 게 안전합니다.",
        link: { label: "고용노동부", url: "https://www.moel.go.kr" },
        estimate: "1-3일",
        category: "운영",
      };
      items.splice(idx + 1, 0, labor);
    }
  }

  return items.map((item, i) => ({ ...item, step: i + 1 }));
}

// ── Component ───────────────────────────────────────────────────

function ActionContent() {
  const searchParams = useSearchParams();
  const store = useAnalyzeStore();

  const industryCode =
    searchParams?.get("industry_code") || store.industryCode;
  const districtCode =
    searchParams?.get("district_code") || store.selectedDistrictCode;
  const budget =
    Number(searchParams?.get("budget")) ||
    Number(searchParams?.get("budget_max")) ||
    store.budget;

  const experienceLevel =
    searchParams?.get("experience_level") || store.experienceLevel || "";
  const employeeCount =
    searchParams?.get("employee_count") || store.employeeCount || "";

  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [checklistLoaded, setChecklistLoaded] = useState(false);

  useEffect(() => {
    useAnalyzeStore.getState().setStep(3);
  }, []);

  useEffect(() => {
    const { setExperienceLevel, setEmployeeCount } = useAnalyzeStore.getState();
    if (experienceLevel) setExperienceLevel(experienceLevel);
    if (employeeCount) setEmployeeCount(employeeCount);
  }, [experienceLevel, employeeCount]);

  const storageKey = `spotpick:checklist:${industryCode}:${districtCode || "none"}`;

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) {
        setChecked(new Set());
        setChecklistLoaded(true);
        return;
      }
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        const ids = parsed.filter((x) => typeof x === "string");
        setChecked(new Set(ids));
      } else {
        setChecked(new Set());
      }
    } catch {
      setChecked(new Set());
    } finally {
      setChecklistLoaded(true);
    }
  }, [storageKey]);

  useEffect(() => {
    if (!checklistLoaded) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify(Array.from(checked)));
    } catch {
      // ignore storage failures (private mode, quota, etc.)
    }
  }, [checked, storageKey, checklistLoaded]);

  const toggle = (id: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedDistrict = store.topDistricts.find(
    (d) => d.district_code === districtCode,
  );
  const districtName = selectedDistrict?.district_name || "선택된 상권";
  const industryName = store.industryName || "업종";
  const experienceLabel = EXPERIENCE_LABELS[experienceLevel] || experienceLevel || "미입력";
  const employeeLabel = EMPLOYEE_LABELS[employeeCount] || employeeCount || "미입력";
  const profileLabel = [experienceLabel, employeeLabel].filter(Boolean).join(" · ");

  const checklistItems = buildChecklistItems({ experienceLevel, employeeCount });

  const checkedCount = checklistItems.filter((i) => checked.has(i.id)).length;
  const totalCount = checklistItems.length;
  const progressPct = totalCount > 0 ? Math.round((checkedCount / totalCount) * 100) : 0;

  const costs = computeCosts(budget);
  const maxRatio = Math.max(...costs.map((c) => c.ratio));

  // Build query string for navigation links
  const queryString = new URLSearchParams({
    industry_code: industryCode,
    ...(districtCode ? { district_code: districtCode } : {}),
    budget: String(budget),
  }).toString();

  // Suppress unused-var lint for API_BASE (kept for future use)
  void API_BASE;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600">
              <MapPin className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-bold text-slate-900">SpotPick</span>
          </Link>
          <Link
            href="/analyze"
            className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md"
          >
            시작하기
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-20 pt-8 sm:px-6">
        {/* Stepper */}
        <AnalyzeStepper currentStep={3} className="mb-8" />

        {/* Title */}
        <div className="mb-6 text-center animate-slide-up">
          <h1 className="text-2xl font-extrabold text-slate-900 sm:text-3xl">
            ✅ 창업 실행 체크리스트
          </h1>
          <p className="mt-1.5 text-sm text-slate-500">
            {districtName} {industryName} 창업을 위한 단계별 가이드
          </p>
        </div>

        {/* Context Card */}
        <div className="mb-8 animate-slide-up rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                <Briefcase className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  업종
                </p>
                <p className="truncate text-xs font-bold text-slate-800">
                  {store.industryIcon} {industryName}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                <Building2 className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  상권
                </p>
                <p className="truncate text-xs font-bold text-slate-800">
                  {districtName}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                <DollarSign className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  예산
                </p>
                <p className="truncate text-xs font-bold text-slate-800">
                  {formatMoney(budget * 10000)}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
                <User className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  프로필
                </p>
                <p className="truncate text-xs font-bold text-slate-800">{profileLabel}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-6 animate-slide-up">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-bold text-slate-700">
              {checkedCount}/{totalCount} 완료
            </span>
            <span className="text-xs font-semibold text-blue-600">
              {progressPct}%
            </span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500 ease-out"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {/* Checklist by Category */}
        <div className="space-y-8">
          {CATEGORIES.map((cat) => {
            const items = checklistItems.filter(
              (item) => item.category === cat.key,
            );
            if (items.length === 0) return null;

            return (
              <section key={cat.key}>
                {/* Category Header */}
                <div className="mb-3 flex items-center gap-2">
                  <span className="text-base">{cat.emoji}</span>
                  <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400">
                    {cat.label}
                  </h2>
                  <div className="h-px flex-1 bg-slate-100" />
                </div>

                {/* Items */}
                <div className="space-y-3">
                  {items.map((item) => {
                    const isDone = checked.has(item.id);
                    return (
                      <div
                        key={item.id}
                        className={cn(
                          "group relative rounded-xl border p-4 transition-all duration-200",
                          isDone
                            ? "border-emerald-200 bg-emerald-50/30"
                            : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm",
                        )}
                      >
                        <div className="flex items-start gap-3">
                          {/* Checkbox */}
                          <button
                            type="button"
                            onClick={() => toggle(item.id)}
                            className={cn(
                              "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-all duration-200",
                              isDone
                                ? "border-emerald-500 bg-emerald-500 text-white"
                                : "border-slate-300 bg-white hover:border-blue-400",
                            )}
                            aria-label={`${item.title} ${isDone ? "완료 취소" : "완료 처리"}`}
                          >
                            {isDone && <Check className="h-3 w-3" strokeWidth={3} />}
                          </button>

                          {/* Content */}
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-2">
                              <h3
                                className={cn(
                                  "text-sm font-bold transition-all duration-200",
                                  isDone
                                    ? "text-emerald-700 line-through decoration-emerald-400"
                                    : "text-slate-900",
                                )}
                              >
                                <span className="mr-1.5 text-xs font-semibold text-slate-400">
                                  Step {item.step}.
                                </span>
                                {item.title}
                              </h3>
                              <span
                                className={cn(
                                  "shrink-0 whitespace-nowrap text-xs font-medium",
                                  isDone
                                    ? "text-emerald-500"
                                    : "text-slate-400",
                                )}
                              >
                                {isDone ? "완료! ✓" : item.estimate}
                              </span>
                            </div>

                            <p
                              className={cn(
                                "mt-1 text-xs leading-relaxed",
                                isDone ? "text-slate-400" : "text-slate-600",
                              )}
                            >
                              {item.description}
                            </p>

                            {item.link && (
                              <a
                                href={item.link.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-2 inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-600 transition hover:bg-blue-100"
                              >
                                {item.link.label}
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>

        {/* Cost Summary Card */}
        <div className="mt-12 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-bold text-slate-900">
            💵 예상 비용 배분{" "}
            <span className="font-medium text-slate-400">
              (예산 {formatMoney(budget * 10000)} 기준)
            </span>
          </h2>

          <div className="space-y-3">
            {costs.map((row) => (
              <div key={row.label} className="flex items-center gap-3">
                <span className="w-28 shrink-0 text-xs font-medium text-slate-600 sm:w-32">
                  {row.label}
                </span>
                <div className="flex flex-1 items-center gap-2">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-blue-400 to-indigo-400 transition-all duration-500"
                      style={{
                        width: `${(row.ratio / maxRatio) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right text-[11px] font-semibold text-slate-500">
                    {Math.round(row.ratio * 100)}%
                  </span>
                </div>
                <span className="w-20 shrink-0 text-right text-xs font-bold text-slate-800 sm:w-24">
                  {formatMoney(row.amount)}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3">
            <span className="text-xs font-bold text-slate-700">합계</span>
            <span className="text-sm font-extrabold text-slate-900">
              {formatMoney(budget * 10000)}
            </span>
          </div>
        </div>

        {/* Useful Links */}
        <div className="mt-10">
          <h2 className="mb-4 text-sm font-bold text-slate-900">
            🔗 유용한 링크 모음
          </h2>
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
            {USEFUL_LINKS.map((link) => (
              <a
                key={link.url}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2.5 rounded-xl border border-slate-200 bg-white p-3 transition hover:border-blue-200 hover:bg-blue-50/50 hover:shadow-sm"
              >
                <span className="text-lg">{link.icon}</span>
                <span className="text-xs font-semibold text-slate-700">
                  {link.label}
                </span>
              </a>
            ))}
          </div>
        </div>

        {/* Bottom CTAs */}
        <div className="mt-12 flex flex-col gap-3 sm:flex-row">
          <Link
            href={`/analyze/report?${queryString}`}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          >
            <ChevronLeft className="h-4 w-4" />
            진단 결과 다시 보기
          </Link>
          <Link
            href="/analyze"
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            처음부터 다시 분석하기
          </Link>
        </div>
      </main>
    </div>
  );
}

export default function AnalyzeActionPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <ActionContent />
    </Suspense>
  );
}
