"use client";

import { useState, useEffect, useCallback, useRef, useMemo, Suspense } from "react";
import {
  MapPin,
  TrendingUp,
  Store,
  Clock,
  DollarSign,
  Shield,
  Users,
  ChevronRight,
  SlidersHorizontal,
  Search,
  MessageCircle,
  FileText,
  ChevronDown,
  GitCompareArrows,
  X,
  CheckSquare,
  Square,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import dynamic from "next/dynamic";
import Link from "next/link";
import type { InteractiveMarkerData } from "@/components/InteractiveMap";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = "/api/v1";

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

const AREA_TYPES = [
  { value: "", label: "전체" },
  { value: "골목상권", label: "골목상권" },
  { value: "발달상권", label: "발달상권" },
  { value: "관광특구", label: "관광특구" },
  { value: "전통시장", label: "전통시장" },
];

const DISTRICTS_25 = [
  "서울 전체", "강남구", "강동구", "강북구", "강서구", "관악구", "광진구",
  "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구",
  "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구",
  "용산구", "은평구", "종로구", "중구", "중랑구",
];

const TYPE_BADGE: Record<string, { bg: string; text: string }> = {
  골목상권: { bg: "bg-emerald-50 border-emerald-200", text: "text-emerald-700" },
  발달상권: { bg: "bg-blue-50 border-blue-200", text: "text-blue-700" },
  관광특구: { bg: "bg-purple-50 border-purple-200", text: "text-purple-700" },
  전통시장: { bg: "bg-amber-50 border-amber-200", text: "text-amber-700" },
};

const MAX_COMPARE = 3;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DashboardResult {
  rank: number;
  district_code: string;
  district_name: string;
  district_type: string;
  success_probability: number;
  verdict: string;
  estimated_rent: number;
  monthly_sales: number;
  sales_per_store: number;
  store_count: number;
  survival_rate: number;
  peak_time: string;
  peak_day: string;
  main_age_group: string;
  foot_traffic_total: number;
  worker_total: number;
  subway_count: number;
  change_indicator: string;
  lat: number;
  lng: number;
  scorecard_total: number;
  key_factors: string[];
}

interface DashboardResponse {
  results: DashboardResult[];
  total_available: number;
  filters_applied: Record<string, string | number>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMan(wonValue: number): string {
  return `${Math.round(wonValue / 10000).toLocaleString()}만원`;
}

function verdictStyle(verdict: string) {
  if (verdict === "추천")
    return { color: "text-emerald-600", bg: "bg-emerald-50 border-emerald-200", ring: "ring-emerald-500/20" };
  if (verdict === "주의")
    return { color: "text-amber-600", bg: "bg-amber-50 border-amber-200", ring: "ring-amber-500/20" };
  return { color: "text-rose-600", bg: "bg-rose-50 border-rose-200", ring: "ring-rose-500/20" };
}

function getStoredIndustry() {
  if (typeof window === "undefined") return { code: "CS100010", name: "카페", icon: "☕" };
  const code = window.localStorage.getItem("builder_curation_industry_code") || "CS100010";
  return {
    code,
    name: INDUSTRY_NAMES[code] || "카페",
    icon: INDUSTRY_ICONS[code] || "☕",
  };
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  return debouncedValue;
}

// ---------------------------------------------------------------------------
// Dynamic imports
// ---------------------------------------------------------------------------

const InteractiveMap = dynamic(
  () => import("@/components/InteractiveMap").then((mod) => ({ default: mod.InteractiveMap })),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full min-h-[300px] flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
        <div className="text-center text-gray-500">
          <MapPin size={32} className="mx-auto mb-2 opacity-60 animate-pulse" />
          <p className="text-sm">지도 로딩 중...</p>
        </div>
      </div>
    ),
  }
);

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------

function CardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-slate-200/60 shadow-sm p-5 animate-pulse">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-full bg-slate-200" />
        <div className="flex-1 space-y-3">
          <div className="h-5 bg-slate-200 rounded w-2/3" />
          <div className="h-4 bg-slate-200 rounded w-1/2" />
          <div className="grid grid-cols-2 gap-2">
            <div className="h-4 bg-slate-200 rounded" />
            <div className="h-4 bg-slate-200 rounded" />
            <div className="h-4 bg-slate-200 rounded" />
            <div className="h-4 bg-slate-200 rounded" />
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Filter Bar
// ---------------------------------------------------------------------------

function formatBudgetLabel(value: number): string {
  if (value >= 10000) {
    const eok = value / 10000;
    if (eok === Math.floor(eok)) return `${Math.floor(eok)}억`;
    return `${eok.toFixed(1)}억`;
  }
  return `${value.toLocaleString()}만`;
}

function FilterBar({
  budgetMin,
  budgetMax,
  district,
  areaType,
  onBudgetMinChange,
  onBudgetMaxChange,
  onDistrictChange,
  onAreaTypeChange,
}: {
  budgetMin: number;
  budgetMax: number;
  district: string;
  areaType: string;
  onBudgetMinChange: (v: number) => void;
  onBudgetMaxChange: (v: number) => void;
  onDistrictChange: (v: string) => void;
  onAreaTypeChange: (v: string) => void;
}) {
  return (
    <div className="bg-white/80 backdrop-blur-md rounded-2xl border border-slate-200/60 shadow-sm p-4 sm:p-5">
      <div className="flex items-center gap-2 mb-4">
        <SlidersHorizontal size={16} className="text-blue-600" />
        <span className="text-sm font-semibold text-slate-700">필터</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Budget range */}
        <div className="sm:col-span-2 lg:col-span-2">
          <label className="block text-xs font-medium text-slate-500 mb-2">
            총예산: {formatBudgetLabel(budgetMin)} ~ {formatBudgetLabel(budgetMax)}원
          </label>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={3000}
              max={20000}
              step={1000}
              value={budgetMin}
              onChange={(e) => {
                const v = Number(e.target.value);
                onBudgetMinChange(Math.min(v, budgetMax - 1000));
              }}
              className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <input
              type="range"
              min={3000}
              max={20000}
              step={1000}
              value={budgetMax}
              onChange={(e) => {
                const v = Number(e.target.value);
                onBudgetMaxChange(Math.max(v, budgetMin + 1000));
              }}
              className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>
        </div>

        {/* District selector */}
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-2">지역</label>
          <div className="relative">
            <select
              value={district}
              onChange={(e) => onDistrictChange(e.target.value)}
              className="w-full appearance-none bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 pr-8"
            >
              {DISTRICTS_25.map((d) => (
                <option key={d} value={d === "서울 전체" ? "" : d}>
                  {d}
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          </div>
        </div>

        {/* Area type */}
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-2">상권 유형</label>
          <div className="flex flex-wrap gap-1.5">
            {AREA_TYPES.map((t) => (
              <button
                key={t.value}
                onClick={() => onAreaTypeChange(t.value)}
                className={cn(
                  "px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all border",
                  areaType === t.value
                    ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                    : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
                )}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Result Card (with compare checkbox)
// ---------------------------------------------------------------------------

function ResultCard({
  result,
  industryCode,
  industryName,
  isHighlighted,
  isCompareSelected,
  compareDisabled,
  onHover,
  onCompareToggle,
  cardRef,
}: {
  result: DashboardResult;
  industryCode: string;
  industryName: string;
  isHighlighted: boolean;
  isCompareSelected: boolean;
  compareDisabled: boolean;
  onHover: (code: string | null) => void;
  onCompareToggle: (code: string) => void;
  cardRef: (el: HTMLDivElement | null) => void;
}) {
  const v = verdictStyle(result.verdict);
  const badge = TYPE_BADGE[result.district_type] || TYPE_BADGE["골목상권"];
  const prob = Math.round(result.success_probability * 100);
  const survivalPct = Math.min(100, Math.round(result.survival_rate * 100));

  return (
    <div
      ref={cardRef}
      data-district={result.district_code}
      onMouseEnter={() => onHover(result.district_code)}
      onMouseLeave={() => onHover(null)}
      className={cn(
        "bg-white rounded-2xl border shadow-sm transition-all duration-200 overflow-hidden",
        isHighlighted
          ? "border-blue-400 shadow-md ring-2 ring-blue-500/20 scale-[1.01]"
          : isCompareSelected
            ? "border-indigo-400 shadow-md ring-2 ring-indigo-500/20"
            : "border-slate-200/60 hover:shadow-md hover:border-slate-300"
      )}
    >
      <div className="p-4 sm:p-5">
        {/* Header row */}
        <div className="flex items-start gap-3 mb-3">
          {/* Compare checkbox */}
          <button
            onClick={() => onCompareToggle(result.district_code)}
            disabled={compareDisabled && !isCompareSelected}
            className={cn(
              "flex-shrink-0 mt-0.5 transition-all",
              compareDisabled && !isCompareSelected
                ? "opacity-30 cursor-not-allowed"
                : "cursor-pointer hover:scale-110"
            )}
            title={isCompareSelected ? "비교 해제" : compareDisabled ? `최대 ${MAX_COMPARE}개` : "비교에 추가"}
          >
            {isCompareSelected ? (
              <CheckSquare size={18} className="text-indigo-600" />
            ) : (
              <Square size={18} className="text-slate-300" />
            )}
          </button>

          {/* Rank badge */}
          <div className={cn(
            "w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-md flex-shrink-0",
            result.rank <= 3
              ? "bg-gradient-to-br from-blue-500 to-indigo-600"
              : "bg-gradient-to-br from-slate-400 to-slate-500"
          )}>
            {result.rank}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base font-bold text-slate-800 truncate">
                {result.district_name}
              </h3>
              <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full border", badge.bg, badge.text)}>
                {result.district_type}
              </span>
            </div>

            {/* Verdict + probability */}
            <div className="flex items-center gap-2 mt-1.5">
              <span className={cn("inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full border", v.bg, v.color)}>
                {result.verdict}
              </span>
              <span className={cn("text-lg font-extrabold tracking-tight", v.color)}>
                {prob}%
              </span>
            </div>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div className="flex items-center gap-2">
            <DollarSign size={14} className="text-blue-500 flex-shrink-0" />
            <span className="text-slate-500">월세</span>
            <span className="ml-auto font-semibold text-slate-800">{formatMan(result.estimated_rent)}</span>
          </div>
          <div className="flex items-center gap-2">
            <TrendingUp size={14} className="text-emerald-500 flex-shrink-0" />
            <span className="text-slate-500">매출</span>
            <span className="ml-auto font-semibold text-slate-800">{formatMan(result.sales_per_store)}/월</span>
          </div>
          <div className="flex items-center gap-2">
            <Store size={14} className="text-orange-500 flex-shrink-0" />
            <span className="text-slate-500">경쟁</span>
            <span className="ml-auto font-semibold text-slate-800">{industryName} {result.store_count}개</span>
          </div>
          <div className="flex items-center gap-2">
            <Shield size={14} className="text-indigo-500 flex-shrink-0" />
            <span className="text-slate-500">생존율</span>
            <span className="ml-auto font-semibold text-slate-800">{survivalPct}%</span>
          </div>
          <div className="flex items-center gap-2">
            <Clock size={14} className="text-pink-500 flex-shrink-0" />
            <span className="text-slate-500">피크</span>
            <span className="ml-auto font-semibold text-slate-800 truncate">{result.peak_time || "-"}</span>
          </div>
          <div className="flex items-center gap-2">
            <Users size={14} className="text-violet-500 flex-shrink-0" />
            <span className="text-slate-500">유동인구</span>
            <span className="ml-auto font-semibold text-slate-800">
              {result.foot_traffic_total > 0 ? `${Math.round(result.foot_traffic_total / 10000).toLocaleString()}만` : "-"}
            </span>
          </div>
        </div>

        {/* Key factors */}
        {result.key_factors && result.key_factors.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {result.key_factors.slice(0, 3).map((f, i) => (
              <span key={i} className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                {f}
              </span>
            ))}
          </div>
        )}

        {/* CTA */}
        <Link
          href={`/report?district_code=${result.district_code}&industry_code=${industryCode}`}
          className="mt-4 flex items-center justify-center gap-2 w-full py-2.5 bg-gradient-to-r from-blue-500 to-indigo-600 text-white text-sm font-semibold rounded-xl shadow-sm hover:shadow-md hover:from-blue-600 hover:to-indigo-700 transition-all"
        >
          <FileText size={14} />
          상세 보고서
          <ChevronRight size={14} />
        </Link>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <Link
            href={`/simulator?district_code=${result.district_code}&industry_code=${industryCode}`}
            className="flex items-center justify-center gap-1.5 py-2 bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-200 transition-colors"
          >
            <SlidersHorizontal size={12} />
            시뮬레이션
          </Link>
          <Link
            href={`/business-plan?district_code=${result.district_code}&industry_code=${industryCode}`}
            className="flex items-center justify-center gap-1.5 py-2 bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-200 transition-colors"
          >
            <FileText size={12} />
            사업계획서
          </Link>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compare Modal
// ---------------------------------------------------------------------------

function CompareModal({
  items,
  industryCode,
  onClose,
}: {
  items: DashboardResult[];
  industryCode: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  const rows: { label: string; icon: React.ReactNode; getValue: (r: DashboardResult) => string; highlight?: "max" | "min" }[] = [
    {
      label: "추천점수",
      icon: <TrendingUp size={14} className="text-emerald-500" />,
      getValue: (r) => `${Math.round(r.success_probability * 100)}%`,
      highlight: "max",
    },
    {
      label: "판정",
      icon: <Shield size={14} className="text-blue-500" />,
      getValue: (r) => r.verdict,
    },
    {
      label: "월세",
      icon: <DollarSign size={14} className="text-blue-500" />,
      getValue: (r) => formatMan(r.estimated_rent),
      highlight: "min",
    },
    {
      label: "월매출",
      icon: <TrendingUp size={14} className="text-emerald-500" />,
      getValue: (r) => formatMan(r.sales_per_store),
      highlight: "max",
    },
    {
      label: "경쟁점포",
      icon: <Store size={14} className="text-orange-500" />,
      getValue: (r) => `${r.store_count}개`,
      highlight: "min",
    },
    {
      label: "생존율",
      icon: <Shield size={14} className="text-indigo-500" />,
      getValue: (r) => `${Math.min(100, Math.round(r.survival_rate * 100))}%`,
      highlight: "max",
    },
    {
      label: "피크타임",
      icon: <Clock size={14} className="text-pink-500" />,
      getValue: (r) => r.peak_time || "-",
    },
    {
      label: "유동인구",
      icon: <Users size={14} className="text-violet-500" />,
      getValue: (r) => r.foot_traffic_total > 0 ? `${Math.round(r.foot_traffic_total / 10000).toLocaleString()}만` : "-",
      highlight: "max",
    },
    {
      label: "상권유형",
      icon: <MapPin size={14} className="text-slate-500" />,
      getValue: (r) => r.district_type,
    },
  ];

  // Compute best value per row for highlighting
  const bestIdx: Record<number, number[]> = {};
  rows.forEach((row, ri) => {
    if (!row.highlight) return;
    const numericValues = items.map((item) => {
      if (row.label === "추천점수") return item.success_probability;
      if (row.label === "월세") return item.estimated_rent;
      if (row.label === "월매출") return item.sales_per_store;
      if (row.label === "경쟁점포") return item.store_count;
      if (row.label === "생존율") return item.survival_rate;
      if (row.label === "유동인구") return item.foot_traffic_total;
      return 0;
    });
    const target = row.highlight === "max" ? Math.max(...numericValues) : Math.min(...numericValues);
    bestIdx[ri] = numericValues.reduce<number[]>((acc, v, i) => (v === target ? [...acc, i] : acc), []);
  });

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-6">
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl max-h-[85vh] bg-white rounded-t-2xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <GitCompareArrows size={18} className="text-indigo-600" />
            <h3 className="text-base font-bold text-slate-800">상권 비교</h3>
            <span className="text-xs text-slate-400">{items.length}개 선택</span>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors">
            <X size={18} className="text-slate-400" />
          </button>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-50 z-10">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-500 w-28" />
                {items.map((item) => {
                  const v = verdictStyle(item.verdict);
                  return (
                    <th key={item.district_code} className="text-center px-3 py-3 min-w-[130px]">
                      <div className="font-bold text-slate-800 text-sm">{item.district_name}</div>
                      <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded-full border mt-0.5 inline-block", v.bg, v.color)}>
                        #{item.rank}
                      </span>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={row.label} className={ri % 2 === 0 ? "bg-white" : "bg-slate-50/50"}>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-1.5">
                      {row.icon}
                      <span className="text-xs font-medium text-slate-600">{row.label}</span>
                    </div>
                  </td>
                  {items.map((item, ci) => (
                    <td key={item.district_code} className="text-center px-3 py-2.5">
                      <span className={cn(
                        "text-sm font-semibold",
                        bestIdx[ri]?.includes(ci) ? "text-blue-600" : "text-slate-700"
                      )}>
                        {row.getValue(item)}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Footer actions */}
        <div className="px-5 py-3 border-t border-slate-100 flex gap-2">
          {items.map((item) => (
            <Link
              key={item.district_code}
              href={`/report?district_code=${item.district_code}&industry_code=${industryCode}`}
              className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 transition-colors"
            >
              <FileText size={12} />
              {item.district_name} 보고서
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compare Floating Bar
// ---------------------------------------------------------------------------

function CompareBar({
  selectedCodes,
  results,
  onRemove,
  onClear,
  onCompare,
}: {
  selectedCodes: string[];
  results: DashboardResult[];
  onRemove: (code: string) => void;
  onClear: () => void;
  onCompare: () => void;
}) {
  const selected = results.filter((r) => selectedCodes.includes(r.district_code));

  return (
    <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 bg-white/95 backdrop-blur-md border border-indigo-200 shadow-xl rounded-2xl px-4 py-3 flex items-center gap-3 animate-slide-up">
      <div className="flex items-center gap-2">
        {selected.map((r) => (
          <span
            key={r.district_code}
            className="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-lg text-xs font-medium border border-indigo-200"
          >
            {r.district_name}
            <button onClick={() => onRemove(r.district_code)} className="hover:text-indigo-900">
              <X size={12} />
            </button>
          </span>
        ))}
      </div>

      <div className="flex items-center gap-2 ml-2">
        <button
          onClick={onClear}
          className="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
        >
          초기화
        </button>
        <button
          onClick={onCompare}
          disabled={selectedCodes.length < 2}
          className={cn(
            "flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-bold transition-all",
            selectedCodes.length >= 2
              ? "bg-indigo-600 text-white shadow-md hover:bg-indigo-700"
              : "bg-slate-100 text-slate-400 cursor-not-allowed"
          )}
        >
          <GitCompareArrows size={14} />
          비교하기
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Content (needs useSearchParams → wrapped in Suspense)
// ---------------------------------------------------------------------------

function ResultsContent() {
  // Industry
  const [industry, setIndustry] = useState(() => getStoredIndustry());

  // Filters (budget-based, 만원 units)
  const [budgetMin, setBudgetMin] = useState(3000);
  const [budgetMax, setBudgetMax] = useState(20000);
  const [district, setDistrict] = useState("");
  const [areaType, setAreaType] = useState("");

  // Data
  const [results, setResults] = useState<DashboardResult[]>([]);
  const [totalAvailable, setTotalAvailable] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Map interaction
  const [highlightedCode, setHighlightedCode] = useState<string | null>(null);

  // Compare mode
  const [compareCodes, setCompareCodes] = useState<string[]>([]);
  const [showCompareModal, setShowCompareModal] = useState(false);

  // Mobile filter toggle
  const [showFilters, setShowFilters] = useState(true);

  // Card refs for scroll-to
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // Initialize filters from localStorage
  useEffect(() => {
    const storedBudgetMin = localStorage.getItem("builder_curation_budget_min");
    const storedBudgetMax = localStorage.getItem("builder_curation_budget_max");
    const storedDistricts = localStorage.getItem("builder_curation_districts");
    const storedIndustry = localStorage.getItem("builder_curation_industry_code");

    if (storedBudgetMin) setBudgetMin(Number(storedBudgetMin));
    if (storedBudgetMax) setBudgetMax(Number(storedBudgetMax));
    if (storedDistricts && storedDistricts !== "서울 전체") setDistrict(storedDistricts);
    if (storedIndustry) {
      setIndustry({
        code: storedIndustry,
        name: INDUSTRY_NAMES[storedIndustry] || "카페",
        icon: INDUSTRY_ICONS[storedIndustry] || "☕",
      });
    }
  }, []);

  // Debounced filter values
  const debouncedBudgetMin = useDebounce(budgetMin, 300);
  const debouncedBudgetMax = useDebounce(budgetMax, 300);
  const debouncedDistrict = useDebounce(district, 300);
  const debouncedAreaType = useDebounce(areaType, 300);

  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        industry_code: industry.code,
        budget_min: String(debouncedBudgetMin),
        budget_max: String(debouncedBudgetMax),
        limit: "10",
      });
      if (debouncedDistrict) params.set("district_filter", debouncedDistrict);
      if (debouncedAreaType) params.set("area_type", debouncedAreaType);

      const res = await fetch(`${API_BASE}/recommendations/dashboard?${params}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data: DashboardResponse = await res.json();
      setResults(data.results);
      setTotalAvailable(data.total_available);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "데이터를 불러올 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }, [industry.code, debouncedBudgetMin, debouncedBudgetMax, debouncedDistrict, debouncedAreaType]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Map markers (rich data for InteractiveMap)
  const mapMarkers: InteractiveMarkerData[] = useMemo(
    () =>
      results.map((r) => ({
        district_code: r.district_code,
        district_name: r.district_name,
        district_type: r.district_type,
        lat: r.lat,
        lng: r.lng,
        rank: r.rank,
        success_probability: r.success_probability,
        estimated_rent: r.estimated_rent,
        store_count: r.store_count,
        survival_rate: r.survival_rate,
        peak_time: r.peak_time,
        industry_code: industry.code,
        scorecard_total: r.scorecard_total,
      })),
    [results, industry.code]
  );

  // Card↔Map sync: when marker clicked on map, scroll to card
  const handleMarkerClick = useCallback((districtCode: string) => {
    const el = cardRefs.current[districtCode];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      setHighlightedCode(districtCode);
      // Auto-clear highlight after 2s
      setTimeout(() => setHighlightedCode((prev) => (prev === districtCode ? null : prev)), 2000);
    }
  }, []);

  // Compare toggle
  const handleCompareToggle = useCallback((code: string) => {
    setCompareCodes((prev) => {
      if (prev.includes(code)) return prev.filter((c) => c !== code);
      if (prev.length >= MAX_COMPARE) return prev;
      return [...prev, code];
    });
  }, []);

  const compareItems = useMemo(
    () => results.filter((r) => compareCodes.includes(r.district_code)),
    [results, compareCodes]
  );

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-200/60 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm">
              <MapPin size={16} className="text-white" />
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              SpotPick
            </span>
          </Link>

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline text-sm text-slate-500">
              {industry.icon} {industry.name}
            </span>
            <Link
              href="/"
              className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl transition-colors"
            >
              <Search size={14} />
              <span className="hidden sm:inline">다시 검색</span>
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* Filter bar */}
        <div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="sm:hidden flex items-center gap-2 text-sm font-medium text-blue-600 mb-2"
          >
            <SlidersHorizontal size={14} />
            {showFilters ? "필터 접기" : "필터 열기"}
          </button>
          <div className={cn("transition-all", showFilters ? "block" : "hidden sm:block")}>
            <FilterBar
              budgetMin={budgetMin}
              budgetMax={budgetMax}
              district={district}
              areaType={areaType}
              onBudgetMinChange={setBudgetMin}
              onBudgetMaxChange={setBudgetMax}
              onDistrictChange={setDistrict}
              onAreaTypeChange={setAreaType}
            />
          </div>
        </div>

        {/* Filter summary banner */}
        {(() => {
          const hasFilters = district || areaType || budgetMin !== 3000 || budgetMax !== 20000;
          const parts: string[] = [];
          parts.push(`${industry.icon} ${industry.name}`);
          parts.push(district || "서울 전체");
          if (areaType) parts.push(areaType);
          if (budgetMin !== 3000 || budgetMax !== 20000) {
            parts.push(`예산 ${formatBudgetLabel(budgetMin)}~${formatBudgetLabel(budgetMax)}원`);
          }

          return (
            <div className={cn(
              "rounded-xl px-4 py-3 text-sm flex items-center gap-2",
              hasFilters
                ? "bg-blue-50 border border-blue-200 text-blue-700"
                : "bg-slate-50 border border-slate-200 text-slate-600"
            )}>
              <Info size={16} className="flex-shrink-0" />
              {hasFilters ? (
                <span>
                  <span className="font-semibold">{parts.join(" · ")}</span> 기준 추천 결과입니다
                </span>
              ) : (
                <span>전체 업종 · 서울 전체 기준 추천 결과입니다. 필터를 설정하면 맞춤 결과를 볼 수 있습니다.</span>
              )}
            </div>
          );
        })()}

        {/* Results count */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-600">
            <span className="font-bold text-blue-600">{totalAvailable}개</span> 상권 중{" "}
            <span className="font-bold text-slate-800">TOP {results.length}</span> 추천
          </p>
          {compareCodes.length === 0 && results.length > 1 && (
            <p className="text-xs text-slate-400">
              카드 체크박스를 눌러 비교해보세요
            </p>
          )}
        </div>

        {/* Main layout: cards + map */}
        <div className="flex flex-col lg:flex-row gap-5">
          {/* Cards (left) */}
          <div className="w-full lg:w-[58%] space-y-4">
            {loading && (
              <>
                <CardSkeleton />
                <CardSkeleton />
                <CardSkeleton />
              </>
            )}

            {!loading && error && (
              <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-center">
                <p className="text-rose-600 text-sm font-medium">{error}</p>
                <button
                  onClick={fetchData}
                  className="mt-3 px-4 py-2 bg-rose-600 text-white text-sm rounded-xl hover:bg-rose-700 transition-colors"
                >
                  다시 시도
                </button>
              </div>
            )}

            {!loading && !error && results.length === 0 && (
              <div className="bg-slate-50 border border-slate-200 rounded-2xl p-8 text-center">
                <MapPin size={40} className="mx-auto mb-3 text-slate-300" />
                <p className="text-slate-600 font-medium mb-1">조건에 맞는 상권이 없습니다</p>
                <p className="text-slate-400 text-sm mb-4">필터를 조정해보세요.</p>
                <div className="flex flex-col sm:flex-row items-center justify-center gap-2">
                  <button
                    onClick={() => {
                      setBudgetMin(3000);
                      setBudgetMax(20000);
                      setDistrict("");
                      setAreaType("");
                    }}
                    className="px-4 py-2 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors"
                  >
                    필터 초기화
                  </button>
                  <Link
                    href="/chat"
                    className="px-4 py-2 bg-slate-200 text-slate-700 text-sm font-semibold rounded-xl hover:bg-slate-300 transition-colors"
                  >
                    AI에게 질문하기
                  </Link>
                </div>
              </div>
            )}

            {!loading &&
              !error &&
              results.map((r) => (
                <ResultCard
                  key={r.district_code}
                  result={r}
                  industryCode={industry.code}
                  industryName={industry.name}
                  isHighlighted={highlightedCode === r.district_code}
                  isCompareSelected={compareCodes.includes(r.district_code)}
                  compareDisabled={compareCodes.length >= MAX_COMPARE}
                  onHover={setHighlightedCode}
                  onCompareToggle={handleCompareToggle}
                  cardRef={(el) => { cardRefs.current[r.district_code] = el; }}
                />
              ))}
          </div>

          {/* Map (right) — on mobile stacks above cards via order */}
          <div className="w-full lg:w-[42%] order-first lg:order-last">
            <div className="lg:sticky lg:top-20">
              <InteractiveMap
                markers={mapMarkers}
                highlightedCode={highlightedCode}
                onMarkerClick={handleMarkerClick}
                onMarkerHover={setHighlightedCode}
                height={480}
              />

              {/* Mini legend for quick glance */}
              {!loading && results.length > 0 && (
                <div className="mt-3 bg-white rounded-xl border border-slate-200/60 p-3">
                  <p className="text-xs font-medium text-slate-500 mb-2">상위 추천</p>
                  <div className="space-y-1.5">
                    {results.slice(0, 5).map((r) => {
                      const vStyle = verdictStyle(r.verdict);
                      const score = Math.round(r.success_probability * 100);
                      return (
                        <button
                          key={r.district_code}
                          onMouseEnter={() => setHighlightedCode(r.district_code)}
                          onMouseLeave={() => setHighlightedCode(null)}
                          onClick={() => handleMarkerClick(r.district_code)}
                          className={cn(
                            "w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left text-xs transition-colors",
                            highlightedCode === r.district_code
                              ? "bg-blue-50 text-blue-700"
                              : "hover:bg-slate-50 text-slate-600"
                          )}
                        >
                          <span className={cn(
                            "w-5 h-5 rounded-full text-white text-[10px] font-bold flex items-center justify-center flex-shrink-0 bg-gradient-to-br",
                            score >= 80 ? "from-emerald-500 to-emerald-600"
                              : score >= 60 ? "from-amber-500 to-amber-600"
                                : "from-rose-500 to-rose-600"
                          )}>
                            {r.rank}
                          </span>
                          <span className="truncate flex-1 font-medium">{r.district_name}</span>
                          <span className={cn("font-bold text-[11px]", vStyle.color)}>
                            {score}%
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Compare floating bar */}
      {compareCodes.length > 0 && (
        <CompareBar
          selectedCodes={compareCodes}
          results={results}
          onRemove={(code) => setCompareCodes((prev) => prev.filter((c) => c !== code))}
          onClear={() => setCompareCodes([])}
          onCompare={() => setShowCompareModal(true)}
        />
      )}

      {/* Compare modal */}
      {showCompareModal && compareItems.length >= 2 && (
        <CompareModal
          items={compareItems}
          industryCode={industry.code}
          onClose={() => setShowCompareModal(false)}
        />
      )}

      {/* AI Chat FAB */}
      <Link
        href="/chat"
        className={cn(
          "fixed bottom-6 right-6 z-50",
          "flex items-center gap-2 px-5 py-3.5",
          "bg-gradient-to-r from-blue-500 to-indigo-600 text-white",
          "rounded-full shadow-lg hover:shadow-xl",
          "hover:from-blue-600 hover:to-indigo-700",
          "transition-all duration-300",
          "animate-bounce-slow"
        )}
      >
        <MessageCircle size={18} />
        <span className="text-sm font-semibold">AI에게 질문하기</span>
      </Link>

      {/* Animations */}
      <style jsx global>{`
        @keyframes bounce-slow {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-4px); }
        }
        .animate-bounce-slow {
          animation: bounce-slow 3s ease-in-out infinite;
        }
        @keyframes slide-up {
          from { opacity: 0; transform: translate(-50%, 20px); }
          to { opacity: 1; transform: translate(-50%, 0); }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
        .interactive-map-popup .maplibregl-popup-content {
          border-radius: 12px !important;
          padding: 12px !important;
          box-shadow: 0 8px 30px rgba(0,0,0,0.12) !important;
        }
        .interactive-map-popup .maplibregl-popup-tip {
          border-top-color: white !important;
        }
      `}</style>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page (wraps in Suspense for useSearchParams)
// ---------------------------------------------------------------------------

export default function ResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center">
          <div className="text-center text-slate-500">
            <MapPin size={40} className="mx-auto mb-3 animate-pulse" />
            <p className="text-sm">로딩 중...</p>
          </div>
        </div>
      }
    >
      <ResultsContent />
    </Suspense>
  );
}
