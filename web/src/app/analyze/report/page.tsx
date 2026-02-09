"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useAnalyzeStore, type TopDistrict } from "@/lib/analyze-store";
import { AnalyzeStepper } from "@/components/AnalyzeStepper";
import { LocationProfile } from "@/components/LocationProfile";
import { RentTrendChart } from "@/components/RentTrendChart";
import { MiniMap } from "@/components/MiniMap";
import { CompetitionMap } from "@/components/CompetitionMap";
import { ProGateSection } from "@/components/ProGateSection";
import { SalesTrendChart } from "@/components/SalesTrendChart";
import { FloatingTOC } from "@/components/FloatingTOC";
import {
  MapPin,
  ArrowRight,
  Sparkles,
  Loader2,
  Trophy,
  Target,
  TrendingUp,
  Store,
  Users,
  AlertTriangle,
  Building2,
  ArrowDown,
  ArrowUp,
  Minus,
  Gift,
  SlidersHorizontal,
  ChevronRight,
  ChevronDown,
  CreditCard,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// ─── Skeleton component ────────────────────────────────────────────────
function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg bg-slate-200/60",
        className,
      )}
    />
  );
}

function SectionSkeleton({ title }: { title: string }) {
  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Skeleton className="h-5 w-5" />
        <h3 className="text-sm font-bold text-slate-400">{title}</h3>
      </div>
      <div className="space-y-3">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-20 w-full" />
      </div>
    </div>
  );
}

// ─── Data source label ────────────────────────────────────────────────
function DataSource({ text }: { text: string }) {
  return <p className="mt-4 text-[10px] text-slate-400">출처: {text}</p>;
}

// ─── Format helpers ────────────────────────────────────────────────────
function formatWon(value: number): string {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}억원`;
  if (value >= 10_000) return `${Math.round(value / 10_000).toLocaleString()}만원`;
  return `${value.toLocaleString()}원`;
}

function getVerdictStyle(score: number) {
  if (score >= 75) return { label: "추천", color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200" };
  if (score >= 50) return { label: "보통", color: "text-amber-700", bg: "bg-amber-50 border-amber-200" };
  return { label: "주의", color: "text-rose-700", bg: "bg-rose-50 border-rose-200" };
}

function getScoreInterpretation(score: number): string {
  if (score >= 80) return "매우 우수한 수준입니다";
  if (score >= 60) return "양호한 수준입니다";
  if (score >= 40) return "보통 수준입니다";
  return "주의가 필요합니다";
}

// ─── AI Briefing Card ──────────────────────────────────────────────────
function BriefingCard({ districtCode, industryCode }: { districtCode: string; industryCode: string }) {
  const [briefing, setBriefing] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!districtCode) return;
    setLoading(true);
    setBriefing("");
    fetch(`${API_BASE}/districts/${districtCode}/briefing?industry_code=${industryCode}`)
      .then((r) => r.json())
      .then((data) => setBriefing(data.briefing || ""))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [districtCode, industryCode]);

  if (!districtCode) return null;

  // Show skeleton while loading
  if (loading) {
    return (
      <div className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50/80 to-indigo-50/50 p-5">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-blue-500" />
          <h3 className="text-sm font-bold text-blue-900">AI 실시간 브리핑</h3>
        </div>
        <p className="mb-3 text-xs text-blue-600">AI가 상권을 분석하고 있습니다...</p>
        <div className="space-y-2">
          <Skeleton className="h-3 w-full !bg-blue-100/80" />
          <Skeleton className="h-3 w-5/6 !bg-blue-100/80" />
          <Skeleton className="h-3 w-4/6 !bg-blue-100/80" />
        </div>
      </div>
    );
  }

  if (!briefing) return null;

  return (
    <div className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50/80 to-indigo-50/50 p-5">
      <div className="mb-2 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-blue-500" />
        <h3 className="text-sm font-bold text-blue-900">AI 실시간 브리핑</h3>
      </div>
      <p className="text-sm leading-relaxed text-blue-900/80">{briefing}</p>
    </div>
  );
}

// ─── Risk Alert Banner ────────────────────────────────────────────────
function RiskAlertBanner({ districtCode, industryCode }: { districtCode: string; industryCode: string }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [riskData, setRiskAlertData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!districtCode) return;
    setLoading(true);
    fetch(`${API_BASE}/districts/${districtCode}/risk?industry_code=${industryCode}`)
      .then((r) => r.json())
      .then((data) => setRiskAlertData(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [districtCode, industryCode]);

  if (loading || !riskData) return null;

  const level = riskData.risk_level;
  if (level !== "high" && level !== "medium") return null;

  const isHigh = level === "high";
  const signals = (riskData.signals || []).filter(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (s: any) => s.level === "danger" || s.level === "warning"
  );

  return (
    <div
      className={cn(
        "rounded-2xl border p-4",
        isHigh
          ? "border-rose-200 bg-rose-50/80"
          : "border-amber-200 bg-amber-50/80",
      )}
    >
      <div className="flex items-center gap-2">
        <AlertTriangle
          className={cn("h-5 w-5", isHigh ? "text-rose-500" : "text-amber-500")}
        />
        <h3
          className={cn(
            "text-sm font-bold",
            isHigh ? "text-rose-800" : "text-amber-800",
          )}
        >
          {isHigh ? "폐업 위험 높음" : "주의 필요"} — 위험도 {riskData.risk_score}점
        </h3>
      </div>
      {signals.length > 0 && (
        <ul className="mt-2 space-y-1">
          {signals.slice(0, 3).map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (s: any, i: number) => (
              <li
                key={i}
                className={cn(
                  "text-xs",
                  isHigh ? "text-rose-700" : "text-amber-700",
                )}
              >
                · {s.title}: {s.detail}
              </li>
            ),
          )}
        </ul>
      )}
    </div>
  );
}

// ─── Section A: TOP 3 Recommendations ──────────────────────────────────
function Top3Section({
  districts,
  selectedCode,
  onSelect,
  loading,
  industryName,
}: {
  districts: TopDistrict[];
  selectedCode: string;
  onSelect: (code: string) => void;
  loading: boolean;
  industryName: string;
}) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
        <p className="mt-3 text-sm text-slate-500">최적 상권을 분석하고 있습니다...</p>
      </div>
    );
  }

  if (districts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <AlertTriangle className="h-10 w-10 text-amber-400" />
        <p className="mt-3 text-sm text-slate-600">조건에 맞는 상권을 찾지 못했습니다</p>
        <Link href="/analyze" className="mt-3 text-sm font-semibold text-blue-600 hover:text-blue-700">
          조건 변경하기
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Trophy className="h-5 w-5 text-amber-500" />
        <h2 className="text-lg font-extrabold text-slate-900">AI 추천 TOP 3 상권</h2>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {districts.map((d, i) => {
          const verdict = getVerdictStyle(d.scorecard_total);
          const isSelected = d.district_code === selectedCode;
          return (
            <button
              key={d.district_code}
              onClick={() => onSelect(d.district_code)}
              className={cn(
                "relative rounded-xl border-2 p-4 text-left transition-all",
                isSelected
                  ? "border-blue-500 bg-blue-50/50 shadow-md shadow-blue-500/10"
                  : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm",
              )}
            >
              {/* Rank badge */}
              <div
                className={cn(
                  "absolute -top-2.5 left-3 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white",
                  i === 0 ? "bg-amber-500" : i === 1 ? "bg-slate-400" : "bg-amber-700",
                )}
              >
                {i + 1}
              </div>

              <div className="mb-2 flex items-start justify-between">
                <div>
                  <p className="text-sm font-bold text-slate-900">{d.district_name}</p>
                  <span className="text-xs text-slate-500">{d.district_type}</span>
                </div>
                <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold", verdict.bg, verdict.color)}>
                  {verdict.label}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] font-medium text-slate-500">AI 종합 점수</p>
                  <p className="text-sm font-extrabold text-slate-900">{d.scorecard_total}<span className="text-[10px] font-normal text-slate-400">/100</span></p>
                </div>
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] font-medium text-slate-500">2년 생존율</p>
                  <p className="text-sm font-extrabold text-slate-900">{(d.survival_rate * 100).toFixed(0)}%</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] font-medium text-slate-500">상권 전체 월 매출</p>
                  <p className="text-sm font-extrabold text-slate-900">{formatWon(d.monthly_sales)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] font-medium text-slate-500">{industryName} 점포 수</p>
                  <p className="text-sm font-extrabold text-slate-900">{d.store_count}개</p>
                </div>
              </div>

              {isSelected && (
                <div className="mt-2 text-center text-[10px] font-semibold text-blue-600">
                  선택됨 - 아래에서 상세 분석 확인
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Map visualization — always show */}
      <MiniMap
        markers={districts.map((d, i) => ({
          lat: d.coordinates?.lat || 37.5665,
          lng: d.coordinates?.lng || 126.9780,
          label: d.district_name,
          type: d.district_code === selectedCode ? ("selected" as const) : ("recommended" as const),
          rank: i + 1,
          successProbability: d.success_probability,
        }))}
        height={280}
        zoom={12}
      />
    </div>
  );
}

// ─── Section B1: Scorecard ───────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ScorecardSection({ data, loading, districtName, industryName }: { data: any; loading: boolean; districtName: string; industryName: string }) {
  if (loading) return <SectionSkeleton title="성공 점수" />;
  if (!data) return null;

  const categories = data.categories || [];
  const total = data.total_score ?? 0;
  const verdict = getVerdictStyle(total);
  const percentileValue = data.percentile != null ? Math.max(1, Math.round(100 - data.percentile)) : null;

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Target className="h-5 w-5 text-blue-500" />
        <h3 className="text-sm font-bold text-slate-900">B1. {districtName} 성공 점수</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[9px] font-semibold text-blue-600">
          <CreditCard className="h-2.5 w-2.5" />
          카드매출 기반
        </span>
      </div>

      <div className="mb-4 flex items-center gap-4">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50">
          <span className="text-2xl font-extrabold text-blue-600">{total}</span>
        </div>
        <div>
          <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-bold", verdict.bg, verdict.color)}>
            {verdict.label}
          </span>
          <p className="mt-1 text-xs text-slate-500">
            {percentileValue != null ? `서울 평균 대비 상위 ${percentileValue}%` : ""}
          </p>
        </div>
      </div>

      {/* Interpretation */}
      <div className="mb-4 rounded-lg bg-blue-50/50 p-3">
        <p className="text-xs leading-relaxed text-blue-800">
          이 점수는 서울시 {industryName} 전체 상권 중 {percentileValue != null ? `상위 ${percentileValue}%에 해당하며, ` : ""}매출·인구·경쟁·입지 4개 항목을 종합한 결과입니다.
        </p>
      </div>

      <div className="space-y-2">
        {categories.map(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (cat: any) => {
            const score = cat.score ?? 0;
            const pctWidth = Math.min(100, score);
            return (
              <div key={cat.name}>
                <div className="flex items-center gap-3">
                  <span className="w-16 text-xs font-medium text-slate-600">{cat.name}</span>
                  <div className="flex-1">
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all duration-500",
                          score >= 80 ? "bg-gradient-to-r from-emerald-400 to-emerald-500"
                            : score >= 60 ? "bg-gradient-to-r from-blue-400 to-indigo-500"
                            : score >= 40 ? "bg-gradient-to-r from-amber-400 to-orange-500"
                            : "bg-gradient-to-r from-rose-400 to-rose-500",
                        )}
                        style={{ width: `${pctWidth}%` }}
                      />
                    </div>
                  </div>
                  <span className={cn(
                    "w-12 text-right text-xs font-bold",
                    score >= 80 ? "text-emerald-700"
                      : score >= 60 ? "text-blue-700"
                      : score >= 40 ? "text-amber-700"
                      : "text-rose-700",
                  )}>
                    {score}점
                  </span>
                </div>
                <p className="ml-[76px] text-[10px] text-slate-400">{getScoreInterpretation(score)}</p>
              </div>
            );
          },
        )}
      </div>

      <DataSource text="서울시 상권분석서비스 종합" />
    </div>
  );
}

// ─── Section B2: Revenue Waterfall ─────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function RevenueSection({ data, loading, districtName, industryName }: { data: any; loading: boolean; districtName: string; industryName: string }) {
  if (loading) return <SectionSkeleton title="예상 수익 구조" />;
  if (!data) return null;

  const revenue = data.revenue || {};
  const operating = data.operating_cost || {};
  const breakEven = data.break_even || {};
  const assumptions = data.assumptions || {};
  const storeCount = revenue.store_count || data.store_count || 0;
  const areaPyeong = assumptions.area_pyeong || 15;
  const areaSummary = assumptions.summary || `${areaPyeong}평 기준`;

  const monthlySales = revenue.monthly_sales_per_store || 0;
  const netProfit = breakEven.monthly_net_profit || 0;
  const laborAmount = operating.labor || 0;
  const laborCount = laborAmount > 0 ? Math.round(laborAmount / 2_500_000) : 0;
  const cogsRatio = monthlySales > 0 ? Math.round((operating.cogs || 0) / monthlySales * 100) : 32;
  const utilitiesAmount = operating.utilities || 0;
  const otherAmount = operating.other || 0;

  const items = [
    { label: "월 매출", value: monthlySales, color: "bg-blue-500", type: "positive", desc: storeCount > 0 ? `${districtName} ${industryName} 전체 카드매출 ÷ 점포 ${storeCount}개` : "상권 카드매출 데이터 기반" },
    { label: "식재료비", value: -(operating.cogs || 0), color: "bg-orange-400", type: "negative", desc: `KREI 외식업체경영실태조사 기준 매출의 ${cogsRatio}%` },
    { label: "인건비", value: -laborAmount, color: "bg-amber-400", type: "negative", desc: laborCount > 0 ? `직원 ${laborCount}명 × 250만원 (급여+4대보험), KREI 실측 기반` : "KREI 외식업체경영실태조사 기반" },
    { label: "임대료", value: -(operating.rent || 0), color: "bg-rose-400", type: "negative", desc: `${districtName} 상권 등급·${areaPyeong}평 면적 기준 추정 월세` },
    { label: "기타비용", value: -(utilitiesAmount + otherAmount), color: "bg-slate-400", type: "negative", desc: `공과금(${formatWon(utilitiesAmount)}) + 잡비·소모품(${formatWon(otherAmount)})` },
    { label: "순이익", value: netProfit, color: netProfit >= 0 ? "bg-emerald-500" : "bg-rose-500", type: "result", desc: "매출 - 식재료비 - 인건비 - 임대료 - 기타비용" },
  ];

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-emerald-500" />
        <h3 className="text-sm font-bold text-slate-900">B2. {districtName} 예상 수익 구조</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[9px] font-semibold text-emerald-600">
          <CreditCard className="h-2.5 w-2.5" />
          카드매출 기반
        </span>
      </div>

      {/* Explanation box */}
      <div className="mb-4 rounded-lg bg-blue-50/50 p-3">
        <p className="text-xs leading-relaxed text-blue-800">
          <strong>{areaSummary}</strong> 기준 시뮬레이션입니다.
          서울시 공공데이터(카드매출)에서 {districtName} 상권의 {industryName} 실제 월평균 매출을 기반으로 산출했습니다.
          {storeCount > 0 && ` 점포당 매출은 해당 상권 내 같은 업종 가게 수(${storeCount}개)로 나누어 추정한 값입니다.`}
        </p>
      </div>

      {/* Waterfall visualization */}
      <div className="space-y-2">
        {items.map((item) => {
          const absValue = Math.abs(item.value);
          const pct = monthlySales > 0 ? (absValue / monthlySales) * 100 : 0;
          return (
            <div key={item.label}>
              <div className="flex items-center gap-3">
                <span className="w-16 text-xs font-medium text-slate-600">{item.label}</span>
                <div className="flex-1">
                  <div className="h-5 overflow-hidden rounded bg-slate-50">
                    <div
                      className={cn("h-full rounded transition-all duration-500", item.color)}
                      style={{ width: `${Math.min(100, pct)}%` }}
                    />
                  </div>
                </div>
                <span className={cn("w-20 text-right text-xs font-bold", item.value >= 0 ? "text-slate-700" : "text-rose-600")}>
                  {item.value >= 0 ? "" : "-"}{formatWon(absValue)}
                </span>
              </div>
              {item.desc && (
                <p className="ml-[76px] text-[10px] text-slate-400">({item.desc})</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Break-even */}
      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="rounded-xl bg-slate-50 p-3 text-center">
          <p className="text-[10px] text-slate-400">순이익률</p>
          <p className="text-sm font-extrabold text-slate-900">
            {((breakEven.net_profit_margin || 0) * 100).toFixed(1)}%
          </p>
          <p className="text-[9px] text-slate-400">순이익 ÷ 매출</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-3 text-center">
          <p className="text-[10px] text-slate-400">투자회수</p>
          <p className="text-sm font-extrabold text-slate-900">
            {breakEven.break_even_months_min || "-"}~{breakEven.break_even_months_max || "-"}개월
          </p>
          <p className="text-[9px] text-slate-400">초기투자 ÷ 월순이익</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-3 text-center">
          <p className="text-[10px] text-slate-400">일 손익분기</p>
          <p className="text-sm font-extrabold text-slate-900">
            {formatWon(breakEven.daily_break_even_sales || 0)}
          </p>
          <p className="text-[9px] text-slate-400">월 고정비 ÷ 30일</p>
        </div>
      </div>

      <a
        href="#section-c"
        className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700"
      >
        시뮬레이터로 조정해보기 <ChevronRight className="h-3 w-3" />
      </a>

      <DataSource text="서울시 카드매출 데이터 기반 추정" />
    </div>
  );
}

// ─── Section B3: Competition ───────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CompetitionSection({ data, loading, localdataData, localdataLoading, districtName, industryName }: { data: any; loading: boolean; localdataData?: any; localdataLoading?: boolean; districtName: string; industryName: string }) {
  if (loading) return <SectionSkeleton title="경쟁 환경" />;
  if (!data) return null;

  const stores = data.stores || {};
  const storeCount = stores.store_count || stores.total || 0;
  const newStores = stores.new_stores || 0;
  const closedStores = stores.closed_stores || 0;
  const franchiseStores = stores.franchise_stores || 0;
  const franchiseRatio = storeCount > 0 ? ((franchiseStores / storeCount) * 100).toFixed(0) : "0";
  const netGrowth = newStores - closedStores;

  const strategyText = netGrowth > 0
    ? "신규 진입이 활발한 상권입니다. 차별화 전략이 중요합니다."
    : netGrowth < 0
      ? "폐업이 신규 개업보다 많아 경쟁이 줄어드는 추세입니다."
      : "점포 수가 안정적으로 유지되고 있습니다.";

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Store className="h-5 w-5 text-purple-500" />
        <h3 className="text-sm font-bold text-slate-900">B3. {districtName} 경쟁 환경</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-purple-50 px-2 py-0.5 text-[9px] font-semibold text-purple-600">
          LOCALDATA + 카드매출
        </span>
      </div>

      {/* Interpretation */}
      <div className="mb-4 rounded-lg bg-purple-50/50 p-3">
        <p className="text-xs leading-relaxed text-purple-800">
          현재 {districtName}에는 {industryName} 점포 {storeCount}개가 영업 중입니다. {strategyText}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 text-center">
          <p className="text-[10px] text-slate-400">총 점포</p>
          <p className="text-lg font-extrabold text-slate-900">{storeCount}개</p>
        </div>
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 text-center">
          <p className="text-[10px] text-slate-400">순증감</p>
          <div className="flex items-center justify-center gap-1">
            {netGrowth > 0 ? (
              <ArrowUp className="h-3 w-3 text-emerald-500" />
            ) : netGrowth < 0 ? (
              <ArrowDown className="h-3 w-3 text-rose-500" />
            ) : (
              <Minus className="h-3 w-3 text-slate-400" />
            )}
            <p className={cn("text-lg font-extrabold", netGrowth > 0 ? "text-emerald-600" : netGrowth < 0 ? "text-rose-600" : "text-slate-700")}>
              {netGrowth > 0 ? "+" : ""}{netGrowth}
            </p>
          </div>
        </div>
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 text-center">
          <p className="text-[10px] text-slate-400">프랜차이즈</p>
          <p className="text-lg font-extrabold text-slate-900">{franchiseRatio}%</p>
        </div>
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 text-center">
          <p className="text-[10px] text-slate-400">신규/폐업</p>
          <p className="text-sm font-extrabold text-slate-900">
            <span className="text-emerald-600">+{newStores}</span>
            <span className="mx-1 text-slate-300">/</span>
            <span className="text-rose-600">-{closedStores}</span>
          </p>
        </div>
      </div>

      {/* LOCALDATA Competition Map */}
      <CompetitionMap data={localdataData} loading={localdataLoading || false} />

      <DataSource text="서울시 상권분석서비스 + 네이버 지도" />
    </div>
  );
}

// ─── Section B5: Customer Analysis ─────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomerSection({ data, loading, districtName, industryName }: { data: any; loading: boolean; districtName: string; industryName: string }) {
  if (loading) return <SectionSkeleton title="고객 분석" />;
  if (!data) return null;

  const breakdown = data.breakdown || {};
  const byAge = breakdown.by_age || {};
  const byTime = breakdown.by_time || {};
  const byGender = breakdown.by_gender || {};
  const byDay = breakdown.by_day || {};

  const ageLabels: Record<string, string> = {
    "10s": "10대", "20s": "20대", "30s": "30대", "40s": "40대", "50s": "50대", "60s_plus": "60+",
  };
  const timeLabels: Record<string, string> = {
    "00_06": "0~6시", "06_11": "6~11시", "11_14": "11~14시", "14_17": "14~17시", "17_21": "17~21시", "21_24": "21~24시",
  };
  const dayLabels: Record<string, string> = {
    mon: "월", tue: "화", wed: "수", thu: "목", fri: "금", sat: "토", sun: "일",
  };

  // Find peak time
  const peakTimeEntry = Object.entries(byTime).sort(([, a], [, b]) => (b as number) - (a as number))[0];
  const peakTimeLabel = peakTimeEntry ? timeLabels[peakTimeEntry[0]] || peakTimeEntry[0] : null;

  // Find peak day
  const peakDayEntry = Object.entries(byDay).sort(([, a], [, b]) => (b as number) - (a as number))[0];
  const peakDayLabel = peakDayEntry ? dayLabels[peakDayEntry[0]] || peakDayEntry[0] : null;

  // Calculate quarter count from data
  const quarterCount = data.quarter_count || data.quarters?.length || 0;

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Users className="h-5 w-5 text-cyan-500" />
        <h3 className="text-sm font-bold text-slate-900">B5. {districtName} 고객 분석</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-cyan-50 px-2 py-0.5 text-[9px] font-semibold text-cyan-600">
          <CreditCard className="h-2.5 w-2.5" />
          {quarterCount > 0 ? `최근 ${quarterCount}분기` : "분기별 카드매출"}
        </span>
      </div>

      {/* Interpretation */}
      <div className="mb-4 rounded-lg bg-cyan-50/50 p-3">
        <p className="text-xs leading-relaxed text-cyan-800">
          {districtName} 상권에서 {industryName} 업종의 카드 결제 데이터를 분석한 결과입니다.
          {peakTimeLabel && ` 피크 시간대는 ${peakTimeLabel}입니다.`}
          {peakDayLabel && ` 가장 매출이 높은 요일은 ${peakDayLabel}요일입니다.`}
        </p>
      </div>

      {/* Gender */}
      <div className="mb-4">
        <p className="mb-2 text-xs font-semibold text-slate-500">성별</p>
        <div className="flex h-4 overflow-hidden rounded-full">
          <div className="bg-blue-400" style={{ width: `${byGender.male_pct || 50}%` }} />
          <div className="bg-pink-400" style={{ width: `${byGender.female_pct || 50}%` }} />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-slate-500">
          <span>남성 {byGender.male_pct || 50}%</span>
          <span>여성 {byGender.female_pct || 50}%</span>
        </div>
      </div>

      {/* Age distribution */}
      <div className="mb-4">
        <p className="mb-2 text-xs font-semibold text-slate-500">연령대별 매출 비중</p>
        <div className="flex items-end gap-1">
          {Object.entries(ageLabels).map(([key, label]) => {
            const pct = byAge[key] || 0;
            return (
              <div key={key} className="flex-1 text-center">
                <div className="mx-auto w-full overflow-hidden rounded-t bg-slate-100" style={{ height: "60px" }}>
                  <div
                    className="w-full rounded-t bg-gradient-to-t from-cyan-500 to-cyan-400 transition-all duration-500"
                    style={{ height: `${pct}%`, marginTop: `${100 - pct}%` }}
                  />
                </div>
                <p className="mt-1 text-[9px] font-medium text-slate-500">{label}</p>
                <p className="text-[10px] font-bold text-slate-700">{pct}%</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Time distribution */}
      <div className="mb-4">
        <p className="mb-2 text-xs font-semibold text-slate-500">시간대별 매출 비중</p>
        <div className="flex items-end gap-1">
          {Object.entries(timeLabels).map(([key, label]) => {
            const pct = byTime[key] || 0;
            return (
              <div key={key} className="flex-1 text-center">
                <div className="mx-auto w-full overflow-hidden rounded-t bg-slate-100" style={{ height: "60px" }}>
                  <div
                    className="w-full rounded-t bg-gradient-to-t from-indigo-500 to-indigo-400 transition-all duration-500"
                    style={{ height: `${pct}%`, marginTop: `${100 - pct}%` }}
                  />
                </div>
                <p className="mt-1 text-[8px] font-medium text-slate-500">{label}</p>
                <p className="text-[10px] font-bold text-slate-700">{pct}%</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Day distribution (if data exists) */}
      {Object.keys(byDay).length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold text-slate-500">요일별 매출 비중</p>
          <div className="flex items-end gap-1">
            {Object.entries(dayLabels).map(([key, label]) => {
              const pct = byDay[key] || 0;
              return (
                <div key={key} className="flex-1 text-center">
                  <div className="mx-auto w-full overflow-hidden rounded-t bg-slate-100" style={{ height: "50px" }}>
                    <div
                      className="w-full rounded-t bg-gradient-to-t from-violet-500 to-violet-400 transition-all duration-500"
                      style={{ height: `${pct}%`, marginTop: `${100 - pct}%` }}
                    />
                  </div>
                  <p className="mt-1 text-[9px] font-medium text-slate-500">{label}</p>
                  <p className="text-[10px] font-bold text-slate-700">{pct}%</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <DataSource text="서울시 카드매출 데이터" />
    </div>
  );
}

// ─── Section B7: Franchise Comparison ──────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function FranchiseSection({ data, loading, industryName }: { data: any; loading: boolean; industryName: string }) {
  if (loading) return <SectionSkeleton title="프랜차이즈 현황" />;
  if (!data) return null;

  const brands = data.brands || data.top_brands || [];
  const startupCosts = data.startup_costs || [];
  const industryStatus = data.industry_status || [];
  const hasData = brands.length > 0 || startupCosts.length > 0;

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Building2 className="h-5 w-5 text-orange-500" />
        <h3 className="text-sm font-bold text-slate-900">B7. {industryName} 프랜차이즈 현황</h3>
      </div>

      {hasData ? (
        <div className="space-y-2">
          <div className="rounded-lg bg-orange-50/50 p-2">
            <p className="text-[10px] leading-relaxed text-orange-700">
              아래 금액은 공정거래위원회 정보공개서 기준 <strong>가맹 가입비</strong>만 포함합니다.
              실제 총 창업비용은 인테리어·보증금·장비비 등이 추가되어 훨씬 높습니다.
              (비용비교 페이지에서 총 비용을 확인하세요)
            </p>
          </div>
          {/* 공정위 startup_costs 데이터 */}
          {startupCosts.length > 0 && startupCosts.map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (item: any, i: number) => {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const status = industryStatus.find((s: any) => s.name === item.name);
              return (
                <div key={i} className="rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-900">{item.name}</p>
                    <span className="text-xs font-bold text-slate-700">
                      가맹 가입비 {formatWon(item.total_joining_cost || 0)}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-3 text-[10px] text-slate-500">
                    <span>가맹비 {formatWon(item.franchise_fee || 0)}</span>
                    <span>교육비 {formatWon(item.education_fee || 0)}</span>
                    <span>기타 {formatWon(item.other_fee || 0)}</span>
                  </div>
                  {status && (
                    <div className="mt-1 flex flex-wrap gap-x-3 text-[10px] text-slate-500">
                      <span>브랜드 {status.brand_count}개</span>
                      <span>가맹점 {(status.store_count || 0).toLocaleString()}개</span>
                      <span>폐점 {(status.closed_store_count || 0).toLocaleString()}개</span>
                    </div>
                  )}
                </div>
              );
            },
          )}
          {/* Legacy brands format */}
          {brands.length > 0 && brands.slice(0, 5).map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (brand: any, i: number) => (
              <div key={`b-${i}`} className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-2">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{brand.brand_name || brand.name}</p>
                  <p className="text-[10px] text-slate-500">
                    가맹비 {formatWon(brand.franchise_fee || brand.initial_cost || 0)}
                    {brand.store_count ? ` / ${brand.store_count}개 매장` : ""}
                  </p>
                </div>
                {brand.avg_monthly_sales && (
                  <span className="text-xs font-bold text-slate-700">
                    월매출 {formatWon(brand.avg_monthly_sales)}
                  </span>
                )}
              </div>
            ),
          )}
          {data.avg_total_startup_cost && (
            <div className="mt-2 rounded-lg bg-orange-50 p-2 text-center">
              <p className="text-[10px] text-orange-500">업종 평균 가맹 가입비</p>
              <p className="text-sm font-extrabold text-orange-700">{formatWon(data.avg_total_startup_cost)}</p>
              <p className="text-[9px] text-orange-400">가맹비+교육비+기타 합산 (인테리어·보증금·장비 별도)</p>
            </div>
          )}
        </div>
      ) : (
        <div className="rounded-lg bg-orange-50/50 p-4 text-center">
          <p className="text-sm text-slate-500">이 업종의 프랜차이즈 데이터가 아직 없습니다.</p>
          <p className="mt-1 text-xs text-slate-400">독립창업 기준으로 비용을 산정합니다.</p>
        </div>
      )}

      <DataSource text={`공정거래위원회 가맹사업 정보 (${data.year || "2024"})`} />
    </div>
  );
}

// ─── Section C: Inline Simulator ───────────────────────────────────────
function InlineSimulatorSection({
  defaults,
  loading,
  districtName,
}: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  defaults: any;
  loading: boolean;
  districtName: string;
}) {
  const [salesMultiplier, setSalesMultiplier] = useState(1.0);
  const [rentMultiplier, setRentMultiplier] = useState(1.0);
  const [laborMultiplier, setLaborMultiplier] = useState(1.0);

  if (loading) return <SectionSkeleton title="수익 시뮬레이터" />;
  if (!defaults) return null;

  const baseSales = defaults.revenue?.monthly_sales_per_store || 0;
  const baseRent = defaults.operating_cost?.rent || 0;
  const baseLabor = defaults.operating_cost?.labor || 0;
  const baseCogs = defaults.operating_cost?.cogs || 0;
  const baseOther = (defaults.operating_cost?.utilities || 0) + (defaults.operating_cost?.other || 0);

  const adjustedSales = Math.round(baseSales * salesMultiplier);
  const adjustedRent = Math.round(baseRent * rentMultiplier);
  const adjustedLabor = Math.round(baseLabor * laborMultiplier);
  const totalCost = baseCogs + adjustedRent + adjustedLabor + baseOther;
  const adjustedProfit = adjustedSales - totalCost;

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <SlidersHorizontal className="h-5 w-5 text-indigo-500" />
        <h3 className="text-sm font-bold text-slate-900">C. {districtName} 수익 시뮬레이터</h3>
      </div>

      {/* Description */}
      <div className="mb-4 rounded-lg bg-indigo-50/50 p-3">
        <p className="text-xs leading-relaxed text-indigo-800">
          임대료, 인건비, 매출을 조정하면 예상 월 수익이 실시간으로 바뀝니다. 슬라이더를 움직여 다양한 시나리오를 확인해보세요.
        </p>
      </div>

      <div className="space-y-4">
        {/* Sales slider */}
        <div>
          <label className="mb-1 flex items-center justify-between text-xs text-slate-500">
            <span>매출 조정</span>
            <span className="font-bold text-slate-700">{(salesMultiplier * 100).toFixed(0)}% ({formatWon(adjustedSales)})</span>
          </label>
          <input
            type="range"
            min={0.5}
            max={1.5}
            step={0.05}
            value={salesMultiplier}
            onChange={(e) => setSalesMultiplier(parseFloat(e.target.value))}
            className="w-full accent-indigo-600"
          />
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>-50%</span>
            <span>기본</span>
            <span>+50%</span>
          </div>
        </div>

        {/* Rent slider */}
        <div>
          <label className="mb-1 flex items-center justify-between text-xs text-slate-500">
            <span>월 임대료 <span className="text-[10px] text-slate-400">(예상 월세, 보증금 별도)</span></span>
            <span className="font-bold text-slate-700">{formatWon(adjustedRent)}</span>
          </label>
          <input
            type="range"
            min={0.5}
            max={2.0}
            step={0.1}
            value={rentMultiplier}
            onChange={(e) => setRentMultiplier(parseFloat(e.target.value))}
            className="w-full accent-rose-500"
          />
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>-50%</span>
            <span>기본</span>
            <span>+100%</span>
          </div>
        </div>

        {/* Labor slider */}
        <div>
          <label className="mb-1 flex items-center justify-between text-xs text-slate-500">
            <span>인건비 <span className="text-[10px] text-slate-400">(직원 급여 + 4대보험)</span></span>
            <span className="font-bold text-slate-700">{formatWon(adjustedLabor)}</span>
          </label>
          <input
            type="range"
            min={0.5}
            max={2.0}
            step={0.1}
            value={laborMultiplier}
            onChange={(e) => setLaborMultiplier(parseFloat(e.target.value))}
            className="w-full accent-amber-500"
          />
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>-50%</span>
            <span>기본</span>
            <span>+100%</span>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className="rounded-xl bg-blue-50 p-3 text-center">
          <p className="text-[10px] text-blue-500">조정 매출</p>
          <p className="text-sm font-extrabold text-blue-700">{formatWon(adjustedSales)}</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-3 text-center">
          <p className="text-[10px] text-slate-500">총 비용</p>
          <p className="text-sm font-extrabold text-slate-700">{formatWon(totalCost)}</p>
        </div>
        <div className={cn("rounded-xl p-3 text-center", adjustedProfit >= 0 ? "bg-emerald-50" : "bg-rose-50")}>
          <p className={cn("text-[10px]", adjustedProfit >= 0 ? "text-emerald-500" : "text-rose-500")}>순이익</p>
          <p className={cn("text-sm font-extrabold", adjustedProfit >= 0 ? "text-emerald-700" : "text-rose-700")}>
            {adjustedProfit < 0 ? "-" : ""}{formatWon(Math.abs(adjustedProfit))}
          </p>
        </div>
      </div>

      <p className="mt-4 text-[10px] text-slate-400">
        순이익 = 매출 - 임대료 - 인건비 - 재료비(매출의 약 35%)
      </p>
    </div>
  );
}

// ─── Section D: Risk & Opportunity ─────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function RiskSection({ data, loading, districtName }: { data: any; loading: boolean; districtName: string }) {
  const [riskExpanded, setRiskExpanded] = useState(false);
  const [oppExpanded, setOppExpanded] = useState(false);

  if (loading) return <SectionSkeleton title="리스크 & 기회" />;
  if (!data) return null;

  const sections = data.sections || data.analysis?.sections || [];

  // Flat-field fallback: API may return verdict_summary, risk_comment etc instead of sections[]
  const riskContent = data.risk_comment || data.competition_comment || "";
  const oppContent = data.verdict_summary || data.profitability_comment || "";
  const customerNote = data.customer_comment || "";

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const riskSection = sections.find((s: any) =>
    s.title?.includes("리스크") || s.title?.includes("위험") || s.title?.includes("약점") || s.title?.includes("threat") || s.title?.includes("risk")
  );
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const oppSection = sections.find((s: any) =>
    s.title?.includes("기회") || s.title?.includes("강점") || s.title?.includes("장점") || s.title?.includes("opportunity") || s.title?.includes("strength")
  );

  const displayRiskText = riskSection?.content || riskContent;
  const displayOppText = oppSection?.content || oppContent;
  const hasContent = displayRiskText || displayOppText || customerNote;

  const COLLAPSE_THRESHOLD = 500;

  const renderCollapsibleText = (text: string, expanded: boolean, setExpanded: (v: boolean) => void, colorClass: string) => {
    const needsCollapse = text.length > COLLAPSE_THRESHOLD;
    const displayText = !needsCollapse || expanded ? text : text;
    return (
      <div>
        <p className={cn("text-xs leading-relaxed", colorClass)}>
          {displayText}
        </p>
        {needsCollapse && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-1 flex items-center gap-0.5 text-[10px] font-semibold text-slate-500 hover:text-slate-700"
          >
            {expanded ? "접기" : "더 보기"}
            <ChevronDown className={cn("h-3 w-3 transition-transform", expanded && "rotate-180")} />
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-amber-500" />
        <h3 className="text-sm font-bold text-slate-900">D. {districtName} 리스크 & 기회 분석</h3>
      </div>

      {/* Preamble */}
      <div className="mb-4 rounded-lg bg-amber-50/50 p-3">
        <p className="text-xs leading-relaxed text-amber-800">
          AI가 {districtName} 상권의 잠재적 위험 요소와 기회 요인을 분석했습니다.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {/* Risk */}
        <div className="rounded-xl border border-rose-100 bg-rose-50/30 p-4">
          <p className="mb-2 text-xs font-bold text-rose-700">{riskSection?.title || "주요 리스크"}</p>
          {displayRiskText ? (
            renderCollapsibleText(displayRiskText, riskExpanded, setRiskExpanded, "text-rose-900/80")
          ) : (
            <p className="text-xs text-rose-500">해당 상권의 특이 리스크 분석 중입니다</p>
          )}
        </div>

        {/* Opportunity */}
        <div className="rounded-xl border border-emerald-100 bg-emerald-50/30 p-4">
          <p className="mb-2 text-xs font-bold text-emerald-700">{oppSection?.title || "주요 기회"}</p>
          {displayOppText ? (
            renderCollapsibleText(displayOppText, oppExpanded, setOppExpanded, "text-emerald-900/80")
          ) : (
            <p className="text-xs text-emerald-500">기회 요인을 탐색 중입니다</p>
          )}
        </div>
      </div>

      {/* Customer note */}
      {customerNote && (
        <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50/30 p-3">
          <p className="mb-1 text-xs font-bold text-blue-700">고객 분석 인사이트</p>
          <p className="text-xs leading-relaxed text-blue-900/80">{customerNote}</p>
        </div>
      )}

      {hasContent && <DataSource text="AI 종합 분석" />}
    </div>
  );
}

// ─── Section E: Support Programs ───────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function SupportSection({ data, loading, industryCode, industryName }: { data: any; loading: boolean; industryCode: string; industryName: string }) {
  if (loading) return <SectionSkeleton title="지원금 매칭" />;
  if (!data) return null;

  const programs = data.programs || data.matched_programs || [];

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Gift className="h-5 w-5 text-green-500" />
        <h3 className="text-sm font-bold text-slate-900">E. {industryName} 창업 지원금</h3>
        {programs.length > 0 && (
          <span className="rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-bold text-green-700">
            {programs.length}건
          </span>
        )}
      </div>

      {/* Interpretation */}
      <div className="mb-4 rounded-lg bg-green-50/50 p-3">
        <p className="text-xs leading-relaxed text-green-800">
          현재 신청 가능한 정부·지자체 창업 지원 프로그램입니다. 대부분의 지원금은 사업계획서 제출이 필수입니다.
        </p>
      </div>

      {programs.length > 0 ? (
        <div className="space-y-2">
          {programs.slice(0, 3).map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (prog: any, i: number) => (
              <div key={i} className="rounded-lg border border-slate-100 bg-slate-50/50 p-3">
                <p className="text-xs font-semibold text-slate-900">{prog.program_name || prog.name}</p>
                <p className="mt-0.5 text-[10px] text-slate-500">{prog.managing_org || prog.organization || ""}</p>
                {prog.max_amount_man > 0 && (
                  <p className="mt-1 text-xs font-bold text-green-700">
                    최대 {prog.max_amount_man >= 10000 ? `${(prog.max_amount_man / 10000).toFixed(1)}억원` : `${prog.max_amount_man.toLocaleString()}만원`}
                  </p>
                )}
                {prog.support_amount && !prog.max_amount_man && (
                  <p className="mt-1 text-xs font-bold text-green-700">
                    {prog.support_amount}
                  </p>
                )}
                {prog.deadline && (
                  <p className="mt-1 text-[10px] font-semibold text-rose-600">
                    신청 마감: {prog.deadline}
                  </p>
                )}
              </div>
            ),
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-500">매칭 가능한 지원 프로그램이 없습니다</p>
      )}

      <Link
        href={`/support?industry_code=${industryCode}`}
        className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700"
      >
        전체 지원금 보기 <ChevronRight className="h-3 w-3" />
      </Link>

      <DataSource text="중소벤처기업부 비즈인포" />
    </div>
  );
}

// ─── Main Report Page ──────────────────────────────────────────────────
function ReportContent() {
  const searchParams = useSearchParams();
  const store = useAnalyzeStore();

  const industryCode = searchParams?.get("industry_code") || store.industryCode;
  const budget = Number(searchParams?.get("budget")) || Number(searchParams?.get("budget_max")) || store.budget;
  const industryName = store.industryName || "카페";

  const [top3Loading, setTop3Loading] = useState(true);
  const [topDistricts, setTopDistricts] = useState<TopDistrict[]>([]);
  const [selectedCode, setSelectedCode] = useState("");

  // Section data states
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [scorecardData, setScorecardData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [simulationData, setSimulationData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [competitionData, setCompetitionData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [customerData, setCustomerData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [franchiseData, setFranchiseData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [riskData, setRiskData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [supportData, setSupportData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [locationData, setLocationData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [rentData, setRentData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars
  const [localdataData, setLocaldataData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [salesTrendData, setSalesTrendData] = useState<any>(null);

  // Section loading states
  const [scorecardLoading, setScorecardLoading] = useState(false);
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [competitionLoading, setCompetitionLoading] = useState(false);
  const [customerLoading, setCustomerLoading] = useState(false);
  const [franchiseLoading, setFranchiseLoading] = useState(false);
  const [riskLoading, setRiskLoading] = useState(false);
  const [supportLoading, setSupportLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);
  const [rentLoading, setRentLoading] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [localdataLoading, setLocaldataLoading] = useState(false);
  const [salesTrendLoading, setSalesTrendLoading] = useState(false);

  // Phase 1: Fetch TOP 3
  useEffect(() => {
    const fetchTop3 = async () => {
      setTop3Loading(true);
      try {
        const params = new URLSearchParams({
          industry_code: industryCode,
          budget_max: String(budget),
          limit: "3",
        });
        const res = await fetch(`${API_BASE}/recommendations/dashboard?${params}`);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        const results = (data.results || []).map(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (r: any) => ({
            district_code: r.district_code,
            district_name: r.district_name,
            district_type: r.district_type,
            success_probability: r.success_probability,
            estimated_rent: r.estimated_rent,
            monthly_sales: r.monthly_sales,
            store_count: r.store_count,
            survival_rate: r.survival_rate,
            scorecard_total: r.scorecard_total,
            key_factors: r.key_factors || [],
            coordinates: typeof r.lat === "number" && typeof r.lng === "number" && !(r.lat === 0 && r.lng === 0)
              ? { lat: r.lat, lng: r.lng }
              : undefined,
          }),
        );
        setTopDistricts(results);
        store.setTopDistricts(results);
        if (results.length > 0) {
          setSelectedCode(results[0].district_code);
          store.setSelectedDistrict(results[0].district_code);
        }
      } catch (err) {
        console.error("Failed to fetch TOP 3:", err);
      } finally {
        setTop3Loading(false);
      }
    };
    fetchTop3();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [industryCode, budget]);

  // Phase 2: Fetch section data when district changes
  const fetchSectionData = useCallback(
    async (districtCode: string) => {
      if (!districtCode) return;

      // Check cache
      const cached = store.sectionData[districtCode];
      const selectedDist = store.topDistricts.find((d) => d.district_code === districtCode);
      const distName = selectedDist?.district_name || "";

      // B1: Scorecard
      if (!cached?.scorecard) {
        setScorecardLoading(true);
        fetch(`${API_BASE}/scorecard/${industryCode}/${districtCode}`)
          .then((r) => r.json())
          .then((data) => {
            setScorecardData({ ...data, district_code: districtCode, industry_code: industryCode });
            store.setSectionData(districtCode, "scorecard", data);
          })
          .catch((err) => { console.error("API error:", err); })
          .finally(() => setScorecardLoading(false));
      } else {
        setScorecardData({ ...cached.scorecard, district_code: districtCode, industry_code: industryCode });
      }

      // B2: Simulation
      if (!cached?.simulation) {
        setSimulationLoading(true);
        fetch(`${API_BASE}/simulation/simulate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            district_code: districtCode,
            industry_code: industryCode,
            area_pyeong: 15,
            interior_grade: "mid",
          }),
        })
          .then((r) => r.json())
          .then((data) => {
            setSimulationData({ ...data, district_code: districtCode, industry_code: industryCode });
            store.setSectionData(districtCode, "simulation", data);
          })
          .catch((err) => { console.error("API error:", err); })
          .finally(() => setSimulationLoading(false));
      } else {
        setSimulationData({ ...cached.simulation, district_code: districtCode, industry_code: industryCode });
      }

      // B3: Competition (stores data + competitive analysis with query param)
      if (!cached?.competition) {
        setCompetitionLoading(true);
        fetch(`${API_BASE}/explore/stores?district_code=${districtCode}&industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            const storesInfo = {
              stores: data,
              store_count: data.store_count || data.total || 0,
              new_stores: 0,
              closed_stores: 0,
              franchise_stores: 0,
            };
            // Get from competitive analysis — include query param
            const query = encodeURIComponent(`${distName} ${industryName}`);
            return fetch(`${API_BASE}/competitive/analyze?district_code=${districtCode}&industry_code=${industryCode}&query=${query}`)
              .then((r2) => r2.json())
              .then((comp) => {
                const merged = { stores: { ...storesInfo, ...comp } };
                setCompetitionData(merged);
                store.setSectionData(districtCode, "competition", merged);
              })
              .catch(() => {
                setCompetitionData({ stores: storesInfo });
                store.setSectionData(districtCode, "competition", { stores: storesInfo });
              });
          })
          .catch((err) => { console.error("API error:", err); })
          .finally(() => setCompetitionLoading(false));
      } else {
        setCompetitionData(cached.competition);
      }

      // B5: Customer (sales breakdown)
      if (!cached?.customer) {
        setCustomerLoading(true);
        fetch(`${API_BASE}/explore/sales-breakdown?district_code=${districtCode}&industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            setCustomerData(data);
            store.setSectionData(districtCode, "customer", data);
          })
          .catch((err) => { console.error("API error:", err); })
          .finally(() => setCustomerLoading(false));
      } else {
        setCustomerData(cached.customer);
      }

      // B7: Franchise
      if (!cached?.franchise) {
        setFranchiseLoading(true);
        fetch(`${API_BASE}/franchise/benchmark/${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            setFranchiseData(data);
            store.setSectionData(districtCode, "franchise", data);
          })
          .catch((err) => { console.error("API error:", err); })
          .finally(() => setFranchiseLoading(false));
      } else {
        setFranchiseData(cached.franchise);
      }

      // D: Risk (AI analysis)
      if (!cached?.risk) {
        setRiskLoading(true);
        fetch(`${API_BASE}/districts/${districtCode}/analysis?industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            setRiskData(data);
            store.setSectionData(districtCode, "risk", data);
          })
          .catch((err) => { console.error("API error:", err); })
          .finally(() => setRiskLoading(false));
      } else {
        setRiskData(cached.risk);
      }

      // E: Support — include district name + budget for filtering
      if (!cached?.support) {
        setSupportLoading(true);
        const districtParam = distName ? `&district=${encodeURIComponent(distName)}` : "";
        const budgetParam = budget > 0 ? `&budget_max=${Math.round(budget * 10000)}` : "";
        fetch(`${API_BASE}/support/programs?industry_code=${industryCode}${districtParam}${budgetParam}`)
          .then((r) => r.json())
          .then((data) => {
            setSupportData(data);
            store.setSectionData(districtCode, "support", data);
          })
          .catch((err) => { console.error("API error:", err); })
          .finally(() => setSupportLoading(false));
      } else {
        setSupportData(cached.support);
      }

      // B4: Location Profile
      if (!cached?.location) {
        setLocationLoading(true);
        fetch(`${API_BASE}/location/profile?district_code=${districtCode}&industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            setLocationData(data);
            store.setSectionData(districtCode, "location", data);
          })
          .catch((err) => { console.error("API error:", err); })
          .finally(() => setLocationLoading(false));
      } else {
        setLocationData(cached.location);
      }

      // B6: Rent Trend
      if (!cached?.rent) {
        setRentLoading(true);
        fetch(`${API_BASE}/kosis/rent-trend?district_code=${districtCode}`)
          .then((r) => r.json())
          .then((data) => {
            setRentData(data);
            store.setSectionData(districtCode, "rent", data);
          })
          .catch((err) => { console.error("API error:", err); })
          .finally(() => setRentLoading(false));
      } else {
        setRentData(cached.rent);
      }

      // Sales Trend
      if (!cached?.salesTrend) {
        setSalesTrendLoading(true);
        fetch(`${API_BASE}/explore/sales-trend?district_code=${districtCode}&industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            setSalesTrendData(data);
            store.setSectionData(districtCode, "salesTrend", data);
          })
          .catch((err) => { console.error("API error:", err); })
          .finally(() => setSalesTrendLoading(false));
      } else {
        setSalesTrendData(cached.salesTrend);
      }

      // B3 enhanced: LOCALDATA competition
      if (!cached?.localdata) {
        setLocaldataLoading(true);
        // Get coordinates from top districts
        const district = store.topDistricts.find((d) => d.district_code === districtCode);
        if (district?.coordinates) {
          fetch(
            `${API_BASE}/explore/stores?district_code=${districtCode}&industry_code=${industryCode}`,
          )
            .then((r) => r.json())
            .then((data) => {
              setLocaldataData(data);
              store.setSectionData(districtCode, "localdata", data);
            })
            .catch((err) => { console.error("API error:", err); })
            .finally(() => setLocaldataLoading(false));
        } else {
          setLocaldataLoading(false);
        }
      } else {
        setLocaldataData(cached.localdata);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [industryCode, industryName],
  );

  useEffect(() => {
    if (selectedCode) {
      fetchSectionData(selectedCode);
    }
  }, [selectedCode, fetchSectionData]);

  const handleDistrictSelect = (code: string) => {
    setSelectedCode(code);
    store.setSelectedDistrict(code);
  };

  const selectedDistrict = topDistricts.find((d) => d.district_code === selectedCode);
  const districtName = selectedDistrict?.district_name || "";

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
            className="text-sm font-medium text-slate-500 hover:text-slate-700"
          >
            다시 분석하기
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 pb-20 pt-8 sm:px-6">
        {/* Stepper */}
        <AnalyzeStepper currentStep={2} className="mb-8" />

        {/* Title */}
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-extrabold text-slate-900 sm:text-3xl">
            {store.industryIcon || "🍽️"} {industryName} 창업 분석 리포트
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            예산 {budget.toLocaleString()}만원 · 서울 1,077개 상권 중 AI 추천 TOP 3
          </p>
        </div>

        {/* Section A: TOP 3 */}
        <div id="section-top3" className="mb-6 rounded-2xl border border-slate-200 bg-white p-6">
          <Top3Section
            districts={topDistricts}
            selectedCode={selectedCode}
            onSelect={handleDistrictSelect}
            loading={top3Loading}
            industryName={industryName}
          />
        </div>

        {/* Context Bar: district + industry + budget */}
        {selectedDistrict && (
          <div className="mb-4 rounded-xl border border-blue-100 bg-blue-50/50 px-4 py-3">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-blue-500" />
                <p className="text-sm font-extrabold text-blue-900">{districtName}</p>
              </div>
              <div className="flex flex-wrap items-center gap-x-3 text-xs text-blue-700">
                <span>상권: {districtName} ({selectedDistrict.district_type})</span>
                <span className="text-blue-300">|</span>
                <span>업종: {industryName}</span>
                <span className="text-blue-300">|</span>
                <span>예산: {budget.toLocaleString()}만원</span>
              </div>
            </div>
          </div>
        )}

        {/* AI Briefing + Risk Alert */}
        {selectedCode && (
          <div className="mb-4 space-y-3">
            <BriefingCard districtCode={selectedCode} industryCode={industryCode} />
            <RiskAlertBanner districtCode={selectedCode} industryCode={industryCode} />
          </div>
        )}

        {/* Report sections B~E — Corrected order: B1+B2, B3+B4, B5+B6, Trends, B7, C, D+E */}
        {selectedCode && (
          <div className="space-y-4">
            {/* Row 1: B1 + B2 */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div id="section-b1">
                <ProGateSection feature="detailed_scorecard">
                  <ScorecardSection data={scorecardData} loading={scorecardLoading} districtName={districtName} industryName={industryName} />
                </ProGateSection>
              </div>
              <div id="section-b2">
                <ProGateSection feature="revenue_waterfall">
                  <RevenueSection data={simulationData} loading={simulationLoading} districtName={districtName} industryName={industryName} />
                </ProGateSection>
              </div>
            </div>

            {/* Row 2: B3 (경쟁 환경) + B4 (입지 분석) */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div id="section-b3">
                <ProGateSection feature="competition_map">
                  <CompetitionSection data={competitionData} loading={competitionLoading} localdataData={localdataData} localdataLoading={localdataLoading} districtName={districtName} industryName={industryName} />
                </ProGateSection>
              </div>
              <div id="section-b4">
                <ProGateSection feature="location_profile">
                  <LocationProfile data={locationData} loading={locationLoading} districtName={districtName} />
                </ProGateSection>
              </div>
            </div>

            {/* Row 3: B5 (고객 분석) + B6 (임대료 트렌드) */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div id="section-b5">
                <ProGateSection feature="full_customer_charts">
                  <CustomerSection data={customerData} loading={customerLoading} districtName={districtName} industryName={industryName} />
                </ProGateSection>
              </div>
              <div id="section-b6">
                <ProGateSection feature="rent_trend">
                  <RentTrendChart data={rentData} loading={rentLoading} districtName={districtName} />
                </ProGateSection>
              </div>
            </div>

            {/* Row 3.5: Sales Trend (매출 트렌드) */}
            <div id="section-trend">
              <SalesTrendChart data={salesTrendData} loading={salesTrendLoading} districtName={districtName} industryName={industryName} />
            </div>

            {/* Row 4: B7 Franchise */}
            <div id="section-b7">
              <ProGateSection feature="franchise_comparison">
                <FranchiseSection data={franchiseData} loading={franchiseLoading} industryName={industryName} />
              </ProGateSection>
            </div>

            {/* Row 5: C Simulator */}
            <div id="section-c">
              <ProGateSection feature="simulator_full">
                <InlineSimulatorSection
                  defaults={simulationData}
                  loading={simulationLoading}
                  districtName={districtName}
                />
              </ProGateSection>
            </div>

            {/* Row 6: D Risk + E Support */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div id="section-d">
                <ProGateSection feature="risk_full">
                  <RiskSection data={riskData} loading={riskLoading} districtName={districtName} />
                </ProGateSection>
              </div>
              <div id="section-e">
                <SupportSection data={supportData} loading={supportLoading} industryCode={industryCode} industryName={industryName} />
              </div>
            </div>
          </div>
        )}

        {/* Action: Go to Step 3 (Action Plan) */}
        {selectedCode && (
          <div className="mt-8 flex flex-col items-center gap-4">
            <Link
              href={`/analyze/action?industry_code=${industryCode}&district_code=${selectedCode}&budget=${budget}`}
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-4 text-base font-bold text-white shadow-lg shadow-blue-500/25 transition hover:shadow-xl"
            >
              <Sparkles className="h-5 w-5" />
              사업계획서 생성하기
              <ArrowRight className="h-5 w-5" />
            </Link>
            <div className="flex flex-wrap justify-center gap-3">
              <Link
                href={`/property?district_code=${selectedCode}&industry_code=${industryCode}`}
                className="text-xs font-medium text-slate-500 underline decoration-slate-300 underline-offset-2 transition hover:text-slate-700"
              >
                매물 탐색
              </Link>
              <span className="text-xs text-slate-300">·</span>
              <Link
                href={`/cost-compare?industry_code=${industryCode}&district_code=${selectedCode}`}
                className="text-xs font-medium text-slate-500 underline decoration-slate-300 underline-offset-2 transition hover:text-slate-700"
              >
                비용 비교
              </Link>
            </div>
          </div>
        )}
      </main>

      {/* Floating TOC for mobile */}
      {selectedCode && <FloatingTOC />}
    </div>
  );
}

export default function AnalyzeReportPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <ReportContent />
    </Suspense>
  );
}
