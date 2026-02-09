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
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
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

// ─── AI Briefing Card ──────────────────────────────────────────────────
function BriefingCard({ districtCode, industryCode }: { districtCode: string; industryCode: string }) {
  const [briefing, setBriefing] = useState<string>("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!districtCode) return;
    setLoading(true);
    fetch(`${API_BASE}/districts/${districtCode}/briefing?industry_code=${industryCode}`)
      .then((r) => r.json())
      .then((data) => setBriefing(data.briefing || ""))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [districtCode, industryCode]);

  if (!districtCode) return null;

  return (
    <div className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50/80 to-indigo-50/50 p-5">
      <div className="mb-2 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-blue-500" />
        <h3 className="text-sm font-bold text-blue-900">AI 실시간 브리핑</h3>
      </div>
      {loading ? (
        <div className="flex items-center gap-2 py-3">
          <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
          <span className="text-xs text-blue-600">AI가 상권을 분석하고 있습니다...</span>
        </div>
      ) : briefing ? (
        <p className="text-sm leading-relaxed text-blue-900/80">{briefing}</p>
      ) : null}
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
}: {
  districts: TopDistrict[];
  selectedCode: string;
  onSelect: (code: string) => void;
  loading: boolean;
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
                  <p className="text-[10px] text-slate-400">종합점수</p>
                  <p className="text-sm font-extrabold text-slate-900">{d.scorecard_total}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] text-slate-400">생존율</p>
                  <p className="text-sm font-extrabold text-slate-900">{(d.survival_rate * 100).toFixed(0)}%</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] text-slate-400">월매출</p>
                  <p className="text-sm font-extrabold text-slate-900">{formatWon(d.monthly_sales)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] text-slate-400">경쟁점포</p>
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

      {/* Map visualization */}
      {districts.some((d) => d.coordinates) && (
        <MiniMap
          markers={districts
            .filter(
              (d): d is TopDistrict & { coordinates: { lat: number; lng: number } } =>
                !!d.coordinates,
            )
            .map((d, i) => ({
              lat: d.coordinates.lat,
              lng: d.coordinates.lng,
              label: d.district_name,
              type: d.district_code === selectedCode ? ("selected" as const) : ("recommended" as const),
              rank: i + 1,
              successProbability: d.success_probability,
            }))}
          height={280}
          zoom={12}
        />
      )}
    </div>
  );
}

// ─── Section B1: Scorecard Radar ───────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ScorecardSection({ data, loading }: { data: any; loading: boolean }) {
  if (loading) return <SectionSkeleton title="성공 점수" />;
  if (!data) return null;

  const categories = data.categories || [];
  const total = data.total_score ?? 0;
  const verdict = getVerdictStyle(total);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Target className="h-5 w-5 text-blue-500" />
        <h3 className="text-sm font-bold text-slate-900">B1. 성공 점수</h3>
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
          <p className="mt-1 text-xs text-slate-500">서울 평균 대비 상위 {data.percentile ?? "-"}%</p>
        </div>
      </div>

      <div className="space-y-2">
        {categories.map(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (cat: any) => (
            <div key={cat.name} className="flex items-center gap-3">
              <span className="w-16 text-xs font-medium text-slate-600">{cat.name}</span>
              <div className="flex-1">
                <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-blue-400 to-indigo-500 transition-all duration-500"
                    style={{ width: `${Math.min(100, (cat.score / cat.max_score) * 100)}%` }}
                  />
                </div>
              </div>
              <span className="text-xs font-bold text-slate-700">
                {cat.score}/{cat.max_score}
              </span>
            </div>
          ),
        )}
      </div>

      <Link
        href={`/report?district_code=${data.district_code}&industry_code=${data.industry_code}`}
        className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700"
      >
        상세 스코어카드 보기 <ChevronRight className="h-3 w-3" />
      </Link>
    </div>
  );
}

// ─── Section B2: Revenue Waterfall ─────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function RevenueSection({ data, loading }: { data: any; loading: boolean }) {
  if (loading) return <SectionSkeleton title="예상 수익 구조" />;
  if (!data) return null;

  const revenue = data.revenue || {};
  const operating = data.operating_cost || {};
  const breakEven = data.break_even || {};

  const monthlySales = revenue.monthly_sales_per_store || 0;
  const netProfit = breakEven.monthly_net_profit || 0;

  const items = [
    { label: "월 매출", value: monthlySales, color: "bg-blue-500", type: "positive" },
    { label: "식재료비", value: -(operating.cogs || 0), color: "bg-orange-400", type: "negative" },
    { label: "인건비", value: -(operating.labor || 0), color: "bg-amber-400", type: "negative" },
    { label: "임대료", value: -(operating.rent || 0), color: "bg-rose-400", type: "negative" },
    { label: "기타비용", value: -((operating.utilities || 0) + (operating.other || 0)), color: "bg-slate-400", type: "negative" },
    { label: "순이익", value: netProfit, color: netProfit >= 0 ? "bg-emerald-500" : "bg-rose-500", type: "result" },
  ];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-emerald-500" />
        <h3 className="text-sm font-bold text-slate-900">B2. 예상 수익 구조</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[9px] font-semibold text-emerald-600">
          <CreditCard className="h-2.5 w-2.5" />
          카드매출 기반
        </span>
      </div>

      {/* Waterfall visualization */}
      <div className="space-y-2">
        {items.map((item) => {
          const absValue = Math.abs(item.value);
          const pct = monthlySales > 0 ? (absValue / monthlySales) * 100 : 0;
          return (
            <div key={item.label} className="flex items-center gap-3">
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
        </div>
        <div className="rounded-xl bg-slate-50 p-3 text-center">
          <p className="text-[10px] text-slate-400">투자회수</p>
          <p className="text-sm font-extrabold text-slate-900">
            {breakEven.break_even_months_min || "-"}~{breakEven.break_even_months_max || "-"}개월
          </p>
        </div>
        <div className="rounded-xl bg-slate-50 p-3 text-center">
          <p className="text-[10px] text-slate-400">일 손익분기</p>
          <p className="text-sm font-extrabold text-slate-900">
            {formatWon(breakEven.daily_break_even_sales || 0)}
          </p>
        </div>
      </div>

      <Link
        href={`/simulator?district_code=${data.district_code}&industry_code=${data.industry_code}`}
        className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700"
      >
        상세 시뮬레이터 <ChevronRight className="h-3 w-3" />
      </Link>
    </div>
  );
}

// ─── Section B3: Competition ───────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CompetitionSection({ data, loading, localdataData, localdataLoading }: { data: any; loading: boolean; localdataData?: any; localdataLoading?: boolean }) {
  if (loading) return <SectionSkeleton title="경쟁 환경" />;
  if (!data) return null;

  const stores = data.stores || {};
  const storeCount = stores.store_count || stores.total || 0;
  const newStores = stores.new_stores || 0;
  const closedStores = stores.closed_stores || 0;
  const franchiseStores = stores.franchise_stores || 0;
  const franchiseRatio = storeCount > 0 ? ((franchiseStores / storeCount) * 100).toFixed(0) : "0";
  const netGrowth = newStores - closedStores;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Store className="h-5 w-5 text-purple-500" />
        <h3 className="text-sm font-bold text-slate-900">B3. 경쟁 환경</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-purple-50 px-2 py-0.5 text-[9px] font-semibold text-purple-600">
          LOCALDATA + 카드매출
        </span>
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
    </div>
  );
}

// ─── Section B5: Customer Analysis ─────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomerSection({ data, loading }: { data: any; loading: boolean }) {
  if (loading) return <SectionSkeleton title="고객 분석" />;
  if (!data) return null;

  const breakdown = data.breakdown || {};
  const byAge = breakdown.by_age || {};
  const byTime = breakdown.by_time || {};
  const byGender = breakdown.by_gender || {};

  const ageLabels: Record<string, string> = {
    "10s": "10대", "20s": "20대", "30s": "30대", "40s": "40대", "50s": "50대", "60s_plus": "60+",
  };
  const timeLabels: Record<string, string> = {
    "00_06": "0~6시", "06_11": "6~11시", "11_14": "11~14시", "14_17": "14~17시", "17_21": "17~21시", "21_24": "21~24시",
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Users className="h-5 w-5 text-cyan-500" />
        <h3 className="text-sm font-bold text-slate-900">B5. 고객 분석</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-cyan-50 px-2 py-0.5 text-[9px] font-semibold text-cyan-600">
          <CreditCard className="h-2.5 w-2.5" />
          카드매출 6년 36분기
        </span>
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
      <div>
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
    </div>
  );
}

// ─── Section B7: Franchise Comparison ──────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function FranchiseSection({ data, loading, industryCode }: { data: any; loading: boolean; industryCode: string }) {
  if (loading) return <SectionSkeleton title="프랜차이즈 vs 독립" />;
  if (!data) return null;

  const brands = data.brands || data.top_brands || [];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Building2 className="h-5 w-5 text-orange-500" />
        <h3 className="text-sm font-bold text-slate-900">B7. 프랜차이즈 vs 독립 창업</h3>
      </div>

      {brands.length > 0 ? (
        <div className="space-y-2">
          {brands.slice(0, 5).map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (brand: any, i: number) => (
              <div key={i} className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-2">
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
        </div>
      ) : (
        <p className="text-sm text-slate-500">프랜차이즈 데이터를 불러올 수 없습니다</p>
      )}

      <Link
        href={`/franchise?industry_code=${industryCode}`}
        className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700"
      >
        프랜차이즈 상세 비교 <ChevronRight className="h-3 w-3" />
      </Link>
    </div>
  );
}

// ─── Section C: Inline Simulator ───────────────────────────────────────
function InlineSimulatorSection({
  defaults,
  loading,
  districtCode,
  industryCode,
}: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  defaults: any;
  loading: boolean;
  districtCode: string;
  industryCode: string;
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
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <SlidersHorizontal className="h-5 w-5 text-indigo-500" />
        <h3 className="text-sm font-bold text-slate-900">C. 수익 시뮬레이터</h3>
      </div>

      <div className="space-y-4">
        {/* Sales slider */}
        <div>
          <label className="mb-1 flex items-center justify-between text-xs text-slate-500">
            <span>매출 조정</span>
            <span className="font-bold text-slate-700">{(salesMultiplier * 100).toFixed(0)}%</span>
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
            <span>임대료 조정</span>
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
            <span>인건비 조정</span>
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

      <Link
        href={`/simulator?district_code=${districtCode}&industry_code=${industryCode}`}
        className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700"
      >
        상세 시뮬레이터 <ChevronRight className="h-3 w-3" />
      </Link>
    </div>
  );
}

// ─── Section D: Risk & Opportunity ─────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function RiskSection({ data, loading }: { data: any; loading: boolean }) {
  if (loading) return <SectionSkeleton title="리스크 & 기회" />;
  if (!data) return null;

  const sections = data.sections || data.analysis?.sections || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const riskSection = sections.find((s: any) => s.title?.includes("리스크") || s.title?.includes("위험"));
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const oppSection = sections.find((s: any) => s.title?.includes("기회") || s.title?.includes("강점") || s.title?.includes("장점"));

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-amber-500" />
        <h3 className="text-sm font-bold text-slate-900">D. AI 리스크 & 기회 분석</h3>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {/* Risk */}
        <div className="rounded-xl border border-rose-100 bg-rose-50/30 p-4">
          <p className="mb-2 text-xs font-bold text-rose-700">주요 리스크</p>
          {riskSection ? (
            <p className="text-xs leading-relaxed text-rose-900/80">
              {riskSection.content?.slice(0, 200)}...
            </p>
          ) : (
            <p className="text-xs text-rose-500">분석 데이터 없음</p>
          )}
        </div>

        {/* Opportunity */}
        <div className="rounded-xl border border-emerald-100 bg-emerald-50/30 p-4">
          <p className="mb-2 text-xs font-bold text-emerald-700">주요 기회</p>
          {oppSection ? (
            <p className="text-xs leading-relaxed text-emerald-900/80">
              {oppSection.content?.slice(0, 200)}...
            </p>
          ) : (
            <p className="text-xs text-emerald-500">분석 데이터 없음</p>
          )}
        </div>
      </div>

      {sections.length > 0 && (
        <p className="mt-3 text-[10px] text-slate-400">
          Powered by Gemini AI - {sections.length}개 섹션 분석 완료
        </p>
      )}
    </div>
  );
}

// ─── Section E: Support Programs ───────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function SupportSection({ data, loading, industryCode }: { data: any; loading: boolean; industryCode: string }) {
  if (loading) return <SectionSkeleton title="지원금 매칭" />;
  if (!data) return null;

  const programs = data.programs || data.matched_programs || [];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Gift className="h-5 w-5 text-green-500" />
        <h3 className="text-sm font-bold text-slate-900">E. 지원금 매칭</h3>
        {programs.length > 0 && (
          <span className="rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-bold text-green-700">
            {programs.length}건
          </span>
        )}
      </div>

      {programs.length > 0 ? (
        <div className="space-y-2">
          {programs.slice(0, 3).map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (prog: any, i: number) => (
              <div key={i} className="rounded-lg border border-slate-100 bg-slate-50/50 p-3">
                <p className="text-xs font-semibold text-slate-900">{prog.name || prog.program_name}</p>
                <p className="mt-0.5 text-[10px] text-slate-500">{prog.organization || prog.provider}</p>
                {(prog.max_amount || prog.amount) && (
                  <p className="mt-1 text-xs font-bold text-green-700">
                    최대 {formatWon(prog.max_amount || prog.amount)}
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
    </div>
  );
}

// ─── Main Report Page ──────────────────────────────────────────────────
function ReportContent() {
  const searchParams = useSearchParams();
  const store = useAnalyzeStore();

  const industryCode = searchParams?.get("industry_code") || store.industryCode;
  const budgetMin = Number(searchParams?.get("budget_min")) || store.budgetMin;
  const budgetMax = Number(searchParams?.get("budget_max")) || store.budgetMax;

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
          budget_min: String(budgetMin),
          budget_max: String(budgetMax),
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
            coordinates: r.lat && r.lng ? { lat: r.lat, lng: r.lng } : undefined,
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
  }, [industryCode, budgetMin, budgetMax]);

  // Phase 2: Fetch section data when district changes
  const fetchSectionData = useCallback(
    async (districtCode: string) => {
      if (!districtCode) return;

      // Check cache
      const cached = store.sectionData[districtCode];

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

      // B3: Competition (stores data)
      if (!cached?.competition) {
        setCompetitionLoading(true);
        fetch(`${API_BASE}/explore/stores?district_code=${districtCode}&industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            const storesInfo = {
              stores: data,
              store_count: data.total || 0,
              new_stores: 0,
              closed_stores: 0,
              franchise_stores: 0,
            };
            // Get from competitive analysis
            return fetch(`${API_BASE}/competitive/analyze?district_code=${districtCode}&industry_code=${industryCode}`)
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

      // E: Support
      if (!cached?.support) {
        setSupportLoading(true);
        fetch(`${API_BASE}/support/programs?industry_code=${industryCode}`)
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
    [industryCode],
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
            AI 원페이지 리포트
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            {store.industryName || "카페"} / 예산 {(budgetMin / 10000 * 10000 / 10000).toLocaleString()}만~{(budgetMax / 10000 * 10000 / 10000).toLocaleString()}만원
          </p>
        </div>

        {/* Section A: TOP 3 */}
        <div id="section-top3" className="mb-6 rounded-2xl border border-slate-200 bg-white p-6">
          <Top3Section
            districts={topDistricts}
            selectedCode={selectedCode}
            onSelect={handleDistrictSelect}
            loading={top3Loading}
          />
        </div>

        {/* Selected district header */}
        {selectedDistrict && (
          <div className="mb-4 flex items-center gap-2 rounded-xl border border-blue-100 bg-blue-50/50 px-4 py-3">
            <Sparkles className="h-4 w-4 text-blue-500" />
            <p className="text-sm font-semibold text-blue-900">
              <span className="font-extrabold">{selectedDistrict.district_name}</span> 상세 분석
            </p>
          </div>
        )}

        {/* AI Briefing + Risk Alert */}
        {selectedCode && (
          <div className="mb-4 space-y-3">
            <BriefingCard districtCode={selectedCode} industryCode={industryCode} />
            <RiskAlertBanner districtCode={selectedCode} industryCode={industryCode} />
          </div>
        )}

        {/* Report sections B~E */}
        {selectedCode && (
          <div className="space-y-4">
            {/* Row 1: B1 + B2 */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div id="section-b1">
                <ProGateSection feature="detailed_scorecard">
                  <ScorecardSection data={scorecardData} loading={scorecardLoading} />
                </ProGateSection>
              </div>
              <div id="section-b2">
                <ProGateSection feature="revenue_waterfall">
                  <RevenueSection data={simulationData} loading={simulationLoading} />
                </ProGateSection>
              </div>
            </div>

            {/* Row 2: B3 + B5 */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div id="section-b3">
                <ProGateSection feature="competition_map">
                  <CompetitionSection data={competitionData} loading={competitionLoading} localdataData={localdataData} localdataLoading={localdataLoading} />
                </ProGateSection>
              </div>
              <div id="section-b5">
                <ProGateSection feature="full_customer_charts">
                  <CustomerSection data={customerData} loading={customerLoading} />
                </ProGateSection>
              </div>
            </div>

            {/* Row 2.5: B4 Location + B6 Rent */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div id="section-b4">
                <ProGateSection feature="location_profile">
                  <LocationProfile data={locationData} loading={locationLoading} />
                </ProGateSection>
              </div>
              <div id="section-b6">
                <ProGateSection feature="rent_trend">
                  <RentTrendChart data={rentData} loading={rentLoading} />
                </ProGateSection>
              </div>
            </div>

            {/* Row 2.75: Sales Trend */}
            <div id="section-trend">
              <SalesTrendChart data={salesTrendData} loading={salesTrendLoading} />
            </div>

            {/* Row 3: B7 Franchise */}
            <div id="section-b7">
              <ProGateSection feature="franchise_comparison">
                <FranchiseSection data={franchiseData} loading={franchiseLoading} industryCode={industryCode} />
              </ProGateSection>
            </div>

            {/* Row 4: C Simulator */}
            <div id="section-c">
              <ProGateSection feature="simulator_full">
                <InlineSimulatorSection
                  defaults={simulationData}
                  loading={simulationLoading}
                  districtCode={selectedCode}
                  industryCode={industryCode}
                />
              </ProGateSection>
            </div>

            {/* Row 5: D Risk + E Support */}
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div id="section-d">
                <ProGateSection feature="risk_full">
                  <RiskSection data={riskData} loading={riskLoading} />
                </ProGateSection>
              </div>
              <div id="section-e">
                <SupportSection data={supportData} loading={supportLoading} industryCode={industryCode} />
              </div>
            </div>
          </div>
        )}

        {/* Action: Go to Step 3 (Property) */}
        {selectedCode && (
          <div className="mt-8 flex flex-col items-center gap-3">
            <Link
              href={`/property?district_code=${selectedCode}&industry_code=${industryCode}`}
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 px-8 py-4 text-base font-bold text-white shadow-lg shadow-emerald-500/25 transition hover:shadow-xl"
            >
              <Building2 className="h-5 w-5" />
              매물 찾아보기
              <ArrowRight className="h-5 w-5" />
            </Link>
            <div className="flex flex-wrap justify-center gap-3">
              <Link
                href={`/cost-compare?industry_code=${industryCode}&district_code=${selectedCode}`}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
              >
                비용 비교하기
              </Link>
              <Link
                href={`/timeline?district_code=${selectedCode}&industry_code=${industryCode}&budget=${budgetMax}`}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
              >
                창업 타임라인
              </Link>
              <Link
                href={`/analyze/action?industry_code=${industryCode}&district_code=${selectedCode}&budget_min=${budgetMin}&budget_max=${budgetMax}`}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
              >
                사업계획서 생성
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
