"use client";

import { useState, useEffect, useMemo, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  BadgeDollarSign,
  ExternalLink,
  Loader2,
  AlertCircle,
  Landmark,
  Clock,
  ChevronRight,
  FileText,
  Lightbulb,
  MapPin,
  Store,
  Wallet,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { track } from "@/lib/analytics";
import { JourneyStepper } from "@/components/JourneyStepper";
import { AiInsightBanner } from "@/components/AiInsightBanner";
import { JourneyContextBadge } from "@/components/JourneyContextBadge";
import {
  useJourneyStore,
  INDUSTRY_NAMES,
  INDUSTRY_ICONS,
} from "@/lib/journey-store";

// ============================================================================
// Constants
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// ============================================================================
// Types
// ============================================================================

interface SupportProgram {
  program_id: string;
  program_name: string;
  category: string;
  support_target: string;
  max_amount_man: number;
  application_start_date: string;
  application_end_date: string;
  days_until_deadline: number;
  managing_org: string;
  detail_url: string;
  program_type: string;
}

// ============================================================================
// Helpers
// ============================================================================

/** Format max_amount_man: >= 10000 show as 억원, otherwise 만원 */
function formatAmount(manWon: number): string {
  if (manWon >= 10000) {
    const eok = manWon / 10000;
    return Number.isInteger(eok) ? `${eok}억원` : `${eok.toFixed(1)}억원`;
  }
  return `${manWon.toLocaleString()}만원`;
}

/** Format budget values for badges */
function formatBudge(value: number): string {
  if (value >= 10000) {
    const eok = value / 10000;
    return Number.isInteger(eok) ? `${eok}억` : `${eok.toFixed(1)}억`;
  }
  return `${value.toLocaleString()}만`;
}

const TYPE_BADGE_STYLES: Record<string, { bg: string; text: string }> = {
  "대출": { bg: "bg-blue-50 border-blue-200", text: "text-blue-700" },
  "보조금": { bg: "bg-emerald-50 border-emerald-200", text: "text-emerald-700" },
  "컨설팅": { bg: "bg-violet-50 border-violet-200", text: "text-violet-700" },
  "교육": { bg: "bg-amber-50 border-amber-200", text: "text-amber-700" },
  "기타": { bg: "bg-slate-50 border-slate-200", text: "text-slate-600" },
};

// ============================================================================
// Loading Skeleton
// ============================================================================

function LoadingSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      {/* Condition badges skeleton */}
      <div className="flex flex-wrap gap-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 w-28 bg-slate-200 rounded-full" />
        ))}
      </div>

      {/* Cards skeleton */}
      {[1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="bg-white rounded-xl border border-slate-200 p-5 space-y-3"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-slate-200" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-slate-200 rounded w-3/4" />
              <div className="h-3 bg-slate-100 rounded w-1/2" />
            </div>
            <div className="h-6 w-16 bg-slate-200 rounded-full" />
          </div>
          <div className="flex items-center gap-3">
            <div className="h-7 w-24 bg-slate-100 rounded-lg" />
            <div className="h-7 w-16 bg-slate-100 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Program Card
// ============================================================================

function ProgramCard({
  program,
  rank,
}: {
  program: SupportProgram;
  rank: number;
}) {
  const isUrgent = program.days_until_deadline <= 14;
  const typeBadge =
    TYPE_BADGE_STYLES[program.program_type] || TYPE_BADGE_STYLES["기타"];

  return (
    <div className="bg-white rounded-xl border border-slate-200 hover:border-blue-200 hover:shadow-md transition-all duration-200 p-5">
      <div className="flex items-start gap-4">
        {/* Rank number */}
        <div className="shrink-0 w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-sm font-bold shadow-sm">
          #{rank}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title row */}
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="text-base font-bold text-slate-800 leading-snug">
                {program.program_name}
              </h3>
              <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
                <Landmark className="w-3 h-3 shrink-0" />
                {program.managing_org}
              </p>
            </div>

            {/* D-day badge */}
            <span
              className={cn(
                "shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border",
                isUrgent
                  ? "bg-red-50 border-red-200 text-red-600"
                  : "bg-slate-50 border-slate-200 text-slate-600"
              )}
            >
              <Clock className="w-3 h-3" />
              D-{program.days_until_deadline}
            </span>
          </div>

          {/* Amount + type + link row */}
          <div className="flex flex-wrap items-center gap-2.5 mt-3">
            {/* Amount */}
            <span className="inline-flex items-center gap-1 text-blue-600 font-bold text-sm">
              <BadgeDollarSign className="w-4 h-4" />
              최대 {formatAmount(program.max_amount_man)}
            </span>

            {/* Program type badge */}
            <span
              className={cn(
                "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
                typeBadge.bg,
                typeBadge.text
              )}
            >
              {program.program_type}
            </span>

            {/* Spacer */}
            <div className="flex-1" />

            {/* Detail link */}
            <a
              href={program.detail_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline transition-colors"
            >
              상세보기
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Inner Page (uses useSearchParams)
// ============================================================================

function SupportPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const {
    industryCode: storeIndustryCode,
    selectedDistrict,
    budgetMin: storeBudgetMin,
    budgetMax: storeBudgetMax,
    setMatchedPrograms,
  } = useJourneyStore();

  // Resolve params: prefer URL query params, fall back to journey store
  const industryCode =
    searchParams?.get("industry_code") || storeIndustryCode || "CS100010";
  const districtParam = searchParams?.get("district") || searchParams?.get("district_code") || "";
  const budgetMin = parseInt(
    searchParams?.get("budget_min") || String(storeBudgetMin),
    10
  );
  const budgetMax = parseInt(
    searchParams?.get("budget_max") || String(storeBudgetMax),
    10
  );

  const industryName = INDUSTRY_NAMES[industryCode] || "카페";
  const industryIcon = INDUSTRY_ICONS[industryCode] || "";
  const districtName =
    districtParam ||
    selectedDistrict?.district_name ||
    selectedDistrict?.district_code ||
    "";

  const [programs, setPrograms] = useState<SupportProgram[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // AI Insight message (dynamic, based on loaded programs)
  const supportInsightMessage = useMemo(() => {
    if (programs.length === 0) return "";
    const urgent = programs.filter((p) => p.days_until_deadline <= 14);
    const maxAmount = Math.max(...programs.map((p) => p.max_amount_man));
    const totalMax = programs.reduce((s, p) => s + p.max_amount_man, 0);

    if (urgent.length > 0) {
      return `마감 임박 ${urgent.length}건 주의! ${urgent[0].program_name} D-${urgent[0].days_until_deadline}. 최대 지원금 ${maxAmount >= 10000 ? maxAmount / 10000 + "억" : maxAmount.toLocaleString() + "만"}원 프로그램이 포함되어 있습니다.`;
    }
    return `총 ${programs.length}건, 최대 ${maxAmount >= 10000 ? maxAmount / 10000 + "억" : maxAmount.toLocaleString() + "만"}원 규모 프로그램이 매칭되었습니다. 합산 최대 ${totalMax >= 10000 ? Math.round(totalMax / 10000) + "억" : totalMax.toLocaleString() + "만"}원 지원 가능합니다.`;
  }, [programs]);

  // Set journey step to 6 on mount
  useEffect(() => {
    useJourneyStore.getState().setStep(6);
    track("support_match");
  }, []);

  // Fetch matched programs
  useEffect(() => {
    const controller = new AbortController();

    async function fetchPrograms() {
      setLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        params.set("industry_code", industryCode);
        if (districtName) params.set("district", districtName);
        params.set("budget_min", String(budgetMin));
        params.set("budget_max", String(budgetMax));

        const res = await fetch(
          `${API_BASE}/support/matched?${params.toString()}`,
          { signal: controller.signal }
        );

        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          throw new Error(
            errData?.detail || `서버 오류가 발생했습니다 (${res.status})`
          );
        }

        const data: SupportProgram[] = await res.json();
        setPrograms(data);
        setMatchedPrograms(data);
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(
          e instanceof Error
            ? e.message
            : "지원 프로그램을 불러오는 중 오류가 발생했습니다."
        );
      } finally {
        setLoading(false);
      }
    }

    fetchPrograms();

    return () => controller.abort();
  }, [industryCode, districtName, budgetMin, budgetMax, setMatchedPrograms]);

  // Navigate to business-plan with query params
  const handleNext = () => {
    const params = new URLSearchParams();
    params.set("industry_code", industryCode);
    // Use zustand store district, else fall back to URL param
    const dc = selectedDistrict?.district_code || districtParam;
    const dn = selectedDistrict?.district_name || districtParam;
    if (dc) {
      params.set("district_code", dc);
      params.set("district_name", dn);
    }
    params.set("budget", String(budgetMax));
    router.push(`/business-plan?${params.toString()}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Stepper */}
      <JourneyStepper className="py-3 px-4 bg-white/80 backdrop-blur-sm border-b border-slate-100" />

      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-2.5 mb-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md">
              <BadgeDollarSign className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800">
                받을 수 있는 정부 지원금
              </h1>
              <p className="text-xs text-slate-500">
                조건에 맞는 지원 프로그램을 매칭했습니다
              </p>
            </div>
          </div>
        </div>

        {/* Journey context */}
        <JourneyContextBadge className="mb-4" />

        {/* Match condition badges */}
        <div className="flex flex-wrap gap-2 mb-6">
          {/* Industry badge */}
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-medium">
            <Store className="w-3.5 h-3.5" />
            {industryIcon && <span>{industryIcon}</span>}
            {industryName}
          </span>

          {/* District badge */}
          {districtName && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium">
              <MapPin className="w-3.5 h-3.5" />
              {districtName}
            </span>
          )}

          {/* Budget badge */}
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-50 border border-amber-200 text-amber-700 text-xs font-medium">
            <Wallet className="w-3.5 h-3.5" />
            예산 {formatBudge(budgetMin)}~{formatBudge(budgetMax)}원
          </span>
        </div>

        {/* Content area */}
        {loading ? (
          <LoadingSkeleton />
        ) : error ? (
          /* Error state */
          <div className="bg-white rounded-xl border border-red-200 p-8 text-center">
            <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
            <p className="text-sm font-semibold text-red-700 mb-1">
              데이터를 불러오지 못했습니다
            </p>
            <p className="text-xs text-red-500">{error}</p>
          </div>
        ) : programs.length === 0 ? (
          /* Empty state */
          <div className="bg-white rounded-xl border border-slate-200 p-10 text-center">
            <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-4">
              <BadgeDollarSign className="w-7 h-7 text-slate-400" />
            </div>
            <p className="text-base font-semibold text-slate-700 mb-1">
              조건에 맞는 지원 프로그램이 없습니다
            </p>
            <p className="text-sm text-slate-500">
              조건을 변경해보세요.
            </p>
          </div>
        ) : (
          /* Program list */
          <div className="space-y-3">
            <AiInsightBanner message={supportInsightMessage} variant="emerald" className="mb-3" />
            <p className="text-sm text-slate-500 font-medium">
              총{" "}
              <span className="text-blue-600 font-bold">
                {programs.length}건
              </span>
              의 지원 프로그램이 매칭되었습니다
            </p>
            {programs.map((program, idx) => (
              <ProgramCard
                key={program.program_id}
                program={program}
                rank={idx + 1}
              />
            ))}
          </div>
        )}

        {/* Tip banner */}
        <div className="mt-8 flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl p-4">
          <Lightbulb className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-800">TIP</p>
            <p className="text-xs text-amber-700 mt-0.5">
              사업계획서가 있으면 지원금 심사에 유리합니다.
            </p>
          </div>
        </div>

        {/* Next button */}
        <button
          onClick={handleNext}
          className="mt-6 w-full flex items-center justify-center gap-2 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold text-base hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg active:scale-[0.98]"
        >
          <FileText className="w-5 h-5" />
          사업계획서 만들기
          <ChevronRight className="w-5 h-5" />
        </button>

        {/* Data source footer */}
        <p className="mt-8 text-center text-[11px] text-slate-400">
          데이터 출처: 중소벤처기업부, 소상공인시장진흥공단, 서울시 (2026)
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// Page export (with Suspense for useSearchParams)
// ============================================================================

export default function SupportPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      }
    >
      <SupportPageInner />
    </Suspense>
  );
}
