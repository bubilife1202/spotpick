"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  FileText,
  TrendingUp,
  DollarSign,
  Users,
  Store,
  Shield,
  CalendarDays,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Download,
  SlidersHorizontal,
  BarChart3,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { track } from "@/lib/analytics";
import { JourneyStepper } from "@/components/JourneyStepper";
import { JourneyContextBadge } from "@/components/JourneyContextBadge";
import { useJourneyStore } from "@/lib/journey-store";
import { ScorecardCard } from "@/components/ScorecardCard";
import { ChatChartSection } from "@/components/ChatChart";
import { SupportProgramList } from "@/components/SupportProgramCard";
import type {
  ScorecardResult,
  SimulationData,
  ChartData,
  CompetitiveInsight,
  TrademarkCheckResult,
  TimelineData,
  SupportProgramData,
  DistrictIncomeInfo,
} from "@/types/chat";

// ============================================================================
// Constants
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

const INDUSTRY_NAMES: Record<string, string> = {
  CS100001: "한식", CS100002: "중식", CS100003: "일식", CS100004: "양식",
  CS100005: "베이커리", CS100006: "패스트푸드", CS100007: "치킨",
  CS100008: "분식", CS100009: "호프/주점", CS100010: "카페",
};

const INDUSTRY_ICONS: Record<string, string> = {
  CS100001: "🍚", CS100002: "🥟", CS100003: "🍣", CS100004: "🍝",
  CS100005: "🍞", CS100006: "🍔", CS100007: "🍗",
  CS100008: "🍜", CS100009: "🍺", CS100010: "☕",
};

// ============================================================================
// Helpers
// ============================================================================

function formatMan(value: number) {
  return `${Math.round(value / 10000).toLocaleString()}만원`;
}

function formatManRange(min: number, max: number) {
  return `${formatMan(min)} ~ ${formatMan(max)}`;
}

function formatKRWCompact(value: number) {
  if (!Number.isFinite(value) || value <= 0) return "-";
  if (value >= 100_000_000) {
    const eok = value / 100_000_000;
    return `${eok >= 100 ? eok.toFixed(0) : eok.toFixed(1)}억`;
  }
  if (value >= 10_000) {
    return `${Math.round(value / 10_000).toLocaleString()}만`;
  }
  return `${Math.round(value).toLocaleString()}원`;
}

// ============================================================================
// Skeleton Components
// ============================================================================

function SectionSkeleton({ lines = 4 }: { lines?: number }) {
  return (
    <div className="animate-pulse space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-4 bg-slate-200 rounded"
          style={{ width: `${70 + Math.random() * 30}%` }}
        />
      ))}
    </div>
  );
}

function CardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-5 sm:p-6 animate-pulse">
      <div className="h-5 w-32 bg-slate-200 rounded mb-4" />
      <div className="space-y-3">
        <div className="h-4 bg-slate-200 rounded w-full" />
        <div className="h-4 bg-slate-200 rounded w-3/4" />
        <div className="h-4 bg-slate-200 rounded w-1/2" />
      </div>
    </div>
  );
}

// ============================================================================
// Section Components
// ============================================================================

function SectionCard({
  icon,
  title,
  children,
  className,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden",
        className
      )}
    >
      <div className="px-5 py-4 sm:px-6 sm:py-5 border-b border-slate-100 bg-gradient-to-r from-slate-50/80 to-white">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm">
            {icon}
          </div>
          <h2 className="text-base sm:text-lg font-bold text-slate-800">{title}</h2>
        </div>
      </div>
      <div className="p-5 sm:p-6">{children}</div>
    </section>
  );
}

// --- Analysis Info Box ---
function AnalysisInfoBox({ text }: { text: string | undefined }) {
  if (!text) return null;
  return (
    <div className="mb-4 rounded-xl border border-blue-200 bg-blue-50/60 px-4 py-3">
      <p className="text-sm text-blue-800 leading-relaxed">{text}</p>
    </div>
  );
}

// --- Category interpretation helper ---
function getCategoryInterpretation(name: string, score: number): string {
  const s = Math.round(score);
  if (name === "매출력") {
    if (s >= 75) return "매출 수준이 높아 수익 확보에 유리합니다";
    if (s >= 50) return "매출 수준이 보통이므로 차별화 전략이 필요합니다";
    return "매출이 낮아 수요 창출 전략이 필수입니다";
  }
  if (name === "성장성") {
    if (s >= 75) return "상권이 성장 중이며 신규 진입에 적합합니다";
    if (s >= 50) return "성장세가 보통이므로 시장 변화를 주시하세요";
    return "상권이 정체/위축 중이라 진입에 신중해야 합니다";
  }
  if (name === "경쟁환경") {
    if (s >= 75) return "경쟁이 적어 시장 선점 기회가 있습니다";
    if (s >= 50) return "경쟁이 보통 수준으로 차별화가 권장됩니다";
    return "경쟁이 치열하여 강력한 차별화가 필요합니다";
  }
  if (name === "입지여건") {
    if (s >= 75) return "교통·유동인구 등 입지 조건이 우수합니다";
    if (s >= 50) return "입지 조건이 보통으로 마케팅 보완이 필요합니다";
    return "입지 여건이 부족하여 접근성 개선이 과제입니다";
  }
  if (name === "안정성") {
    if (s >= 75) return "생존율이 높아 장기 운영에 안정적입니다";
    if (s >= 50) return "안정성이 보통이므로 리스크 관리가 중요합니다";
    return "생존율이 낮아 철저한 사전 준비가 필요합니다";
  }
  return s >= 60 ? "양호한 수준입니다" : "보완이 필요합니다";
}

// --- Section 1: Go/No-Go ---
function GoNoGoSection({
  scorecard,
  loading,
  verdictSummary,
  industryName,
}: {
  scorecard: ScorecardResult | null;
  loading: boolean;
  verdictSummary?: string;
  industryName?: string;
}) {
  if (loading) return <CardSkeleton />;
  if (!scorecard) return null;

  const score = Math.round(scorecard.total_score);
  const topPercent = Math.max(1, Math.round(100 - scorecard.percentile));

  // Derive success probability heuristic from score
  const successProb = Math.min(99, Math.max(10, Math.round(score * 0.95 + 5)));

  // Score-based verdict badge: >=75 green "추천", 50-74 amber "보통", <50 red "주의"
  const verdict =
    score >= 75
      ? { label: "추천", color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200", badgeBg: "bg-gradient-to-r from-emerald-500 to-emerald-600", glowClass: "glow-emerald", icon: <CheckCircle size={24} className="text-white" /> }
      : score >= 50
        ? { label: "보통", color: "text-amber-600", bg: "bg-amber-50 border-amber-200", badgeBg: "bg-gradient-to-r from-amber-500 to-amber-600", glowClass: "glow-amber", icon: <AlertTriangle size={24} className="text-white" /> }
        : { label: "주의", color: "text-rose-600", bg: "bg-rose-50 border-rose-200", badgeBg: "bg-gradient-to-r from-rose-500 to-rose-600", glowClass: "glow-rose", icon: <XCircle size={24} className="text-white" /> };

  const probColor =
    successProb >= 70 ? "text-emerald-600" : successProb >= 50 ? "text-amber-600" : "text-rose-600";

  const catColors: Record<string, string> = {
    "매출력": "text-blue-600",
    "성장성": "text-green-600",
    "경쟁환경": "text-amber-600",
    "입지여건": "text-purple-600",
    "안정성": "text-teal-600",
  };

  // Identify dangerously low categories (score < 30)
  const dangerousCategories = scorecard.categories.filter(
    (cat) => Math.round(cat.score) < 30
  );

  // Score-based progress bar color
  const getScoreBarColor = (s: number) => {
    if (s >= 70) return "bg-emerald-500";
    if (s >= 50) return "bg-amber-500";
    return "bg-rose-500";
  };

  const getScoreBarTrack = (s: number) => {
    if (s >= 70) return "bg-emerald-100";
    if (s >= 50) return "bg-amber-100";
    return "bg-rose-100";
  };

  return (
    <SectionCard icon={<TrendingUp size={16} className="text-white" />} title="종합 판정">
      <div className="space-y-6">
        {/* Top row: Big verdict badge + success probability */}
        <div className="flex flex-col sm:flex-row items-center gap-5">
          {/* Large verdict badge with animated glow */}
          <div className="flex flex-col items-center gap-2">
            <div
              className={cn(
                "flex items-center gap-3 px-6 py-4 rounded-2xl shadow-md text-white animate-verdict-glow",
                verdict.badgeBg,
                verdict.glowClass,
              )}
            >
              {verdict.icon}
              <span className="text-2xl font-extrabold">{verdict.label}</span>
            </div>
            {industryName && (
              <p className="text-xs text-slate-500 text-center leading-snug max-w-[200px]">
                이 상권에서 <span className="font-semibold text-slate-700">{industryName}</span> 창업은{" "}
                <span className={cn("font-bold", verdict.color)}>{verdict.label}</span>입니다
              </p>
            )}
          </div>
          <div className="text-center sm:text-left">
            <p className="text-xs text-slate-500 mb-1">예상 성공확률</p>
            <span className={cn("text-5xl sm:text-6xl font-extrabold tracking-tight", probColor)}>
              {successProb}%
            </span>
            <div className="flex items-center gap-3 text-sm text-slate-600 mt-1">
              <span className="font-semibold text-slate-800">{score}/100점</span>
              <span className="text-slate-400">|</span>
              <span>상위 {topPercent}%</span>
            </div>
          </div>
        </div>

        {/* AI commentary */}
        {verdictSummary && (
          <p className="text-sm text-slate-600 leading-relaxed bg-slate-50 rounded-xl p-4 border border-slate-200/60">
            {verdictSummary}
          </p>
        )}

        {/* Warning banners for dangerously low categories */}
        {dangerousCategories.length > 0 && (
          <div className="space-y-2">
            {dangerousCategories.map((cat) => {
              const catScore = Math.round(cat.score);
              const interpretation = getCategoryInterpretation(cat.name, cat.score);
              return (
                <div
                  key={`warn-${cat.name}`}
                  className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50/80 px-4 py-3"
                >
                  <AlertTriangle size={18} className="text-rose-500 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-rose-800 leading-relaxed">
                    <span className="font-bold">{cat.name}</span> 점수가 매우 낮습니다 (
                    <span className="font-bold">{catScore}점</span>). {interpretation}
                  </p>
                </div>
              );
            })}
          </div>
        )}

        {/* Category interpretations with progress bars — transparent scorecard */}
        {scorecard.categories.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">5대 카테고리 평가</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {scorecard.categories.map((cat) => {
                const catScore = Math.round(cat.score);
                const interpretation = getCategoryInterpretation(cat.name, cat.score);
                const colorClass = catColors[cat.name] || "text-slate-600";
                const weightPercent = cat.weight != null ? Math.round(cat.weight * 100) : null;
                const scoreBarColor = getScoreBarColor(catScore);
                const trackColor = getScoreBarTrack(catScore);

                return (
                  <div
                    key={cat.name}
                    className={cn(
                      "bg-slate-50/80 rounded-xl p-3 border",
                      catScore < 30
                        ? "border-rose-200/80"
                        : "border-slate-100"
                    )}
                  >
                    {/* Header: name + weight + score */}
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className={cn("text-xs font-semibold", colorClass)}>
                          {cat.name}
                        </span>
                        {weightPercent != null && (
                          <span className="text-[10px] text-slate-400 font-medium">
                            (가중치 {weightPercent}%)
                          </span>
                        )}
                      </div>
                      <span className={cn("text-sm font-bold", colorClass)}>
                        {catScore}<span className="text-[10px] text-slate-400 font-normal"> / 100</span>
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className={cn("w-full h-2 rounded-full overflow-hidden mb-2", trackColor)}>
                      <div
                        className={cn(
                          "h-full rounded-full transition-all duration-700 ease-out",
                          scoreBarColor,
                        )}
                        style={{ width: `${Math.min(100, Math.max(0, catScore))}%` }}
                      />
                    </div>

                    {/* Interpretation */}
                    <p className="text-xs text-slate-500 leading-relaxed">{interpretation}</p>

                    {/* Sub-items breakdown */}
                    {cat.items && cat.items.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-slate-200/60 space-y-1">
                        {cat.items.map((item) => {
                          const itemPct = Math.round(item.percentile);
                          return (
                            <div key={item.feature} className="flex items-center gap-2">
                              <span className="text-[10px] text-slate-400 w-16 truncate flex-shrink-0">{item.label}</span>
                              <div className="flex-1 h-1.5 bg-slate-200/80 rounded-full overflow-hidden">
                                <div
                                  className={cn(
                                    "h-full rounded-full",
                                    itemPct >= 70 ? "bg-emerald-400" : itemPct >= 40 ? "bg-amber-400" : "bg-rose-400"
                                  )}
                                  style={{ width: `${Math.min(100, Math.max(0, itemPct))}%` }}
                                />
                              </div>
                              <span className="text-[10px] text-slate-500 font-medium w-8 text-right">{itemPct}%</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Detailed scorecard (collapsible) */}
        <div>
          <ScorecardCard scorecard={scorecard} />
        </div>
      </div>
    </SectionCard>
  );
}

// --- Section 2: Profitability ---
function ProfitabilitySection({
  simulation,
  loading,
  comment,
}: {
  simulation: SimulationData | null;
  loading: boolean;
  comment?: string;
}) {
  if (loading) return <CardSkeleton />;
  if (!simulation) return null;

  const { startup_cost: startup, operating_cost: operating, break_even: breakEven, revenue, franchise_benchmark, menu_costs } = simulation;
  const operatingPercent = (value: number) =>
    operating.total > 0 ? Math.round((value / operating.total) * 100) : 0;
  const hasFranchise = franchise_benchmark?.startup_costs && franchise_benchmark.startup_costs.length > 0;

  return (
    <SectionCard icon={<DollarSign size={16} className="text-white" />} title="수익성 분석">
      <div className="space-y-6">
        <AnalysisInfoBox text={comment} />

        {/* Key metrics summary cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100/50 rounded-xl p-3 border border-blue-200/60 text-center">
            <p className="text-[10px] font-semibold text-blue-600 uppercase tracking-wide mb-1">초기 투자</p>
            <p className="text-lg font-bold text-blue-800">{formatManRange(startup.total_min, startup.total_max)}</p>
          </div>
          <div className="bg-gradient-to-br from-amber-50 to-amber-100/50 rounded-xl p-3 border border-amber-200/60 text-center">
            <p className="text-[10px] font-semibold text-amber-600 uppercase tracking-wide mb-1">월 운영비</p>
            <p className="text-lg font-bold text-amber-800">{formatMan(operating.total)}</p>
          </div>
          <div className="bg-gradient-to-br from-emerald-50 to-emerald-100/50 rounded-xl p-3 border border-emerald-200/60 text-center">
            <p className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wide mb-1">예상 월매출</p>
            <p className="text-lg font-bold text-emerald-800">{formatKRWCompact(revenue.monthly_sales_per_store)}</p>
          </div>
          <div className="bg-gradient-to-br from-purple-50 to-purple-100/50 rounded-xl p-3 border border-purple-200/60 text-center">
            <p className="text-[10px] font-semibold text-purple-600 uppercase tracking-wide mb-1">투자 회수</p>
            <p className="text-lg font-bold text-purple-800">{breakEven.break_even_months_min}~{breakEven.break_even_months_max}개월</p>
          </div>
        </div>

        {/* Revenue scenarios */}
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">월매출 시나리오</h3>
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: "비관", value: revenue.pessimistic, color: "text-rose-600 bg-rose-50 border-rose-200" },
              { label: "보통", value: revenue.monthly_sales_per_store, color: "text-blue-600 bg-blue-50 border-blue-200" },
              { label: "낙관", value: revenue.optimistic, color: "text-emerald-600 bg-emerald-50 border-emerald-200" },
            ].map((s) => (
              <div key={s.label} className={cn("rounded-xl border p-3 text-center", s.color)}>
                <p className="text-[10px] font-semibold uppercase tracking-wide mb-1">{s.label}</p>
                <p className="text-lg sm:text-xl font-bold">{formatKRWCompact(s.value)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Startup cost: independent vs franchise */}
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <DollarSign size={14} className="text-emerald-600" />
            초기 투자비용
          </h3>
          {hasFranchise ? (() => {
            const fb = franchise_benchmark!;
            const costs = fb.startup_costs!;
            const avgFranchiseFee = Math.round(costs.reduce((s, c) => s + c.franchise_fee, 0) / costs.length);
            const avgEducationFee = Math.round(costs.reduce((s, c) => s + c.education_fee, 0) / costs.length);
            const avgOtherFee = Math.round(costs.reduce((s, c) => s + c.other_fee, 0) / costs.length);
            const avgTotal = fb.avg_total_startup_cost || Math.round(costs.reduce((s, c) => s + c.total_joining_cost, 0) / costs.length);
            return (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 space-y-2">
                  <p className="text-xs font-semibold text-blue-700 text-center pb-2 border-b border-blue-200/60">독립창업 예상</p>
                  <div className="space-y-1 text-xs">
                    {[
                      ["보증금", formatMan(startup.deposit)],
                      ["인테리어", formatMan(startup.interior)],
                      ["장비", `${formatMan(startup.equipment_min)}~${formatMan(startup.equipment_max)}`],
                      ["재고+기타", `${formatMan(startup.initial_inventory_min + startup.permits_misc_min)}~${formatMan(startup.initial_inventory_max + startup.permits_misc_max)}`],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-slate-500">{k}</span>
                        <span className="text-blue-800 font-medium">{v}</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-between pt-2 border-t border-blue-200/60 text-sm">
                    <span className="font-semibold text-blue-700">합계</span>
                    <span className="font-bold text-blue-800">{formatManRange(startup.total_min, startup.total_max)}</span>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 space-y-2">
                  <p className="text-xs font-semibold text-slate-500 text-center pb-2 border-b border-slate-200/60">가맹평균 (공정위)</p>
                  <div className="space-y-1 text-xs">
                    {[
                      ["가맹비", avgFranchiseFee > 0 ? formatMan(avgFranchiseFee) : "-"],
                      ["교육비", avgEducationFee > 0 ? formatMan(avgEducationFee) : "-"],
                      ["기타 가입비", avgOtherFee > 0 ? formatMan(avgOtherFee) : "-"],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between">
                        <span className="text-slate-400">{k}</span>
                        <span className="text-slate-600 font-medium">{v}</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex justify-between pt-2 border-t border-slate-200/60 text-sm">
                    <span className="font-semibold text-slate-500">합계</span>
                    <span className="font-bold text-slate-700">{avgTotal > 0 ? formatMan(avgTotal) : "-"}</span>
                  </div>
                  <p className="text-[10px] text-slate-400 text-center">
                    {fb.source}{fb.brand_count ? ` (${fb.brand_count}개 브랜드)` : ""}
                  </p>
                </div>
              </div>
            );
          })() : (
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-slate-500">총 투자</span>
                <span className="font-semibold text-slate-800">{formatManRange(startup.total_min, startup.total_max)}</span>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="px-2 py-1 rounded-full bg-emerald-50 text-emerald-700">보증금 {formatMan(startup.deposit)}</span>
                <span className="px-2 py-1 rounded-full bg-slate-100 text-slate-600">인테리어 {formatMan(startup.interior)}</span>
                <span className="px-2 py-1 rounded-full bg-slate-100 text-slate-600">장비 {formatMan(startup.equipment_min)}~{formatMan(startup.equipment_max)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Monthly operating cost */}
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <Clock size={14} className="text-amber-600" />
            월 운영비
          </h3>
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-4">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-slate-500">총 운영비</span>
              <span className="font-semibold text-slate-800">{formatMan(operating.total)}/월</span>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="px-2 py-1 rounded-full bg-slate-100 text-slate-600">월세 {formatMan(operating.rent)}</span>
              <span className="px-2 py-1 rounded-full bg-amber-100 text-amber-700">재료비 {operatingPercent(operating.cogs)}%</span>
              <span className="px-2 py-1 rounded-full bg-amber-100 text-amber-700">인건비 {operatingPercent(operating.labor)}%</span>
              <span className="px-2 py-1 rounded-full bg-slate-100 text-slate-600">공과금 {formatMan(operating.utilities)}</span>
              <span className="px-2 py-1 rounded-full bg-slate-100 text-slate-600">기타 {formatMan(operating.other)}</span>
            </div>
          </div>
        </div>

        {/* Break even */}
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <TrendingUp size={14} className="text-emerald-600" />
            손익분기
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "월 순이익", value: formatMan(breakEven.monthly_net_profit), color: "text-emerald-700" },
              { label: "이익률", value: `${(breakEven.net_profit_margin * 100).toFixed(1)}%`, color: "text-emerald-700" },
              { label: "투자회수", value: `${breakEven.break_even_months_min}~${breakEven.break_even_months_max}개월`, color: "text-slate-700" },
              { label: "일 손익분기", value: formatMan(breakEven.daily_break_even_sales), color: "text-amber-700" },
            ].map((item) => (
              <div key={item.label} className="bg-slate-50 rounded-xl p-3 text-center">
                <p className="text-[10px] text-slate-500 mb-1">{item.label}</p>
                <p className={cn("text-sm font-bold", item.color)}>{item.value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Menu costs */}
        {menu_costs && menu_costs.menu_costs.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-3">메뉴 원가</h3>
            <div className="grid gap-1.5 text-xs text-slate-600">
              {menu_costs.menu_costs.slice(0, 6).map((item) => (
                <div key={item.menu} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2">
                  <span>{item.menu} {item.cost.toLocaleString()}원 → {item.selling_price.toLocaleString()}원</span>
                  <span className="text-emerald-700 font-semibold">마진 {(item.margin_rate * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Data source */}
        {simulation.assumptions && (
          <p className="text-[10px] text-slate-400 text-right">
            {simulation.assumptions.summary} &middot; {simulation.assumptions.disclaimer}
          </p>
        )}
      </div>
    </SectionCard>
  );
}

// --- Section 3: Customer Analysis ---
function CustomerAnalysisSection({
  charts,
  singleHouseholdRatio,
  incomeInfo,
  footTraffic,
  workerTotal,
  loading,
  comment,
}: {
  charts: ChartData[];
  singleHouseholdRatio: number | null;
  incomeInfo: DistrictIncomeInfo | null;
  footTraffic: number | null;
  workerTotal: number | null;
  loading: boolean;
  comment?: string;
}) {
  if (loading) return <CardSkeleton />;
  if (charts.length === 0 && !singleHouseholdRatio && !incomeInfo) return null;

  return (
    <SectionCard icon={<Users size={16} className="text-white" />} title="고객 분석">
      <div className="space-y-5">
        <AnalysisInfoBox text={comment} />
        {/* Charts 2x2 */}
        {charts.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {charts.map((chart, i) => (
              <div key={`${chart.type}-${i}`}>
                <ChatChartSection charts={[chart]} />
              </div>
            ))}
          </div>
        )}

        {/* Badges row */}
        <div className="flex flex-wrap gap-2">
          {singleHouseholdRatio != null && singleHouseholdRatio > 0 && (
            <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-orange-50 text-orange-700 border border-orange-200">
              1인가구 {(singleHouseholdRatio * 100).toFixed(0)}%
            </span>
          )}
          {incomeInfo && (
            <span className={cn(
              "px-3 py-1.5 rounded-full text-xs font-medium border",
              incomeInfo.income_level === "상" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
              incomeInfo.income_level === "중" ? "bg-blue-50 text-blue-700 border-blue-200" :
              "bg-slate-50 text-slate-600 border-slate-200"
            )}>
              소득수준 {incomeInfo.income_level} ({formatKRWCompact(incomeInfo.avg_monthly_income)}/월)
            </span>
          )}
          {footTraffic != null && footTraffic > 0 && (
            <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
              유동인구 {footTraffic >= 1_000_000 ? `${(footTraffic / 10_000).toFixed(0)}만` : `${(footTraffic / 1_000).toFixed(0)}K`}
            </span>
          )}
          {workerTotal != null && workerTotal > 0 && (
            <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
              직장인구 {workerTotal >= 10_000 ? `${(workerTotal / 10_000).toFixed(1)}만` : `${(workerTotal / 1_000).toFixed(1)}K`}
            </span>
          )}
        </div>
      </div>
    </SectionCard>
  );
}

// --- Section 4: Competition ---
function CompetitionSection({
  competitive,
  industryName,
  loading,
  comment,
}: {
  competitive: CompetitiveInsight | null;
  industryName: string;
  loading: boolean;
  comment?: string;
}) {
  if (loading) return <CardSkeleton />;
  if (!competitive) return null;

  return (
    <SectionCard icon={<Store size={16} className="text-white" />} title="경쟁 환경">
      <div className="space-y-5">
        <AnalysisInfoBox text={comment} />
        <div className="flex items-center gap-3 text-sm">
          <span className="text-slate-500">주변 {industryName} 매장</span>
          <span className="text-xl font-bold text-slate-800">{competitive.total_nearby_cafes}개</span>
        </div>

        {/* Cafe type distribution */}
        {competitive.cafe_types.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">{industryName} 유형 분포</h3>
            <div className="space-y-2">
              {competitive.cafe_types.slice(0, 5).map((ct, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs text-slate-600 w-20 truncate">{ct.type}</span>
                  <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        i === 0 ? "bg-amber-400" : i === 1 ? "bg-blue-400" : "bg-slate-300"
                      )}
                      style={{ width: `${Math.min(100, ct.ratio)}%` }}
                    />
                  </div>
                  <span className="text-xs font-semibold text-slate-700 w-12 text-right">{ct.ratio}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Market gaps */}
        {competitive.market_gaps.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">시장 틈새</h3>
            <div className="space-y-2">
              {competitive.market_gaps.slice(0, 3).map((gap, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <span className={cn(
                    "w-2 h-2 rounded-full mt-1.5 flex-shrink-0",
                    gap.opportunity_score >= 0.7 ? "bg-emerald-500" :
                    gap.opportunity_score >= 0.4 ? "bg-amber-500" : "bg-slate-400"
                  )} />
                  <span className="text-slate-600">{gap.description}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Strategies — show up to 5 */}
        {competitive.strategies.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">차별화 전략</h3>
            <div className="space-y-2">
              {competitive.strategies.slice(0, 5).map((s, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <span className={cn(
                    "px-1.5 py-0.5 rounded text-[10px] font-semibold flex-shrink-0 mt-0.5",
                    s.priority === "high" ? "bg-rose-100 text-rose-700" :
                    s.priority === "medium" ? "bg-amber-100 text-amber-700" :
                    "bg-emerald-100 text-emerald-700"
                  )}>
                    {s.priority === "high" ? "높음" : s.priority === "medium" ? "중간" : "낮음"}
                  </span>
                  <div>
                    <span className="font-medium text-slate-700">{s.strategy}</span>
                    <p className="text-xs text-slate-500 mt-0.5">{s.reason}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Competitor list table */}
        {competitive.top_competitors && competitive.top_competitors.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">주요 경쟁사</h3>
            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="w-full text-xs">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="text-left px-3 py-2 font-semibold text-slate-600">매장명</th>
                    <th className="text-left px-3 py-2 font-semibold text-slate-600">유형</th>
                    <th className="text-left px-3 py-2 font-semibold text-slate-600 hidden sm:table-cell">주소</th>
                  </tr>
                </thead>
                <tbody>
                  {competitive.top_competitors.slice(0, 8).map((comp, i) => (
                    <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-slate-50/50"}>
                      <td className="px-3 py-2 text-slate-800 font-medium">{comp.name}</td>
                      <td className="px-3 py-2 text-slate-600">{comp.category}</td>
                      <td className="px-3 py-2 text-slate-500 hidden sm:table-cell truncate max-w-[200px]">{comp.address}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </SectionCard>
  );
}

// --- Section 5: Risk Check ---
function RiskSection({
  trademark,
  riskFactors,
  loading,
  comment,
}: {
  trademark: TrademarkCheckResult | null;
  riskFactors: string[];
  loading: boolean;
  comment?: string;
}) {
  if (loading) return <CardSkeleton />;
  if (!trademark && riskFactors.length === 0 && !comment) return null;

  return (
    <SectionCard icon={<Shield size={16} className="text-white" />} title="리스크 체크">
      <div className="space-y-5">
        <AnalysisInfoBox text={comment} />
        {/* Trademark check */}
        {trademark && (
          <div className={cn(
            "rounded-xl border p-4 space-y-3",
            trademark.risk_level === "high" ? "bg-rose-50 border-rose-200" :
            trademark.risk_level === "medium" ? "bg-amber-50 border-amber-200" :
            "bg-emerald-50 border-emerald-200"
          )}>
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-slate-700">
                &ldquo;{trademark.query}&rdquo; 상표 충돌 확인
              </span>
              <span className={cn(
                "text-xs font-semibold px-2.5 py-1 rounded-full",
                trademark.risk_level === "high" ? "bg-rose-100 text-rose-700" :
                trademark.risk_level === "medium" ? "bg-amber-100 text-amber-700" :
                "bg-emerald-100 text-emerald-700"
              )}>
                {trademark.risk_level === "high" ? "위험 높음" :
                 trademark.risk_level === "medium" ? "주의" : "양호"}
              </span>
            </div>
            {trademark.conflicts.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {trademark.conflicts.slice(0, 5).map((c, i) => (
                  <span key={i} className={cn(
                    "px-2 py-1 rounded text-xs font-medium",
                    c.similarity >= 0.95 ? "bg-rose-100 text-rose-700" :
                    c.similarity >= 0.85 ? "bg-amber-100 text-amber-700" :
                    "bg-slate-100 text-slate-600"
                  )}>
                    {c.name} ({Math.round(c.similarity * 100)}%)
                  </span>
                ))}
              </div>
            )}
            {trademark.suggestions.length > 0 && (
              <ul className="text-xs text-slate-600 space-y-1">
                {trademark.suggestions.map((s, i) => (
                  <li key={i}>&bull; {s}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Risk factors */}
        {riskFactors.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">주요 리스크 요인</h3>
            <div className="space-y-2">
              {riskFactors.map((rf, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <AlertTriangle size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
                  <span className="text-slate-600">{rf}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </SectionCard>
  );
}

// --- Section 6: Timeline ---
function TimelineSection({
  timeline,
  supportPrograms,
  loadingTimeline,
  loadingSupport,
}: {
  timeline: TimelineData | null;
  supportPrograms: SupportProgramData[];
  loadingTimeline: boolean;
  loadingSupport: boolean;
}) {
  return (
    <SectionCard icon={<CalendarDays size={16} className="text-white" />} title="실행 계획">
      <div className="space-y-6">
        {/* Gantt chart */}
        {loadingTimeline ? <SectionSkeleton lines={5} /> : timeline ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm text-slate-600 mb-2">
              <span>총 소요 기간</span>
              <span className="font-semibold text-slate-800">약 {timeline.total_months}개월</span>
            </div>
            <div className="space-y-2">
              {timeline.stages.map((stage, idx) => {
                const maxWeek = timeline.total_weeks;
                const leftPct = (stage.start_week / maxWeek) * 100;
                const widthPct = Math.max(4, ((stage.end_week - stage.start_week) / maxWeek) * 100);
                const colors = [
                  "bg-blue-400", "bg-emerald-400", "bg-amber-400",
                  "bg-purple-400", "bg-rose-400", "bg-teal-400",
                ];
                return (
                  <div key={idx} className="flex items-center gap-3">
                    <span className="text-xs text-slate-500 w-24 text-right flex-shrink-0 truncate">
                      {stage.name}
                    </span>
                    <div className="flex-1 h-6 bg-slate-100 rounded-full relative overflow-hidden">
                      <div
                        className={cn("absolute h-full rounded-full opacity-80", colors[idx % colors.length])}
                        style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                      />
                      <span className="absolute inset-0 flex items-center justify-center text-[10px] text-slate-600 font-medium">
                        {stage.duration_weeks}주
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
              <span>빠르게 ~{timeline.fast_estimate_months}개월</span>
              <span>여유있게 ~{timeline.slow_estimate_months}개월</span>
            </div>
            <p className="text-[11px] text-slate-400 italic">{timeline.summary}</p>
          </div>
        ) : (
          <p className="text-sm text-slate-400">타임라인 데이터를 불러올 수 없습니다.</p>
        )}

        {/* Support programs */}
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-3">정부 지원사업</h3>
          {loadingSupport ? <SectionSkeleton lines={3} /> : supportPrograms.length > 0 ? (
            <SupportProgramList programs={supportPrograms} />
          ) : (
            <p className="text-sm text-slate-400">현재 신청 가능한 지원사업이 없습니다.</p>
          )}
        </div>
      </div>
    </SectionCard>
  );
}

// --- Warning Banners ---
function WarningBanners({
  simulation,
  loading,
}: {
  simulation: SimulationData | null;
  loading: boolean;
}) {
  if (loading || !simulation) return null;

  const { competition, revenue } = simulation;
  const warnings: Array<{ type: "red" | "amber"; label: string; detail: string }> = [];

  // High closure rate: survival_rate < 60%
  if (competition.survival_rate != null && competition.survival_rate < 0.6) {
    const survPct = Math.round(competition.survival_rate * 100);
    warnings.push({
      type: "red",
      label: "폐업률 높음",
      detail: `2년 생존율 ${survPct}% — 동종 업종 평균 대비 폐업 위험이 높습니다. 철저한 리스크 관리가 필요합니다.`,
    });
  }

  // Market saturation: store_count > 100 (highly competitive)
  if (competition.store_count != null && competition.store_count > 100) {
    warnings.push({
      type: "amber",
      label: "경쟁 포화",
      detail: `동일 업종 점포 ${competition.store_count}개 — 상권 내 경쟁이 포화 상태입니다. 강력한 차별화 전략이 필요합니다.`,
    });
  }

  // Low monthly sales: below 15M KRW threshold
  const monthlySales = revenue.monthly_sales_per_store;
  if (monthlySales != null && monthlySales > 0 && monthlySales < 15_000_000) {
    warnings.push({
      type: "amber",
      label: "매출 주의",
      detail: `예상 월매출 ${formatKRWCompact(monthlySales)} — 업종 평균 대비 낮은 수준입니다. 추가 수요 확보 전략을 검토하세요.`,
    });
  }

  if (warnings.length === 0) return null;

  return (
    <div className="space-y-2">
      {warnings.map((w, i) => {
        const isRed = w.type === "red";
        return (
          <div
            key={i}
            className={cn(
              "flex items-start gap-3 rounded-xl border px-4 py-3",
              isRed
                ? "border-rose-200 bg-rose-50/80"
                : "border-amber-200 bg-amber-50/80"
            )}
          >
            {isRed ? (
              <XCircle size={18} className="text-rose-500 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle size={18} className="text-amber-500 flex-shrink-0 mt-0.5" />
            )}
            <div className="min-w-0">
              <span
                className={cn(
                  "text-xs font-bold uppercase tracking-wide",
                  isRed ? "text-rose-700" : "text-amber-700"
                )}
              >
                {w.label}
              </span>
              <p
                className={cn(
                  "text-sm leading-relaxed mt-0.5",
                  isRed ? "text-rose-800" : "text-amber-800"
                )}
              >
                {w.detail}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// --- Journey Data Connection Badge ---
function JourneyDataBadge() {
  const franchiseChoice = useJourneyStore((s) => s.franchiseChoice);
  const budgetMin = useJourneyStore((s) => s.budgetMin);
  const budgetMax = useJourneyStore((s) => s.budgetMax);

  const hasFranchise = franchiseChoice != null;
  const hasBudget = budgetMin > 0 || budgetMax > 0;

  if (!hasFranchise && !hasBudget) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {hasFranchise && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
          <Store size={12} />
          프랜차이즈 비교에서 선택: {franchiseChoice === "franchise" ? "가맹점" : "독립창업"}
        </span>
      )}
      {hasBudget && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-violet-50 text-violet-700 border border-violet-200">
          <DollarSign size={12} />
          예산 범위: {budgetMin.toLocaleString()}~{budgetMax.toLocaleString()}만원
        </span>
      )}
    </div>
  );
}

// ============================================================================
// Main Report Page Content
// ============================================================================

function ReportContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const districtCode = searchParams?.get("district_code") || "";
  const industryCode = searchParams?.get("industry_code") || "CS100010";
  const brandName = searchParams?.get("brand") || "";

  const industryName = INDUSTRY_NAMES[industryCode] || "카페";
  const industryIcon = INDUSTRY_ICONS[industryCode] || "☕";

  // ---- State for all sections ----
  const [districtName, setDistrictName] = useState<string>("");
  const [scorecard, setScorecard] = useState<ScorecardResult | null>(null);
  const [simulation, setSimulation] = useState<SimulationData | null>(null);
  const [charts, setCharts] = useState<ChartData[]>([]);
  const [competitive, setCompetitive] = useState<CompetitiveInsight | null>(null);
  const [trademark, setTrademark] = useState<TrademarkCheckResult | null>(null);
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [supportPrograms, setSupportPrograms] = useState<SupportProgramData[]>([]);
  const [riskFactors, setRiskFactors] = useState<string[]>([]);

  // Customer data badges
  const [singleHouseholdRatio, setSingleHouseholdRatio] = useState<number | null>(null);
  const [incomeInfo, setIncomeInfo] = useState<DistrictIncomeInfo | null>(null);
  const [footTraffic, setFootTraffic] = useState<number | null>(null);
  const [workerTotal, setWorkerTotal] = useState<number | null>(null);
  const [, setCoordinates] = useState<{ lat: number; lng: number } | null>(null);

  // AI Analysis commentary
  const [analysis, setAnalysis] = useState<{
    verdict_summary: string;
    profitability_comment: string;
    customer_comment: string;
    competition_comment: string;
    risk_comment: string;
  } | null>(null);
  const [, setLoadingAnalysis] = useState(true);

  // Loading states
  const [loadingScorecard, setLoadingScorecard] = useState(true);
  const [loadingSimulation, setLoadingSimulation] = useState(true);
  const [loadingCharts, setLoadingCharts] = useState(true);
  const [loadingCompetitive, setLoadingCompetitive] = useState(true);
  const [loadingTrademark, setLoadingTrademark] = useState(true);
  const [loadingTimeline, setLoadingTimeline] = useState(true);
  const [loadingSupport, setLoadingSupport] = useState(true);

  // Set journey step
  useEffect(() => { useJourneyStore.getState().setStep(4); }, []);

  // Analytics: track report view
  useEffect(() => {
    if (districtCode) {
      track("report_view", { district_code: districtCode });
    }
  }, [districtCode]);

  // Reset all state when district/industry changes to prevent stale data flash
  useEffect(() => {
    setScorecard(null);
    setSimulation(null);
    setCharts([]);
    setCompetitive(null);
    setTrademark(null);
    setTimeline(null);
    setSupportPrograms([]);
    setRiskFactors([]);
    setSingleHouseholdRatio(null);
    setIncomeInfo(null);
    setFootTraffic(null);
    setWorkerTotal(null);
    setCoordinates(null);
    setAnalysis(null);
    setLoadingScorecard(true);
    setLoadingSimulation(true);
    setLoadingCharts(true);
    setLoadingCompetitive(true);
    setLoadingTrademark(true);
    setLoadingTimeline(true);
    setLoadingSupport(true);
    setLoadingAnalysis(true);
  }, [districtCode, industryCode]);

  useEffect(() => {
    if (!districtCode) return;

    // Helper to safely fetch JSON
    const safeFetch = async (url: string) => {
      try {
        const res = await fetch(url);
        if (!res.ok) return null;
        return await res.json();
      } catch {
        return null;
      }
    };

    // 1. Scorecard
    safeFetch(`${API_BASE}/scorecard/${industryCode}/${districtCode}`)
      .then((data) => {
        if (data) {
          setScorecard(data);
          if (data.district_name) setDistrictName(data.district_name);
        }
      })
      .finally(() => setLoadingScorecard(false));

    // 2. Simulation
    safeFetch(`${API_BASE}/simulation/simulate/${districtCode}?industry_code=${industryCode}&area_pyeong=15`)
      .then((data) => {
        if (data) {
          setSimulation(data);
          if (data.district_name) setDistrictName((prev) => prev || data.district_name);
          if (data.risk_summary) setRiskFactors(data.risk_summary);
        }
      })
      .finally(() => setLoadingSimulation(false));

    // 3. Charts — try dedicated endpoint first, then recommendations
    safeFetch(`${API_BASE}/districts/${districtCode}/charts?industry_code=${industryCode}`)
      .then(async (data) => {
        if (data && Array.isArray(data.charts) && data.charts.length > 0) {
          setCharts(data.charts);
          if (data.single_household_ratio != null) setSingleHouseholdRatio(data.single_household_ratio);
          if (data.income_info) setIncomeInfo(data.income_info);
          if (data.foot_traffic_total != null) setFootTraffic(data.foot_traffic_total);
          if (data.worker_total != null) setWorkerTotal(data.worker_total);
        } else {
          // Fallback: use detail endpoint for supplementary data
          const detailData = await safeFetch(
            `${API_BASE}/districts/${districtCode}/detail?industry_code=${industryCode}`
          );
          if (detailData) {
            if (detailData.foot_traffic_total) setFootTraffic(detailData.foot_traffic_total);
            if (detailData.worker_total) setWorkerTotal(detailData.worker_total);
            if (detailData.lat && detailData.lng) setCoordinates({ lat: detailData.lat, lng: detailData.lng });
            if (detailData.risk_factors) setRiskFactors((prev) => prev.length > 0 ? prev : detailData.risk_factors);
            if (detailData.district_name) setDistrictName((prev) => prev || detailData.district_name);
          }
        }
      })
      .finally(() => setLoadingCharts(false));

    // 4. Competitive analysis (needs coordinates, but attempt with district name)
    // We try a broader approach: use district name for query if available
    safeFetch(`${API_BASE}/competitive/analyze?query=${encodeURIComponent(industryName)}&district_code=${districtCode}`)
      .then((data) => {
        if (data && data.total_nearby_cafes != null) {
          setCompetitive(data);
        }
      })
      .finally(() => setLoadingCompetitive(false));

    // 5. Trademark check
    const trademarkQuery = brandName || `${industryName}`;
    safeFetch(`${API_BASE}/trademark/check?name=${encodeURIComponent(trademarkQuery)}&industry_code=${industryCode}`)
      .then((data) => {
        if (data && data.risk_level) {
          setTrademark(data);
        }
      })
      .finally(() => setLoadingTrademark(false));

    // 6. Timeline
    safeFetch(`${API_BASE}/districts/${districtCode}/timeline?industry_code=${industryCode}`)
      .then((data) => {
        if (data && data.stages) {
          setTimeline(data);
        }
      })
      .finally(() => setLoadingTimeline(false));

    // 7. Support programs
    safeFetch(`${API_BASE}/support/programs`)
      .then((data) => {
        if (data && Array.isArray(data.programs)) {
          setSupportPrograms(data.programs);
        } else if (data && Array.isArray(data)) {
          setSupportPrograms(data);
        }
      })
      .finally(() => setLoadingSupport(false));

    // 8. AI Analysis commentary
    safeFetch(`${API_BASE}/districts/${districtCode}/analysis?industry_code=${industryCode}`)
      .then((data) => {
        if (data && data.verdict_summary) {
          setAnalysis(data);
        }
      })
      .finally(() => setLoadingAnalysis(false));
  }, [districtCode, industryCode, industryName, brandName]);

  // PDF download handler (reuse same pattern as PDFExportButton)
  const handlePDFDownload = async () => {
    try {
      const res = await fetch(`${API_BASE}/pdf/report?district_code=${districtCode}&industry_code=${industryCode}`, {
        method: "GET",
      });
      if (!res.ok) {
        alert("PDF 생성에 실패했습니다. 잠시 후 다시 시도해주세요.");
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${districtName || "report"}_${industryName}_분석보고서.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      alert("PDF 다운로드 중 오류가 발생했습니다.");
    }
  };

  if (!districtCode) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-blue-50/30 flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-slate-500">분석할 상권을 선택해주세요.</p>
          <button
            onClick={() => router.push("/")}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            홈으로 돌아가기
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
            <span className="text-sm font-semibold text-slate-800 hidden sm:inline">SpotPick</span>
          </div>

          {/* PDF download hidden — endpoint not yet implemented */}
          {false && (
            <button
              onClick={handlePDFDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-xs sm:text-sm font-medium"
            >
              <Download size={14} />
              <span className="hidden sm:inline">PDF 다운로드</span>
              <span className="sm:hidden">PDF</span>
            </button>
          )}
        </div>
      </header>

      <JourneyStepper className="py-3 px-4 bg-white/80 backdrop-blur-sm border-b border-slate-100" />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-4">
        <JourneyContextBadge className="mb-4" />
      </div>

      {/* Title */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-6 pb-4 sm:pt-8 sm:pb-6">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{industryIcon}</span>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">
              {districtName || `상권 ${districtCode}`}
            </h1>
            <p className="text-sm text-slate-500">{industryName} 창업 분석 보고서</p>
          </div>
        </div>
        {/* Journey data connection badge */}
        <JourneyDataBadge />
      </div>

      {/* Sections */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 pb-12 space-y-6">
        {/* Section 1: Go/No-Go */}
        <GoNoGoSection
          scorecard={scorecard}
          loading={loadingScorecard}
          verdictSummary={analysis?.verdict_summary}
          industryName={industryName}
        />

        {/* Warning Banners — risky indicators from simulation */}
        <WarningBanners
          simulation={simulation}
          loading={loadingSimulation}
        />

        {/* Section 2: Profitability */}
        <ProfitabilitySection
          simulation={simulation}
          loading={loadingSimulation}
          comment={analysis?.profitability_comment}
        />

        {/* Section 3: Customer Analysis */}
        <CustomerAnalysisSection
          charts={charts}
          singleHouseholdRatio={singleHouseholdRatio}
          incomeInfo={incomeInfo}
          footTraffic={footTraffic}
          workerTotal={workerTotal}
          loading={loadingCharts}
          comment={analysis?.customer_comment}
        />

        {/* Section 4: Competition */}
        <CompetitionSection
          competitive={competitive}
          industryName={industryName}
          loading={loadingCompetitive}
          comment={analysis?.competition_comment}
        />

        {/* Section 5: Risk */}
        <RiskSection
          trademark={trademark}
          riskFactors={riskFactors}
          loading={loadingTrademark}
          comment={analysis?.risk_comment}
        />

        {/* Section 6: Timeline & Support */}
        <TimelineSection
          timeline={timeline}
          supportPrograms={supportPrograms}
          loadingTimeline={loadingTimeline}
          loadingSupport={loadingSupport}
        />

        {/* Bottom CTA */}
        <div className="flex flex-wrap items-center justify-center gap-3 py-8 border-t border-slate-100 mt-8">
          <Link
            href={`/summary?district_code=${districtCode}&industry_code=${industryCode}`}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-purple-600 text-white font-semibold text-sm shadow-md hover:shadow-lg transition-all"
          >
            <BarChart3 size={16} />
            전체 분석 요약
          </Link>
          <Link
            href={`/simulator?district_code=${districtCode}&industry_code=${industryCode}`}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 text-white font-semibold shadow-lg shadow-emerald-500/25 hover:shadow-xl transition-all active:scale-[0.98] text-sm"
          >
            <SlidersHorizontal size={16} />
            수익 시뮬레이션 해보기
          </Link>
          <Link
            href={`/business-plan?district_code=${districtCode}&industry_code=${industryCode}`}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-semibold shadow-lg shadow-purple-500/25 hover:shadow-xl transition-all active:scale-[0.98] text-sm"
          >
            <FileText size={16} />
            사업계획서 만들기
          </Link>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Page Export (with Suspense for useSearchParams)
// ============================================================================

export default function ReportPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-blue-50/30 flex items-center justify-center">
          <div className="text-center space-y-3">
            <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto" />
            <p className="text-sm text-slate-500">보고서 로딩 중...</p>
          </div>
        </div>
      }
    >
      <ReportContent />
    </Suspense>
  );
}
