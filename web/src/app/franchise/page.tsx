"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  MapPin,
  Building2,
  Store,
  TrendingUp,
  ShieldCheck,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { track } from "@/lib/analytics";
import { JourneyStepper } from "@/components/JourneyStepper";
import {
  useJourneyStore,
  INDUSTRY_NAMES,
  INDUSTRY_ICONS,
} from "@/lib/journey-store";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

// ---------------------------------------------------------------------------
// Types (matches franchise_data_service.py response)
// ---------------------------------------------------------------------------

interface StartupCosts {
  franchise_fee: number;
  education_fee: number;
  deposit: number;
  interior_cost: number;
  total_startup_cost: number;
}

interface IndustryStatus {
  brand_count: number;
  store_count: number;
  avg_sales: number;
}

interface FranchiseBenchmark {
  startup_costs: StartupCosts;
  industry_status: IndustryStatus;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatManWon(won: number): string {
  if (won === 0) return "0원";
  const man = Math.round(won / 10000);
  return `${man.toLocaleString()}만원`;
}

// ---------------------------------------------------------------------------
// Pros & Risks content
// ---------------------------------------------------------------------------

const FRANCHISE_PROS = [
  "검증된 브랜드",
  "본사 마케팅·물류 지원",
  "레시피·운영 매뉴얼",
];

const FRANCHISE_RISKS = [
  "월 로열티 3~5%",
  "메뉴/인테리어 자유도 제한",
  "계약해지 위약금",
];

const INDEPENDENT_PROS = [
  "초기비용 낮음",
  "메뉴/운영 자유도",
  "로열티 없음",
];

const INDEPENDENT_RISKS = [
  "브랜드 인지도 0",
  "모든 것 직접 해결",
  "마케팅 직접",
];

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function ComparisonSkeleton() {
  return (
    <div className="space-y-8">
      {/* Title skeleton */}
      <div className="text-center">
        <div className="h-8 w-72 bg-slate-200 rounded-lg mx-auto mb-3 animate-pulse" />
        <div className="h-5 w-80 bg-slate-100 rounded-lg mx-auto animate-pulse" />
      </div>

      {/* Cards skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {[0, 1].map((i) => (
          <div
            key={i}
            className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden animate-pulse"
          >
            <div className="h-1.5 bg-slate-200" />
            <div className="p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-slate-200" />
                <div className="space-y-2 flex-1">
                  <div className="h-5 bg-slate-200 rounded w-1/2" />
                  <div className="h-3 bg-slate-100 rounded w-1/3" />
                </div>
              </div>
              <div className="bg-slate-50 rounded-xl p-4 space-y-3">
                {[0, 1, 2, 3, 4].map((j) => (
                  <div key={j} className="flex justify-between">
                    <div className="h-4 bg-slate-200 rounded w-1/3" />
                    <div className="h-4 bg-slate-200 rounded w-1/4" />
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                <div className="h-4 bg-slate-200 rounded w-2/3" />
                <div className="h-4 bg-slate-200 rounded w-3/4" />
                <div className="h-4 bg-slate-200 rounded w-1/2" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Industry status skeleton */}
      <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-6 animate-pulse">
        <div className="h-5 bg-slate-200 rounded w-1/3 mb-4" />
        <div className="grid grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => (
            <div key={i} className="bg-slate-50 rounded-xl p-4">
              <div className="h-3 bg-slate-200 rounded w-1/2 mx-auto mb-2" />
              <div className="h-7 bg-slate-200 rounded w-2/3 mx-auto" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cost Row
// ---------------------------------------------------------------------------

function CostRow({
  label,
  value,
  bold,
  highlight,
}: {
  label: string;
  value: string;
  bold?: boolean;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between py-2",
        bold && "border-t border-slate-200 pt-3 mt-1"
      )}
    >
      <span
        className={cn(
          "text-sm",
          bold ? "font-bold text-slate-800" : "text-slate-600"
        )}
      >
        {label}
      </span>
      <span
        className={cn(
          "text-sm tabular-nums",
          bold
            ? "font-extrabold text-slate-900 text-base"
            : highlight
              ? "font-semibold text-emerald-600"
              : "font-semibold text-slate-800"
        )}
      >
        {value}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bullet List
// ---------------------------------------------------------------------------

function BulletList({
  icon,
  titleColor,
  title,
  items,
  bulletColor,
  bulletChar,
}: {
  icon: React.ReactNode;
  titleColor: string;
  title: string;
  items: string[];
  bulletColor: string;
  bulletChar: string;
}) {
  return (
    <div className="mt-5">
      <div className="flex items-center gap-1.5 mb-2">
        {icon}
        <span className={cn("text-xs font-bold", titleColor)}>{title}</span>
      </div>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
            <span className={cn("mt-0.5 flex-shrink-0", bulletColor)}>
              {bulletChar}
            </span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function FranchisePage() {
  const router = useRouter();
  const {
    industryCode,
    industryName,
    industryIcon,
    setStep,
    setFranchiseChoice,
  } = useJourneyStore();

  const displayName = INDUSTRY_NAMES[industryCode] || industryName || "카페";
  const displayIcon = INDUSTRY_ICONS[industryCode] || industryIcon || "☕";

  const [data, setData] = useState<FranchiseBenchmark | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Set journey step on mount
  useEffect(() => {
    setStep(2);
    track("franchise_compare", { industry_code: industryCode });
  }, [setStep, industryCode]);

  // Fetch franchise benchmark data
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/franchise/benchmark/${industryCode}`
      );
      if (!res.ok) throw new Error(`서버 오류 (${res.status})`);
      const json: FranchiseBenchmark = await res.json();
      setData(json);
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "데이터를 불러올 수 없습니다."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [industryCode]);

  // Derived independent costs
  const independentInterior = data
    ? Math.round(data.startup_costs.interior_cost * 0.7)
    : 0;
  const independentTotal = independentInterior;

  // Choice handlers
  const handleFranchiseChoice = () => {
    setFranchiseChoice("franchise");
    router.push("/results");
  };

  const handleIndependentChoice = () => {
    setFranchiseChoice("independent");
    router.push("/results");
  };

  const handleSkip = () => {
    router.push("/results");
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-200/60 sticky top-0 z-40">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm">
              <MapPin size={16} className="text-white" />
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              SpotPick
            </span>
          </Link>

          <span className="text-sm text-slate-500">
            {displayIcon} {displayName}
          </span>
        </div>
      </header>

      {/* Stepper */}
      <JourneyStepper className="py-3 px-4 bg-white/80 backdrop-blur-sm border-b border-slate-100" />

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        {/* Title */}
        <div className="text-center">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900">
            {displayName} — 프랜차이즈 vs 독립 창업
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            초기 비용과 장단점을 비교해 나에게 맞는 창업 방식을 선택하세요
          </p>
        </div>

        {/* Loading skeleton */}
        {loading && <ComparisonSkeleton />}

        {/* Error state */}
        {!loading && error && (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-8 text-center">
            <AlertTriangle
              size={36}
              className="mx-auto mb-3 text-rose-400"
            />
            <p className="text-rose-600 text-sm font-medium mb-1">
              데이터를 불러올 수 없습니다
            </p>
            <p className="text-rose-400 text-xs mb-4">{error}</p>
            <button
              onClick={fetchData}
              className="px-5 py-2.5 bg-rose-600 text-white text-sm font-semibold rounded-xl hover:bg-rose-700 transition-colors"
            >
              다시 시도
            </button>
          </div>
        )}

        {/* Comparison cards */}
        {!loading && !error && data && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* LEFT -- Franchise Card */}
              <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
                <div className="h-1.5 bg-gradient-to-r from-blue-500 to-indigo-500" />
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-5">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center">
                      <Building2 size={20} className="text-blue-600" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-slate-800">
                        프랜차이즈 창업
                      </h2>
                      <p className="text-xs text-slate-400">
                        가맹본부와 함께 시작
                      </p>
                    </div>
                  </div>

                  {/* Cost breakdown */}
                  <div className="bg-slate-50 rounded-xl p-4">
                    <CostRow
                      label="가맹비"
                      value={formatManWon(data.startup_costs.franchise_fee)}
                    />
                    <CostRow
                      label="교육비"
                      value={formatManWon(data.startup_costs.education_fee)}
                    />
                    <CostRow
                      label="보증금"
                      value={formatManWon(data.startup_costs.deposit)}
                    />
                    <CostRow
                      label="인테리어"
                      value={formatManWon(data.startup_costs.interior_cost)}
                    />
                    <CostRow
                      label="총 초기비용"
                      value={formatManWon(data.startup_costs.total_startup_cost)}
                      bold
                    />
                  </div>

                  {/* Pros */}
                  <BulletList
                    icon={<ShieldCheck size={14} className="text-emerald-500" />}

                    titleColor="text-emerald-700"
                    title="장점"
                    items={FRANCHISE_PROS}
                    bulletColor="text-emerald-400"
                    bulletChar="+"
                  />

                  {/* Risks */}
                  <BulletList
                    icon={<AlertTriangle size={14} className="text-amber-500" />}

                    titleColor="text-amber-700"
                    title="리스크"
                    items={FRANCHISE_RISKS}
                    bulletColor="text-amber-400"
                    bulletChar="-"
                  />
                </div>
              </div>

              {/* RIGHT -- Independent Card */}
              <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm overflow-hidden">
                <div className="h-1.5 bg-gradient-to-r from-emerald-500 to-teal-500" />
                <div className="p-6">
                  <div className="flex items-center gap-3 mb-5">
                    <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center">
                      <Store size={20} className="text-emerald-600" />
                    </div>
                    <div>
                      <h2 className="text-lg font-bold text-slate-800">
                        독립 창업
                      </h2>
                      <p className="text-xs text-slate-400">
                        나만의 브랜드로 시작
                      </p>
                    </div>
                  </div>

                  {/* Cost breakdown */}
                  <div className="bg-slate-50 rounded-xl p-4">
                    <CostRow label="가맹비" value="0원" highlight />
                    <CostRow label="교육비" value="0원" highlight />
                    <CostRow label="보증금" value="0원" highlight />
                    <CostRow
                      label="인테리어"
                      value={formatManWon(independentInterior)}
                    />
                    <CostRow
                      label="총 초기비용"
                      value={formatManWon(independentTotal)}
                      bold
                    />
                  </div>

                  {/* Pros */}
                  <BulletList
                    icon={<ShieldCheck size={14} className="text-emerald-500" />}

                    titleColor="text-emerald-700"
                    title="장점"
                    items={INDEPENDENT_PROS}
                    bulletColor="text-emerald-400"
                    bulletChar="+"
                  />

                  {/* Risks */}
                  <BulletList
                    icon={<AlertTriangle size={14} className="text-amber-500" />}

                    titleColor="text-amber-700"
                    title="리스크"
                    items={INDEPENDENT_RISKS}
                    bulletColor="text-amber-400"
                    bulletChar="-"
                  />
                </div>
              </div>
            </div>

            {/* Savings highlight */}
            {data.startup_costs.total_startup_cost > independentTotal && (
              <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-2xl p-5 text-center">
                <p className="text-sm text-emerald-700">
                  독립 창업 시{" "}
                  <span className="font-extrabold text-emerald-800 text-lg">
                    {formatManWon(
                      data.startup_costs.total_startup_cost - independentTotal
                    )}
                  </span>{" "}
                  절약 가능
                </p>
              </div>
            )}

            {/* Industry Overview */}
            <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-6">
              <h3 className="text-base font-bold text-slate-800 mb-4 flex items-center gap-2">
                <TrendingUp size={18} className="text-blue-500" />
                {displayName} 프랜차이즈 업계 현황
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-slate-50 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">가맹본부 수</p>
                  <p className="text-2xl font-extrabold text-slate-800">
                    {data.industry_status.brand_count.toLocaleString()}
                    <span className="text-sm font-medium text-slate-500 ml-0.5">
                      개
                    </span>
                  </p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">가맹점 수</p>
                  <p className="text-2xl font-extrabold text-slate-800">
                    {data.industry_status.store_count.toLocaleString()}
                    <span className="text-sm font-medium text-slate-500 ml-0.5">
                      개
                    </span>
                  </p>
                </div>
                <div className="bg-slate-50 rounded-xl p-4 text-center">
                  <p className="text-xs text-slate-500 mb-1">평균 매출</p>
                  <p className="text-2xl font-extrabold text-slate-800">
                    {formatManWon(data.industry_status.avg_sales)}
                    <span className="text-sm font-medium text-slate-500 ml-0.5">
                      /월
                    </span>
                  </p>
                </div>
              </div>
            </div>

            {/* Choice buttons */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button
                  onClick={handleFranchiseChoice}
                  className={cn(
                    "group relative flex items-center justify-center gap-3 px-6 py-4",
                    "bg-white rounded-2xl border-2 border-blue-300",
                    "hover:border-blue-500 hover:shadow-lg hover:shadow-blue-500/10",
                    "transition-all duration-200"
                  )}
                >
                  <Building2
                    size={20}
                    className="text-blue-500 group-hover:text-blue-600 transition-colors"
                  />
                  <span className="text-base font-bold text-slate-800 group-hover:text-blue-700 transition-colors">
                    프랜차이즈로 진행
                  </span>
                  <ArrowRight
                    size={16}
                    className="text-blue-400 group-hover:translate-x-1 transition-transform"
                  />
                </button>

                <button
                  onClick={handleIndependentChoice}
                  className={cn(
                    "group relative flex items-center justify-center gap-3 px-6 py-4",
                    "bg-white rounded-2xl border-2 border-emerald-300",
                    "hover:border-emerald-500 hover:shadow-lg hover:shadow-emerald-500/10",
                    "transition-all duration-200"
                  )}
                >
                  <Store
                    size={20}
                    className="text-emerald-500 group-hover:text-emerald-600 transition-colors"
                  />
                  <span className="text-base font-bold text-slate-800 group-hover:text-emerald-700 transition-colors">
                    독립 창업으로 진행
                  </span>
                  <ArrowRight
                    size={16}
                    className="text-emerald-400 group-hover:translate-x-1 transition-transform"
                  />
                </button>
              </div>

              {/* Skip link */}
              <div className="text-center">
                <button
                  onClick={handleSkip}
                  className="text-sm text-slate-400 hover:text-slate-600 underline underline-offset-4 transition-colors"
                >
                  이 단계 건너뛰기
                </button>
              </div>
            </div>

            {/* Data source footer */}
            <div className="text-center pt-4 pb-2">
              <p className="text-xs text-slate-400">
                데이터 출처: 공정거래위원회 정보공개서 (2025)
              </p>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
