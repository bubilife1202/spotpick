"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  TrendingUp,
  DollarSign,
  Clock,
  Shield,
  Wallet,
  Store,
  ArrowLeft,
  RefreshCw,
  FileText,
  RotateCcw,
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
import type { ScorecardCategory, ScorecardResult } from "@/types/chat";

// ============================================================================
// Constants
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// ============================================================================
// Types
// ============================================================================

interface ReportApiResponse {
  district_code: string;
  district_name: string;
  total_score: number;
  rank: number;
  percentile: number;
  categories: ScorecardCategory[];
}

interface SimulationApiResponse {
  district_name: string;
  district_type: string;
  revenue: {
    monthly_sales_per_store: number;
    pessimistic: number;
    optimistic: number;
  };
  startup_cost: {
    total_min: number;
    total_max: number;
  };
  break_even: {
    break_even_months_min: number;
    break_even_months_max: number;
    monthly_net_profit: number;
    net_profit_margin: number;
  };
  competition: {
    store_count: number;
    survival_rate: number;
  };
}

// ============================================================================
// Helpers
// ============================================================================

function formatKRWCompact(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "-";
  if (value >= 100_000_000) {
    const eok = value / 100_000_000;
    return `${eok >= 100 ? eok.toFixed(0) : eok.toFixed(1)}억`;
  }
  if (value >= 10_000) {
    return `${Math.round(value / 10_000).toLocaleString()}만원`;
  }
  return `${Math.round(value).toLocaleString()}원`;
}

function formatBudgetMan(manWon: number): string {
  if (manWon >= 10000) {
    const eok = manWon / 10000;
    return Number.isInteger(eok) ? `${eok}억` : `${eok.toFixed(1)}억`;
  }
  return `${manWon.toLocaleString()}만`;
}

function generateSummaryInsight(
  districtName: string,
  industryName: string,
  scorecard: { total: number; categories: Array<{ name: string; score: number; weight: number }> },
  simulation: { monthly_sales: number; survival_rate: number; store_count: number }
): string {
  const strengths: string[] = [];
  const weaknesses: string[] = [];

  for (const cat of scorecard.categories) {
    const pct = cat.score / cat.weight;
    if (pct >= 0.7) strengths.push(cat.name);
    else if (pct < 0.4) weaknesses.push(cat.name);
  }

  let msg = `${districtName} ${industryName}은 종합 ${scorecard.total}점으로 `;
  if (scorecard.total >= 75) msg += "적극 추천합니다. ";
  else if (scorecard.total >= 50) msg += "조건부 추천합니다. ";
  else msg += "신중한 검토가 필요합니다. ";

  if (strengths.length > 0) msg += `강점: ${strengths.join(", ")}. `;
  if (weaknesses.length > 0) msg += `보완 필요: ${weaknesses.join(", ")}. `;

  if (simulation.survival_rate < 0.6) {
    msg += "2년 생존율이 낮으므로 리스크 관리 전략을 수립하세요.";
  } else if (simulation.store_count > 80) {
    msg += "경쟁 점포가 많으므로 차별화 전략이 중요합니다.";
  }

  return msg;
}

// ============================================================================
// Skeleton Component
// ============================================================================

function MetricSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-5 animate-pulse">
      <div className="h-3 w-16 bg-slate-200 rounded mb-3" />
      <div className="h-8 w-24 bg-slate-200 rounded mb-2" />
      <div className="h-3 w-20 bg-slate-200 rounded" />
    </div>
  );
}

// ============================================================================
// Metric Card Component
// ============================================================================

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  icon: React.ReactNode;
  accentClass: string;
  iconBgClass: string;
}

function MetricCard({ label, value, sub, icon, accentClass, iconBgClass }: MetricCardProps) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-5 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className={cn("w-8 h-8 rounded-lg flex items-center justify-center", iconBgClass)}>
          {icon}
        </span>
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
          {label}
        </span>
      </div>
      <p className={cn("text-2xl font-extrabold tracking-tight", accentClass)}>
        {value}
      </p>
      {sub && (
        <p className="text-xs text-slate-500">{sub}</p>
      )}
    </div>
  );
}

// ============================================================================
// Main Summary Content
// ============================================================================

function SummaryContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Read from zustand store
  const storeDistrict = useJourneyStore((s) => s.selectedDistrict);
  const storeIndustryCode = useJourneyStore((s) => s.industryCode);
  const matchedPrograms = useJourneyStore((s) => s.matchedPrograms);
  const budgetMin = useJourneyStore((s) => s.budgetMin);
  const budgetMax = useJourneyStore((s) => s.budgetMax);

  // Resolve params: store first, then URL fallback
  const districtCode =
    storeDistrict?.district_code ||
    searchParams?.get("district_code") ||
    "";
  const industryCode =
    (storeDistrict ? storeIndustryCode : null) ||
    searchParams?.get("industry_code") ||
    "CS100010";

  const industryName = INDUSTRY_NAMES[industryCode] || "카페";
  const industryIcon = INDUSTRY_ICONS[industryCode] || "☕";

  // API data
  const [scorecard, setScorecard] = useState<ScorecardResult | null>(null);
  const [simulation, setSimulation] = useState<SimulationApiResponse | null>(null);
  const [districtName, setDistrictName] = useState<string>(
    storeDistrict?.district_name || ""
  );

  // Loading & error
  const [loadingReport, setLoadingReport] = useState(true);
  const [loadingSimulation, setLoadingSimulation] = useState(true);
  const [errorReport, setErrorReport] = useState<string | null>(null);
  const [errorSimulation, setErrorSimulation] = useState<string | null>(null);

  // Track page view
  useEffect(() => {
    if (districtCode) {
      track("page_view", { page: "summary", district_code: districtCode });
    }
  }, [districtCode]);

  // Fetch report (scorecard) data
  useEffect(() => {
    if (!districtCode) return;

    setLoadingReport(true);
    setErrorReport(null);
    setScorecard(null);

    fetch(`${API_BASE}/scorecard/${industryCode}/${districtCode}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: ReportApiResponse = await res.json();
        setScorecard(data);
        if (data.district_name) {
          setDistrictName((prev) => prev || data.district_name);
        }
      })
      .catch((e: Error) => {
        setErrorReport(e.message);
      })
      .finally(() => setLoadingReport(false));
  }, [districtCode, industryCode]);

  // Fetch simulation data
  useEffect(() => {
    if (!districtCode) return;

    setLoadingSimulation(true);
    setErrorSimulation(null);
    setSimulation(null);

    fetch(
      `${API_BASE}/simulation/simulate/${districtCode}?industry_code=${industryCode}&area_pyeong=15`
    )
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: SimulationApiResponse = await res.json();
        setSimulation(data);
        if (data.district_name) {
          setDistrictName((prev) => prev || data.district_name);
        }
      })
      .catch((e: Error) => {
        setErrorSimulation(e.message);
      })
      .finally(() => setLoadingSimulation(false));
  }, [districtCode, industryCode]);

  // Derived values
  const isLoading = loadingReport || loadingSimulation;
  const hasError = errorReport || errorSimulation;

  const totalScore = scorecard ? Math.round(scorecard.total_score) : null;
  const monthlySales = simulation?.revenue?.monthly_sales_per_store ?? null;
  const bepMin = simulation?.break_even?.break_even_months_min ?? null;
  const bepMax = simulation?.break_even?.break_even_months_max ?? null;
  const survivalRate = simulation?.competition?.survival_rate ?? null;
  const storeCount = simulation?.competition?.store_count ?? null;
  const startupMin = simulation?.startup_cost?.total_min ?? null;
  const startupMax = simulation?.startup_cost?.total_max ?? null;

  // Verdict
  const getVerdict = (score: number) => {
    if (score >= 75)
      return {
        label: "추천",
        color: "text-emerald-600",
        bg: "bg-emerald-50 border-emerald-200",
        badgeBg: "bg-gradient-to-r from-emerald-500 to-emerald-600",
        icon: <CheckCircle size={20} className="text-white" />,
      };
    if (score >= 50)
      return {
        label: "보통",
        color: "text-amber-600",
        bg: "bg-amber-50 border-amber-200",
        badgeBg: "bg-gradient-to-r from-amber-500 to-amber-600",
        icon: <AlertTriangle size={20} className="text-white" />,
      };
    return {
      label: "주의",
      color: "text-rose-600",
      bg: "bg-rose-50 border-rose-200",
      badgeBg: "bg-gradient-to-r from-rose-500 to-rose-600",
      icon: <XCircle size={20} className="text-white" />,
    };
  };

  // AI insight message
  const aiInsight =
    scorecard && simulation
      ? generateSummaryInsight(
          districtName || districtCode,
          industryName,
          {
            total: Math.round(scorecard.total_score),
            categories: scorecard.categories.map((c) => ({
              name: c.name,
              score: c.score,
              weight: c.weight,
            })),
          },
          {
            monthly_sales: simulation.revenue.monthly_sales_per_store,
            survival_rate: simulation.competition.survival_rate,
            store_count: simulation.competition.store_count,
          }
        )
      : "";

  // No district selected
  if (!districtCode) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-blue-50/30 flex items-center justify-center">
        <div className="text-center space-y-4 px-4">
          <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto">
            <Store className="w-7 h-7 text-slate-400" />
          </div>
          <h2 className="text-lg font-bold text-slate-800">
            분석할 상권을 선택하세요
          </h2>
          <p className="text-sm text-slate-500">
            먼저 상권을 탐색하고 선택한 후 요약 보고서를 확인할 수 있습니다.
          </p>
          <button
            onClick={() => router.push("/results")}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors text-sm font-semibold"
          >
            상권 탐색하러 가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-blue-50/30">
      {/* Header */}
      <header className="bg-white/95 backdrop-blur-sm shadow-sm sticky top-0 z-40 border-b border-gray-100/50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft size={18} />
            <span className="hidden sm:inline">뒤로가기</span>
          </button>

          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm">
              <span className="text-sm">{industryIcon}</span>
            </div>
            <span className="text-sm font-semibold text-slate-800 hidden sm:inline">
              SpotPick
            </span>
          </div>
        </div>
      </header>

      {/* Journey Stepper */}
      <JourneyStepper className="py-3 px-4 bg-white/80 backdrop-blur-sm border-b border-slate-100" />

      {/* Title Section */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-6 pb-2 sm:pt-8 sm:pb-4">
        <div className="flex items-center gap-3 mb-3">
          <span className="text-3xl">{industryIcon}</span>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
              SpotPick 창업 분석 요약
            </h1>
            <p className="text-sm text-slate-500">
              {districtName || districtCode} &middot; {industryName}
            </p>
          </div>
        </div>

        {/* Journey Context Badge */}
        <JourneyContextBadge className="mb-4" />

        {/* AI Insight Banner */}
        {aiInsight && (
          <AiInsightBanner
            message={aiInsight}
            variant={
              totalScore !== null
                ? totalScore >= 75
                  ? "emerald"
                  : totalScore >= 50
                  ? "blue"
                  : "amber"
                : "blue"
            }
            className="mb-4"
          />
        )}
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 pb-12">
        {/* Error banner */}
        {hasError && !isLoading && (
          <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50/80 px-4 py-3 mb-6">
            <AlertTriangle size={18} className="text-rose-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-rose-800">
                데이터 로딩 중 일부 오류가 발생했습니다
              </p>
              {errorReport && (
                <p className="text-xs text-rose-600 mt-0.5">
                  보고서: {errorReport}
                </p>
              )}
              {errorSimulation && (
                <p className="text-xs text-rose-600 mt-0.5">
                  시뮬레이션: {errorSimulation}
                </p>
              )}
            </div>
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-100 hover:bg-rose-200 text-rose-700 rounded-lg text-xs font-medium transition-colors shrink-0"
            >
              <RefreshCw size={12} />
              재시도
            </button>
          </div>
        )}

        {/* 6-card metric grid (3x2) */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4 mb-8">
          {/* 1. Verdict */}
          {isLoading ? (
            <MetricSkeleton />
          ) : totalScore !== null ? (
            (() => {
              const verdict = getVerdict(totalScore);
              return (
                <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-5 flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "w-8 h-8 rounded-lg flex items-center justify-center",
                        verdict.badgeBg
                      )}
                    >
                      {verdict.icon}
                    </span>
                    <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                      종합판정
                    </span>
                  </div>
                  <p className={cn("text-2xl font-extrabold tracking-tight", verdict.color)}>
                    {verdict.label}
                  </p>
                  <p className="text-xs text-slate-500">
                    {totalScore}점 / 100점
                  </p>
                </div>
              );
            })()
          ) : (
            <MetricCard
              label="종합판정"
              value="-"
              icon={<TrendingUp size={16} className="text-slate-400" />}
              accentClass="text-slate-400"
              iconBgClass="bg-slate-100"
            />
          )}

          {/* 2. Monthly Sales */}
          {isLoading ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="예상매출"
              value={monthlySales !== null ? formatKRWCompact(monthlySales) : "-"}
              sub="월 예상 매출액"
              icon={<DollarSign size={16} className="text-blue-600" />}
              accentClass="text-blue-700"
              iconBgClass="bg-blue-50"
            />
          )}

          {/* 3. BEP */}
          {isLoading ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="손익분기"
              value={
                bepMin !== null && bepMax !== null
                  ? `${bepMin}~${bepMax}개월`
                  : "-"
              }
              sub="투자금 회수 기간"
              icon={<Clock size={16} className="text-purple-600" />}
              accentClass="text-purple-700"
              iconBgClass="bg-purple-50"
            />
          )}

          {/* 4. Support Programs */}
          {isLoading ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="지원금"
              value={`${matchedPrograms.length}건 매칭`}
              sub="정부/공공 지원사업"
              icon={<Wallet size={16} className="text-amber-600" />}
              accentClass="text-amber-700"
              iconBgClass="bg-amber-50"
            />
          )}

          {/* 5. Survival Rate */}
          {isLoading ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="생존율"
              value={
                survivalRate !== null
                  ? `${Math.round(survivalRate * 100)}%`
                  : "-"
              }
              sub="2년 생존율"
              icon={
                <Shield
                  size={16}
                  className={cn(
                    survivalRate !== null && survivalRate >= 0.6
                      ? "text-emerald-600"
                      : "text-rose-600"
                  )}
                />
              }
              accentClass={
                survivalRate !== null && survivalRate >= 0.6
                  ? "text-emerald-700"
                  : "text-rose-700"
              }
              iconBgClass={
                survivalRate !== null && survivalRate >= 0.6
                  ? "bg-emerald-50"
                  : "bg-rose-50"
              }
            />
          )}

          {/* 6. Initial Cost */}
          {isLoading ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="초기비용"
              value={
                startupMin !== null && startupMax !== null
                  ? `${formatKRWCompact(startupMin)}~${formatKRWCompact(startupMax)}`
                  : budgetMin > 0 || budgetMax > 0
                  ? `${formatBudgetMan(budgetMin)}~${formatBudgetMan(budgetMax)}`
                  : "-"
              }
              sub="예상 초기 투자비"
              icon={<Store size={16} className="text-indigo-600" />}
              accentClass="text-indigo-700"
              iconBgClass="bg-indigo-50"
            />
          )}
        </div>

        {/* AI Summary Section */}
        {!isLoading && scorecard && (
          <section className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden mb-8">
            <div className="px-5 py-4 sm:px-6 sm:py-5 border-b border-slate-100 bg-gradient-to-r from-slate-50/80 to-white">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm">
                  <TrendingUp size={16} className="text-white" />
                </div>
                <h2 className="text-base sm:text-lg font-bold text-slate-800">
                  AI 종합 의견
                </h2>
              </div>
            </div>
            <div className="p-5 sm:p-6 space-y-4">
              {/* Category analysis */}
              {scorecard.categories.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    카테고리별 평가
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {scorecard.categories.map((cat) => {
                      const catScore = Math.round(cat.score);
                      const level =
                        catScore >= 70
                          ? { label: "상", color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200" }
                          : catScore >= 40
                          ? { label: "중", color: "text-amber-600", bg: "bg-amber-50 border-amber-200" }
                          : { label: "하", color: "text-rose-600", bg: "bg-rose-50 border-rose-200" };

                      const barColor =
                        catScore >= 70
                          ? "bg-emerald-500"
                          : catScore >= 40
                          ? "bg-amber-500"
                          : "bg-rose-500";
                      const trackColor =
                        catScore >= 70
                          ? "bg-emerald-100"
                          : catScore >= 40
                          ? "bg-amber-100"
                          : "bg-rose-100";

                      return (
                        <div
                          key={cat.name}
                          className={cn(
                            "rounded-xl p-3 border",
                            level.bg
                          )}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span className={cn("text-xs font-semibold", level.color)}>
                              {cat.name}
                            </span>
                            <div className="flex items-center gap-1.5">
                              <span
                                className={cn(
                                  "text-[10px] font-bold px-1.5 py-0.5 rounded",
                                  level.color,
                                  catScore >= 70
                                    ? "bg-emerald-100"
                                    : catScore >= 40
                                    ? "bg-amber-100"
                                    : "bg-rose-100"
                                )}
                              >
                                {level.label}
                              </span>
                              <span className={cn("text-sm font-bold", level.color)}>
                                {catScore}
                                <span className="text-[10px] text-slate-400 font-normal">
                                  {" "}/ 100
                                </span>
                              </span>
                            </div>
                          </div>
                          <div className={cn("w-full h-2 rounded-full overflow-hidden", trackColor)}>
                            <div
                              className={cn("h-full rounded-full transition-all duration-700 ease-out", barColor)}
                              style={{ width: `${Math.min(100, Math.max(0, catScore))}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Strengths & Weaknesses */}
              {scorecard.categories.length > 0 && (() => {
                const strengths = scorecard.categories.filter(
                  (c) => Math.round(c.score) >= 70
                );
                const weaknesses = scorecard.categories.filter(
                  (c) => Math.round(c.score) < 40
                );

                if (strengths.length === 0 && weaknesses.length === 0) return null;

                return (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {strengths.length > 0 && (
                      <div className="rounded-xl bg-emerald-50/60 border border-emerald-200/60 p-4">
                        <h4 className="text-xs font-bold text-emerald-700 uppercase tracking-wide mb-2">
                          강점
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                          {strengths.map((s) => (
                            <span
                              key={s.name}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-medium"
                            >
                              <CheckCircle size={12} />
                              {s.name} ({Math.round(s.score)}점)
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {weaknesses.length > 0 && (
                      <div className="rounded-xl bg-rose-50/60 border border-rose-200/60 p-4">
                        <h4 className="text-xs font-bold text-rose-700 uppercase tracking-wide mb-2">
                          보완 필요
                        </h4>
                        <div className="flex flex-wrap gap-1.5">
                          {weaknesses.map((w) => (
                            <span
                              key={w.name}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-rose-100 text-rose-700 text-xs font-medium"
                            >
                              <AlertTriangle size={12} />
                              {w.name} ({Math.round(w.score)}점)
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })()}

              {/* Additional warnings */}
              {simulation && (
                <div className="space-y-2">
                  {survivalRate !== null && survivalRate < 0.6 && (
                    <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50/80 px-4 py-3">
                      <XCircle size={16} className="text-rose-500 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-rose-800 leading-relaxed">
                        2년 생존율이{" "}
                        <span className="font-bold">
                          {Math.round(survivalRate * 100)}%
                        </span>
                        로 낮습니다. 철저한 리스크 관리 전략을 수립하세요.
                      </p>
                    </div>
                  )}
                  {storeCount !== null && storeCount > 80 && (
                    <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50/80 px-4 py-3">
                      <AlertTriangle size={16} className="text-amber-500 flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-amber-800 leading-relaxed">
                        동일 업종 점포가{" "}
                        <span className="font-bold">{storeCount}개</span>
                        로 경쟁이 치열합니다. 차별화 전략이 중요합니다.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        )}

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 py-8 border-t border-slate-100 mt-4">
          <Link
            href={`/business-plan?district_code=${districtCode}&industry_code=${industryCode}`}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold shadow-lg shadow-blue-500/25 hover:shadow-xl transition-all active:scale-[0.98] text-sm w-full sm:w-auto justify-center"
          >
            <FileText size={16} />
            사업계획서 다운로드
          </Link>
          <button
            onClick={() => {
              useJourneyStore.getState().reset();
              router.push("/");
            }}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-100 text-slate-700 font-semibold hover:bg-slate-200 transition-all active:scale-[0.98] text-sm w-full sm:w-auto justify-center"
          >
            <RotateCcw size={16} />
            처음부터 다시 분석
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Page Export (with Suspense for useSearchParams)
// ============================================================================

export default function SummaryPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-blue-50/30 flex items-center justify-center">
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto" />
            <p className="text-sm text-slate-500">요약 보고서 로딩 중...</p>
          </div>
        </div>
      }
    >
      <SummaryContent />
    </Suspense>
  );
}
