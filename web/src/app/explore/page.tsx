"use client";

import {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
  Suspense,
} from "react";
import Map, { Marker, NavigationControl } from "react-map-gl/maplibre";
import type { MapRef } from "react-map-gl/maplibre";
import {
  MapPin,
  Layers,
  ChevronRight,
  ChevronDown,
  TrendingUp,
  DollarSign,
  Store,
  Shield,
  Users,
  FileText,
  SlidersHorizontal,
  Search,
  MessageCircle,
  ArrowLeft,
  Trophy,
  Minus,
  BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";
import "maplibre-gl/dist/maplibre-gl.css";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

const MAP_STYLE = {
  version: 8 as const,
  sources: {
    osm: {
      type: "raster" as const,
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  },
  layers: [
    {
      id: "osm",
      type: "raster" as const,
      source: "osm",
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

const INDUSTRIES: { code: string; name: string; icon: string }[] = [
  { code: "CS100010", name: "카페", icon: "☕" },
  { code: "CS100001", name: "한식", icon: "🍚" },
  { code: "CS100007", name: "치킨", icon: "🍗" },
  { code: "CS100005", name: "베이커리", icon: "🍞" },
  { code: "CS100002", name: "중식", icon: "🥟" },
  { code: "CS100003", name: "일식", icon: "🍣" },
  { code: "CS100004", name: "양식", icon: "🍝" },
  { code: "CS100006", name: "패스트푸드", icon: "🍔" },
  { code: "CS100008", name: "분식", icon: "🍜" },
  { code: "CS100009", name: "호프/주점", icon: "🍺" },
];

type DataLayer = "score" | "sales" | "traffic" | "stores" | "survival";

const DATA_LAYERS: { key: DataLayer; label: string }[] = [
  { key: "score", label: "종합점수" },
  { key: "sales", label: "매출" },
  { key: "traffic", label: "유동인구" },
  { key: "stores", label: "점포수" },
  { key: "survival", label: "생존율" },
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GuSummary {
  gu_name: string;
  center_lat: number;
  center_lng: number;
  avg_score: number;
  avg_monthly_sales: number;
  total_foot_traffic: number;
  total_store_count: number;
  avg_survival_rate: number;
  district_count: number;
  new_stores_total: number;
  closed_stores_total: number;
}

interface DistrictGeo {
  district_code: string;
  district_name: string;
  district_type: string;
  lat: number;
  lng: number;
  monthly_sales: number;
  sales_per_store: number;
  store_count: number;
  survival_rate: number;
  foot_traffic_total: number;
  new_stores: number;
  closed_stores: number;
  peak_time: string;
  main_age_group: string;
  change_indicator: string;
}

interface IndustryRank {
  industry_code: string;
  industry_name: string;
  score: number;
  store_count: number;
  new_stores: number;
  closed_stores: number;
  franchise_stores: number;
  monthly_sales: number;
  survival_rate: number;
  reason: string;
  rank: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreColor(score: number) {
  if (score >= 80)
    return {
      bg: "bg-emerald-500",
      text: "text-emerald-700",
      border: "border-emerald-400",
      light: "bg-emerald-50",
      gradient: "from-emerald-500 to-emerald-600",
    };
  if (score >= 60)
    return {
      bg: "bg-amber-500",
      text: "text-amber-700",
      border: "border-amber-400",
      light: "bg-amber-50",
      gradient: "from-amber-500 to-amber-600",
    };
  return {
    bg: "bg-rose-500",
    text: "text-rose-700",
    border: "border-rose-400",
    light: "bg-rose-50",
    gradient: "from-rose-500 to-rose-600",
  };
}

function formatMan(value: number): string {
  const man = Math.round(value / 10000);
  return `${man.toLocaleString()}만원`;
}

function formatManShort(value: number): string {
  const man = Math.round(value / 10000);
  if (man >= 10000) return `${(man / 10000).toFixed(1)}억`;
  return `${man.toLocaleString()}만`;
}

function formatTraffic(value: number): string {
  const man = Math.round(value / 10000);
  if (man <= 0) return "-";
  return `${man.toLocaleString()}만명`;
}

/** Get the metric value for a gu, depending on active data layer */
function guMetricValue(gu: GuSummary, layer: DataLayer): number {
  switch (layer) {
    case "score":
      return gu.avg_score;
    case "sales":
      return gu.avg_monthly_sales / 10000; // normalized to 만
    case "traffic":
      return gu.total_foot_traffic / 10000;
    case "stores":
      return gu.total_store_count;
    case "survival":
      return gu.avg_survival_rate * 100;
  }
}

/** Map metric to a 0-100 color scale based on layer */
function metricToColorScore(value: number, layer: DataLayer, allValues: number[]): number {
  if (allValues.length === 0) return 50;
  const min = Math.min(...allValues);
  const max = Math.max(...allValues);
  if (max === min) return 70;
  const normalized = ((value - min) / (max - min)) * 100;
  return normalized;
}

function districtScore(d: DistrictGeo, layer: DataLayer): number {
  switch (layer) {
    case "score": {
      const sr = d.survival_rate * 40;
      const sales = Math.min(1, d.sales_per_store / 50_000_000) * 35;
      const growth = Math.min(1, (d.new_stores + 1) / Math.max(1, d.closed_stores + 1)) * 25;
      return Math.round(sr + sales + growth);
    }
    case "sales":
      return d.monthly_sales / 10000;
    case "traffic":
      return d.foot_traffic_total / 10000;
    case "stores":
      return d.store_count;
    case "survival":
      return d.survival_rate * 100;
  }
}

// ---------------------------------------------------------------------------
// GuMarker — circle marker for gu level
// ---------------------------------------------------------------------------

function GuMarker({
  gu,
  colorScore,
  size,
  isSelected,
  onClick,
}: {
  gu: GuSummary;
  colorScore: number;
  size: number;
  isSelected: boolean;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const sc = scoreColor(colorScore);

  return (
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Glow radius */}
      <div
        className={cn(
          "absolute rounded-full transition-all duration-300",
          isSelected ? "opacity-30" : hovered ? "opacity-20" : "opacity-10",
          sc.bg
        )}
        style={{
          width: size * 2.2,
          height: size * 2.2,
          left: -(size * 0.6),
          top: -(size * 0.6),
          filter: "blur(8px)",
        }}
      />

      {/* Main circle */}
      <button
        onClick={onClick}
        className={cn(
          "relative flex flex-col items-center justify-center rounded-full",
          "bg-gradient-to-br shadow-lg transition-all duration-200",
          "border-2 border-white/80",
          sc.gradient,
          isSelected && "ring-4 ring-blue-400 scale-110 z-20",
          !isSelected && hovered && "scale-110 z-10",
        )}
        style={{ width: size, height: size }}
      >
        <span className="text-white font-bold text-[11px] leading-tight truncate px-1">
          {gu.gu_name.replace("구", "")}
        </span>
        <span className="text-white/90 text-[10px] font-semibold">
          {Math.round(colorScore)}
        </span>
      </button>

      {/* District count badge */}
      <div className="absolute -top-1 -right-1 bg-white rounded-full shadow-md border border-slate-200 px-1.5 py-0.5 text-[9px] font-bold text-slate-600 z-30">
        {gu.district_count}
      </div>

      {/* Hover tooltip */}
      {hovered && !isSelected && (
        <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 z-50 pointer-events-none">
          <div className="bg-slate-800/95 backdrop-blur-sm text-white rounded-xl px-3.5 py-2.5 shadow-xl text-xs whitespace-nowrap min-w-[160px]">
            <p className="font-bold text-sm mb-1.5">{gu.gu_name}</p>
            <div className="space-y-1 text-slate-200">
              <p>📊 종합 <span className="text-white font-semibold">{Math.round(colorScore)}점</span></p>
              <p>💰 평균매출 <span className="text-white font-semibold">{formatManShort(gu.avg_monthly_sales)}</span></p>
              <p>👥 유동인구 <span className="text-white font-semibold">{formatTraffic(gu.total_foot_traffic)}</span></p>
              <p>🏪 점포 <span className="text-white font-semibold">{gu.total_store_count}개</span></p>
              <p>📈 생존율 <span className="text-white font-semibold">{Math.round(gu.avg_survival_rate * 100)}%</span></p>
            </div>
            <p className="text-blue-300 mt-1.5 text-[10px]">클릭하여 상세 보기 →</p>
            {/* Arrow */}
            <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-[6px] border-r-[6px] border-t-[6px] border-l-transparent border-r-transparent border-t-slate-800/95" />
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// DistrictMarker — smaller circle for district level
// ---------------------------------------------------------------------------

function DistrictMarker({
  district,
  colorScore,
  isSelected,
  onClick,
}: {
  district: DistrictGeo;
  colorScore: number;
  isSelected: boolean;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const sc = scoreColor(colorScore);

  return (
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        onClick={onClick}
        className={cn(
          "relative flex items-center justify-center rounded-full",
          "bg-gradient-to-br shadow-md transition-all duration-200",
          "border-2 border-white/80",
          sc.gradient,
          isSelected && "ring-3 ring-blue-400 scale-125 z-20",
          !isSelected && hovered && "scale-115 z-10"
        )}
        style={{ width: 34, height: 34 }}
      >
        <span className="text-white font-bold text-[10px]">
          {Math.round(colorScore)}
        </span>
      </button>

      {/* Hover tooltip */}
      {hovered && !isSelected && (
        <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 z-50 pointer-events-none">
          <div className="bg-slate-800/95 backdrop-blur-sm text-white rounded-xl px-3 py-2 shadow-xl text-xs whitespace-nowrap min-w-[150px]">
            <p className="font-bold text-[11px] mb-1">{district.district_name}</p>
            <span className="inline-block px-1.5 py-0.5 rounded text-[9px] bg-white/20 mb-1.5">{district.district_type}</span>
            <div className="space-y-0.5 text-slate-200 text-[10px]">
              <p>💰 매출 <span className="text-white font-semibold">{formatManShort(district.monthly_sales)}</span></p>
              <p>🏪 점포 <span className="text-white font-semibold">{district.store_count}개</span></p>
              <p>📈 생존율 <span className="text-white font-semibold">{Math.round(district.survival_rate * 100)}%</span></p>
              {district.peak_time && <p>⏰ 피크 <span className="text-white font-semibold">{district.peak_time}</span></p>}
            </div>
            <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-[5px] border-r-[5px] border-t-[5px] border-l-transparent border-r-transparent border-t-slate-800/95" />
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Left Panel — Desktop sidebar
// ---------------------------------------------------------------------------

function LeftPanel({
  selectedGu,
  selectedDistrict,
  guData,
  districts,
  industryRankings,
  industryCode,
  loadingDistricts,
  loadingRankings,
  onBack,
}: {
  selectedGu: GuSummary | null;
  selectedDistrict: DistrictGeo | null;
  guData: GuSummary[];
  districts: DistrictGeo[];
  industryRankings: IndustryRank[];
  industryCode: string;
  loadingDistricts: boolean;
  loadingRankings: boolean;
  onBack: () => void;
}) {
  // Default: show Seoul overview
  if (!selectedGu) {
    const totalDistricts = guData.reduce((s, g) => s + g.district_count, 0);
    const avgScore =
      guData.length > 0
        ? Math.round(guData.reduce((s, g) => s + g.avg_score, 0) / guData.length)
        : 0;
    return (
      <div className="h-full overflow-y-auto p-4 space-y-4">
        <div className="text-center py-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mx-auto mb-3 shadow-lg">
            <MapPin size={24} className="text-white" />
          </div>
          <h2 className="text-lg font-bold text-slate-800">서울 상권 지도</h2>
          <p className="text-sm text-slate-500 mt-1">
            자치구를 클릭하여 상세 정보를 확인하세요
          </p>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <div className="bg-blue-50 rounded-xl p-3 text-center">
            <p className="text-lg font-bold text-blue-700">{guData.length}</p>
            <p className="text-[10px] text-blue-600">자치구</p>
          </div>
          <div className="bg-emerald-50 rounded-xl p-3 text-center">
            <p className="text-lg font-bold text-emerald-700">
              {totalDistricts}
            </p>
            <p className="text-[10px] text-emerald-600">상권</p>
          </div>
          <div className="bg-amber-50 rounded-xl p-3 text-center">
            <p className="text-lg font-bold text-amber-700">{avgScore}점</p>
            <p className="text-[10px] text-amber-600">평균</p>
          </div>
        </div>

        {/* Top gus list */}
        <div>
          <h3 className="text-xs font-semibold text-slate-500 mb-2">
            자치구 순위 TOP 5
          </h3>
          <div className="space-y-1.5">
            {guData.slice(0, 5).map((gu, i) => {
              const sc = scoreColor(gu.avg_score);
              return (
                <div
                  key={gu.gu_name}
                  className="flex items-center gap-2 px-3 py-2 bg-white rounded-lg border border-slate-100"
                >
                  <span
                    className={cn(
                      "w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold bg-gradient-to-br",
                      sc.gradient
                    )}
                  >
                    {i + 1}
                  </span>
                  <span className="flex-1 text-sm font-medium text-slate-700">
                    {gu.gu_name}
                  </span>
                  <span className={cn("text-sm font-bold", sc.text)}>
                    {Math.round(gu.avg_score)}점
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // Selected gu — show gu detail
  if (!selectedDistrict) {
    const sc = scoreColor(selectedGu.avg_score);
    return (
      <div className="h-full overflow-y-auto p-4 space-y-4">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
        >
          <ArrowLeft size={14} />
          서울 전체
        </button>

        <div>
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-xl font-bold text-slate-800">
              {selectedGu.gu_name}
            </h2>
            <span
              className={cn(
                "px-2.5 py-1 rounded-full text-sm font-bold",
                sc.light,
                sc.text
              )}
            >
              {Math.round(selectedGu.avg_score)}점
            </span>
          </div>

          {/* Score bar */}
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden mb-4">
            <div
              className={cn(
                "h-full rounded-full bg-gradient-to-r transition-all duration-500",
                selectedGu.avg_score >= 80
                  ? "from-emerald-500 to-emerald-400"
                  : selectedGu.avg_score >= 60
                    ? "from-amber-500 to-amber-400"
                    : "from-rose-500 to-rose-400"
              )}
              style={{ width: `${Math.min(100, selectedGu.avg_score)}%` }}
            />
          </div>
        </div>

        {/* Metrics grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-xl border border-slate-100 p-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
              <DollarSign size={12} className="text-blue-500" />
              평균 매출
            </div>
            <p className="text-sm font-bold text-slate-800">
              {formatMan(selectedGu.avg_monthly_sales)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-slate-100 p-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
              <Users size={12} className="text-violet-500" />
              유동인구
            </div>
            <p className="text-sm font-bold text-slate-800">
              {formatTraffic(selectedGu.total_foot_traffic)}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-slate-100 p-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
              <Store size={12} className="text-orange-500" />
              점포수
            </div>
            <p className="text-sm font-bold text-slate-800">
              {selectedGu.total_store_count.toLocaleString()}개
            </p>
          </div>
          <div className="bg-white rounded-xl border border-slate-100 p-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
              <Shield size={12} className="text-indigo-500" />
              평균 생존율
            </div>
            <p className="text-sm font-bold text-slate-800">
              {Math.round(selectedGu.avg_survival_rate * 100)}%
            </p>
          </div>
        </div>

        {/* New/Closed stats */}
        <div className="flex items-center gap-3 text-sm">
          <span className="flex items-center gap-1 text-emerald-600">
            <TrendingUp size={14} />
            신규 {selectedGu.new_stores_total}개
          </span>
          <span className="text-slate-300">|</span>
          <span className="flex items-center gap-1 text-rose-600">
            <Minus size={14} />
            폐업 {selectedGu.closed_stores_total}개
          </span>
        </div>

        {/* Districts in this gu */}
        <div>
          <h3 className="text-xs font-semibold text-slate-500 mb-2">
            {selectedGu.gu_name} 상권 ({selectedGu.district_count}개)
          </h3>
          {loadingDistricts ? (
            <div className="space-y-2">
              {[1, 2, 3].map((k) => (
                <div
                  key={k}
                  className="h-12 bg-slate-100 rounded-lg animate-pulse"
                />
              ))}
            </div>
          ) : (
            <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
              {districts.map((d) => {
                const dScore = districtScore(d, "score");
                const dsc = scoreColor(dScore);
                return (
                  <div
                    key={d.district_code}
                    className="flex items-center gap-2 px-3 py-2 bg-white rounded-lg border border-slate-100 hover:border-blue-200 hover:bg-blue-50/30 cursor-default text-sm"
                  >
                    <span
                      className={cn(
                        "w-2 h-2 rounded-full flex-shrink-0",
                        dsc.bg
                      )}
                    />
                    <span className="flex-1 text-slate-700 truncate">
                      {d.district_name}
                    </span>
                    <span className="text-xs text-slate-400">
                      {formatManShort(d.monthly_sales)}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    );
  }

  // District detail
  const dScore = districtScore(selectedDistrict, "score");
  const dsc = scoreColor(dScore);

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
      >
        <ArrowLeft size={14} />
        {selectedGu.gu_name}
      </button>

      <div>
        <div className="flex items-center gap-2 mb-1">
          <h2 className="text-lg font-bold text-slate-800">
            {selectedDistrict.district_name}
          </h2>
          <span
            className={cn(
              "px-2 py-0.5 rounded-full text-xs font-bold",
              dsc.light,
              dsc.text
            )}
          >
            {dScore}점
          </span>
        </div>
        <span className="text-xs text-slate-400">
          {selectedDistrict.district_type}
        </span>
      </div>

      {/* Score bar */}
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full bg-gradient-to-r",
            dScore >= 80
              ? "from-emerald-500 to-emerald-400"
              : dScore >= 60
                ? "from-amber-500 to-amber-400"
                : "from-rose-500 to-rose-400"
          )}
          style={{ width: `${Math.min(100, dScore)}%` }}
        />
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded-xl border border-slate-100 p-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
            <DollarSign size={12} className="text-blue-500" />
            월매출
          </div>
          <p className="text-sm font-bold text-slate-800">
            {formatMan(selectedDistrict.monthly_sales)}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-100 p-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
            <Users size={12} className="text-violet-500" />
            유동인구
          </div>
          <p className="text-sm font-bold text-slate-800">
            {formatTraffic(selectedDistrict.foot_traffic_total)}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-100 p-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
            <Store size={12} className="text-orange-500" />
            점포수
          </div>
          <p className="text-sm font-bold text-slate-800">
            {selectedDistrict.store_count}개
          </p>
        </div>
        <div className="bg-white rounded-xl border border-slate-100 p-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
            <Shield size={12} className="text-indigo-500" />
            생존율
          </div>
          <p className="text-sm font-bold text-slate-800">
            {Math.round(selectedDistrict.survival_rate * 100)}%
          </p>
        </div>
      </div>

      {/* Action buttons */}
      <div className="space-y-2">
        <Link
          href={`/report?district_code=${selectedDistrict.district_code}&industry_code=${industryCode}`}
          className="flex items-center justify-center gap-2 w-full py-2.5 bg-gradient-to-r from-blue-500 to-indigo-600 text-white text-sm font-semibold rounded-xl shadow-sm hover:shadow-md transition-all"
        >
          <FileText size={14} />
          상세 보기
          <ChevronRight size={14} />
        </Link>
        <div className="grid grid-cols-2 gap-2">
          <Link
            href={`/simulator?district_code=${selectedDistrict.district_code}&industry_code=${industryCode}`}
            className="flex items-center justify-center gap-1.5 py-2 bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-200 transition-colors"
          >
            <SlidersHorizontal size={12} />
            시뮬레이션
          </Link>
          <Link
            href={`/business-plan?district_code=${selectedDistrict.district_code}&industry_code=${industryCode}`}
            className="flex items-center justify-center gap-1.5 py-2 bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-200 transition-colors"
          >
            <FileText size={12} />
            사업계획서
          </Link>
        </div>
      </div>

      {/* Industry ranking — "이 동네 뭐가 잘 될까?" */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <Trophy size={14} className="text-amber-500" />
          <h3 className="text-sm font-bold text-slate-700">
            이 동네 뭐가 잘 될까?
          </h3>
        </div>
        {loadingRankings ? (
          <div className="space-y-2">
            {[1, 2, 3].map((k) => (
              <div
                key={k}
                className="h-10 bg-slate-100 rounded-lg animate-pulse"
              />
            ))}
          </div>
        ) : industryRankings.length === 0 ? (
          <p className="text-xs text-slate-400">업종 데이터가 없습니다</p>
        ) : (
          <div className="space-y-1.5">
            {industryRankings.map((r) => {
              const ind = INDUSTRIES.find((i) => i.code === r.industry_code);
              const rsc = scoreColor(r.score);
              return (
                <div
                  key={r.industry_code}
                  className="flex items-center gap-2 px-3 py-2 bg-white rounded-lg border border-slate-100"
                >
                  <span
                    className={cn(
                      "w-6 h-6 rounded-full flex items-center justify-center text-white text-[10px] font-bold bg-gradient-to-br",
                      rsc.gradient
                    )}
                  >
                    {r.rank}
                  </span>
                  <span className="text-sm mr-1">{ind?.icon || "🏪"}</span>
                  <span className="flex-1 text-sm font-medium text-slate-700">
                    {r.industry_name}
                  </span>
                  <span className={cn("text-xs font-bold", rsc.text)}>
                    {Math.round(r.score)}점
                  </span>
                </div>
              );
            })}
            {industryRankings.length > 0 && (
              <div className="mt-1">
                {industryRankings.slice(0, 3).map((r) => (
                  <p
                    key={r.industry_code}
                    className="text-[10px] text-slate-400 leading-relaxed"
                  >
                    #{r.rank} {r.industry_name}: {r.reason}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Mobile Bottom Sheet
// ---------------------------------------------------------------------------

type SheetHeight = "collapsed" | "half" | "full";

function BottomSheet({
  children,
  height,
  onChangeHeight,
}: {
  children: React.ReactNode;
  height: SheetHeight;
  onChangeHeight: (h: SheetHeight) => void;
}) {
  const sheetRef = useRef<HTMLDivElement>(null);
  const startYRef = useRef(0);
  const startHeightRef = useRef<SheetHeight>("collapsed");

  const heightClass =
    height === "full"
      ? "h-[85vh]"
      : height === "half"
        ? "h-[45vh]"
        : "h-[120px]";

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      startYRef.current = e.touches[0].clientY;
      startHeightRef.current = height;
    },
    [height]
  );

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      const diff = startYRef.current - e.changedTouches[0].clientY;
      if (Math.abs(diff) < 30) return; // ignore small drags

      if (diff > 0) {
        // swipe up
        if (startHeightRef.current === "collapsed") onChangeHeight("half");
        else if (startHeightRef.current === "half") onChangeHeight("full");
      } else {
        // swipe down
        if (startHeightRef.current === "full") onChangeHeight("half");
        else if (startHeightRef.current === "half")
          onChangeHeight("collapsed");
      }
    },
    [onChangeHeight]
  );

  return (
    <div
      ref={sheetRef}
      className={cn(
        "fixed bottom-0 left-0 right-0 z-30 bg-white rounded-t-2xl shadow-2xl border-t border-slate-200 transition-all duration-300 flex flex-col",
        heightClass
      )}
    >
      {/* Drag handle */}
      <div
        className="flex justify-center py-2 cursor-grab"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onClick={() =>
          onChangeHeight(
            height === "collapsed"
              ? "half"
              : height === "half"
                ? "full"
                : "collapsed"
          )
        }
      >
        <div className="w-10 h-1 bg-slate-300 rounded-full" />
      </div>
      <div className="flex-1 overflow-y-auto">{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Score Legend
// ---------------------------------------------------------------------------

function ScoreLegend({ layer }: { layer: DataLayer }) {
  const labels =
    layer === "score"
      ? ["80+ 추천", "60~79 보통", "60 미만 주의"]
      : ["상위", "중간", "하위"];

  return (
    <div className="absolute bottom-3 right-3 z-10 bg-white/95 backdrop-blur-sm rounded-lg px-3 py-2 shadow-md border border-slate-100 flex items-center gap-3">
      <span className="flex items-center gap-1.5 text-[10px]">
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
        <span className="text-slate-600 font-medium">{labels[0]}</span>
      </span>
      <span className="flex items-center gap-1.5 text-[10px]">
        <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
        <span className="text-slate-600 font-medium">{labels[1]}</span>
      </span>
      <span className="flex items-center gap-1.5 text-[10px]">
        <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
        <span className="text-slate-600 font-medium">{labels[2]}</span>
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Explore Content
// ---------------------------------------------------------------------------

function ExploreContent() {
  const mapRef = useRef<MapRef>(null);

  // State
  const [industryCode, setIndustryCode] = useState("CS100010");
  const [dataLayer, setDataLayer] = useState<DataLayer>("score");
  const [showLayerPicker, setShowLayerPicker] = useState(false);

  // Data
  const [guData, setGuData] = useState<GuSummary[]>([]);
  const [districts, setDistricts] = useState<DistrictGeo[]>([]);
  const [industryRankings, setIndustryRankings] = useState<IndustryRank[]>([]);

  // Selection
  const [selectedGu, setSelectedGu] = useState<GuSummary | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<DistrictGeo | null>(
    null
  );

  // Loading
  const [loadingGu, setLoadingGu] = useState(true);
  const [loadingDistricts, setLoadingDistricts] = useState(false);
  const [loadingRankings, setLoadingRankings] = useState(false);

  // Zoom tracking
  const [zoom, setZoom] = useState(11);
  const [viewCenter, setViewCenter] = useState<[number, number]>([126.978, 37.566]);

  // Mobile bottom sheet
  const [sheetHeight, setSheetHeight] = useState<SheetHeight>("collapsed");

  // Guide hint
  const [showGuide, setShowGuide] = useState(true);

  // Auto-dismiss guide after 5s
  useEffect(() => {
    if (showGuide) {
      const t = setTimeout(() => setShowGuide(false), 6000);
      return () => clearTimeout(t);
    }
  }, [showGuide]);

  // ── Fetch gu summary ──
  const fetchGuSummary = useCallback(async (code: string) => {
    setLoadingGu(true);
    try {
      const res = await fetch(
        `${API_BASE}/explore/gu-summary?industry_code=${code}`
      );
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      setGuData(data.gu_list || []);
    } catch {
      setGuData([]);
    } finally {
      setLoadingGu(false);
    }
  }, []);

  // ── Fetch districts for a gu ──
  const fetchDistricts = useCallback(
    async (gu: string) => {
      setLoadingDistricts(true);
      try {
        const res = await fetch(
          `${API_BASE}/explore/districts-geo?industry_code=${industryCode}&gu=${encodeURIComponent(gu)}`
        );
        if (!res.ok) throw new Error("Failed");
        const data = await res.json();
        setDistricts(data.districts || []);
      } catch {
        setDistricts([]);
      } finally {
        setLoadingDistricts(false);
      }
    },
    [industryCode]
  );

  // ── Fetch industry ranking for a district ──
  const fetchRankings = useCallback(async (districtCode: string) => {
    setLoadingRankings(true);
    try {
      const res = await fetch(
        `${API_BASE}/explore/industry-ranking?district_code=${districtCode}`
      );
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      setIndustryRankings(data.rankings || []);
    } catch {
      setIndustryRankings([]);
    } finally {
      setLoadingRankings(false);
    }
  }, []);

  // ── Initial load + industry change ──
  useEffect(() => {
    fetchGuSummary(industryCode);
    setSelectedGu(null);
    setSelectedDistrict(null);
    setDistricts([]);
    setIndustryRankings([]);
    // Reset map view
    mapRef.current?.flyTo({
      center: [126.978, 37.566],
      zoom: 11,
      duration: 800,
    });
  }, [industryCode, fetchGuSummary]);

  // ── Gu marker size normalization ──
  const markerSizes = useMemo(() => {
    if (guData.length === 0) return {};
    const counts = guData.map((g) => g.district_count);
    const min = Math.min(...counts);
    const max = Math.max(...counts);
    const range = max - min || 1;
    const sizes: Record<string, number> = {};
    for (const g of guData) {
      sizes[g.gu_name] = 30 + ((g.district_count - min) / range) * 50;
    }
    return sizes;
  }, [guData]);

  // ── Color scores for gu markers ──
  const guColorScores = useMemo(() => {
    if (dataLayer === "score") {
      // Direct score
      return Object.fromEntries(
        guData.map((g) => [g.gu_name, g.avg_score])
      );
    }
    const values = guData.map((g) => guMetricValue(g, dataLayer));
    return Object.fromEntries(
      guData.map((g, i) => [
        g.gu_name,
        metricToColorScore(values[i], dataLayer, values),
      ])
    );
  }, [guData, dataLayer]);

  // ── Handle gu click ──
  const handleGuClick = useCallback(
    (gu: GuSummary) => {
      setSelectedGu(gu);
      setSelectedDistrict(null);
      setIndustryRankings([]);
      setSheetHeight("half");

      // Fly to gu center and zoom in
      mapRef.current?.flyTo({
        center: [gu.center_lng, gu.center_lat],
        zoom: 13.5,
        duration: 800,
      });

      fetchDistricts(gu.gu_name);
    },
    [fetchDistricts]
  );

  // ── Handle district click ──
  const handleDistrictClick = useCallback(
    (d: DistrictGeo) => {
      setSelectedDistrict(d);
      setSheetHeight("half");

      mapRef.current?.flyTo({
        center: [d.lng, d.lat],
        zoom: 15,
        duration: 600,
      });

      fetchRankings(d.district_code);
    },
    [fetchRankings]
  );

  // ── Handle back ──
  const handleBack = useCallback(() => {
    if (selectedDistrict) {
      setSelectedDistrict(null);
      setIndustryRankings([]);
      if (selectedGu) {
        mapRef.current?.flyTo({
          center: [selectedGu.center_lng, selectedGu.center_lat],
          zoom: 13.5,
          duration: 600,
        });
      }
    } else {
      setSelectedGu(null);
      setDistricts([]);
      setSheetHeight("collapsed");
      mapRef.current?.flyTo({
        center: [126.978, 37.566],
        zoom: 11,
        duration: 800,
      });
    }
  }, [selectedDistrict, selectedGu]);

  // ── Auto-detect gu when user zooms in manually ──
  const autoSelectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isAutoSelectingRef = useRef(false);

  useEffect(() => {
    // When zoom >= 13 and no gu selected yet, find nearest gu to viewport center
    if (zoom >= 13 && !selectedGu && guData.length > 0 && !isAutoSelectingRef.current) {
      if (autoSelectTimerRef.current) clearTimeout(autoSelectTimerRef.current);
      autoSelectTimerRef.current = setTimeout(() => {
        const [cLng, cLat] = viewCenter;
        let closest: GuSummary | null = null;
        let minDist = Infinity;
        for (const gu of guData) {
          const dx = gu.center_lng - cLng;
          const dy = gu.center_lat - cLat;
          const dist = dx * dx + dy * dy;
          if (dist < minDist) {
            minDist = dist;
            closest = gu;
          }
        }
        if (closest) {
          isAutoSelectingRef.current = true;
          setSelectedGu(closest);
          setSelectedDistrict(null);
          setSheetHeight("half");
          fetchDistricts(closest.gu_name);
          // Reset flag after fetch
          setTimeout(() => { isAutoSelectingRef.current = false; }, 1000);
        }
      }, 400); // 400ms debounce
    }

    // When zoom < 12.5 and gu is selected, auto-deselect
    if (zoom < 12.5 && selectedGu && !isAutoSelectingRef.current) {
      setSelectedGu(null);
      setSelectedDistrict(null);
      setDistricts([]);
      setIndustryRankings([]);
      setSheetHeight("collapsed");
    }

    return () => {
      if (autoSelectTimerRef.current) clearTimeout(autoSelectTimerRef.current);
    };
  }, [zoom, viewCenter, selectedGu, guData, fetchDistricts]);

  // ── Industry chip handler ──
  const handleIndustryChange = useCallback((code: string) => {
    setIndustryCode(code);
    if (typeof window !== "undefined") {
      localStorage.setItem("builder_curation_industry_code", code);
    }
  }, []);

  // ── Decide which markers to show ──
  const showDistrictMarkers = zoom >= 13 && districts.length > 0 && selectedGu;

  // Color scores for district markers
  const districtColorScores = useMemo(() => {
    if (districts.length === 0) return {};
    if (dataLayer === "score") {
      return Object.fromEntries(
        districts.map((d) => [d.district_code, districtScore(d, "score")])
      );
    }
    const values = districts.map((d) => districtScore(d, dataLayer));
    return Object.fromEntries(
      districts.map((d, i) => [
        d.district_code,
        metricToColorScore(values[i], dataLayer, values),
      ])
    );
  }, [districts, dataLayer]);

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      {/* ── Top Header ── */}
      <header className="bg-white/90 backdrop-blur-md border-b border-slate-200/60 z-40 flex-shrink-0">
        <div className="px-3 py-2 flex items-center gap-2">
          <Link
            href="/"
            className="flex items-center gap-1.5 flex-shrink-0"
          >
            <ArrowLeft size={18} className="text-slate-500" />
            <span className="text-base font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              SpotPick
            </span>
          </Link>

          {/* Industry chips — horizontal scroll */}
          <div className="flex-1 overflow-x-auto scrollbar-hide">
            <div className="flex items-center gap-1.5 px-1">
              {INDUSTRIES.map((ind) => (
                <button
                  key={ind.code}
                  onClick={() => handleIndustryChange(ind.code)}
                  className={cn(
                    "flex items-center gap-1 px-2.5 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all border flex-shrink-0",
                    industryCode === ind.code
                      ? "bg-blue-600 text-white border-blue-600 shadow-sm"
                      : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
                  )}
                >
                  <span className="text-sm">{ind.icon}</span>
                  {ind.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* ── Main content area ── */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Panel — desktop only */}
        <div className="hidden md:flex w-[350px] flex-shrink-0 bg-white border-r border-slate-200/60 flex-col">
          {loadingGu ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-slate-400">
                <BarChart3
                  size={24}
                  className="mx-auto mb-2 animate-pulse"
                />
                <p className="text-sm">데이터 로딩중...</p>
              </div>
            </div>
          ) : (
            <LeftPanel
              selectedGu={selectedGu}
              selectedDistrict={selectedDistrict}
              guData={guData}
              districts={districts}
              industryRankings={industryRankings}
              industryCode={industryCode}

              loadingDistricts={loadingDistricts}
              loadingRankings={loadingRankings}
              onBack={handleBack}
            />
          )}
        </div>

        {/* Map area */}
        <div className="flex-1 relative">
          {/* Data layer toggle */}
          <div className="absolute top-3 left-3 z-10">
            <button
              onClick={() => setShowLayerPicker(!showLayerPicker)}
              className="flex items-center gap-1.5 px-3 py-2 bg-white/95 backdrop-blur-sm rounded-lg shadow-md border border-slate-200 text-xs font-medium text-slate-700 hover:bg-white transition-colors"
            >
              <Layers size={14} className="text-blue-500" />
              {DATA_LAYERS.find((l) => l.key === dataLayer)?.label}
              <ChevronDown size={12} />
            </button>
            {showLayerPicker && (
              <div className="absolute top-full left-0 mt-1 bg-white rounded-lg shadow-xl border border-slate-200 py-1 min-w-[120px]">
                {DATA_LAYERS.map((l) => (
                  <button
                    key={l.key}
                    onClick={() => {
                      setDataLayer(l.key);
                      setShowLayerPicker(false);
                    }}
                    className={cn(
                      "w-full text-left px-3 py-2 text-xs transition-colors",
                      dataLayer === l.key
                        ? "bg-blue-50 text-blue-700 font-semibold"
                        : "text-slate-600 hover:bg-slate-50"
                    )}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Legend */}
          <ScoreLegend layer={dataLayer} />

          {/* Map */}
          <Map
            ref={mapRef}
            initialViewState={{
              longitude: 126.978,
              latitude: 37.566,
              zoom: 11,
            }}
            style={{ width: "100%", height: "100%" }}
            mapStyle={MAP_STYLE}
            onMove={(e) => {
              setZoom(e.viewState.zoom);
              setViewCenter([e.viewState.longitude, e.viewState.latitude]);
            }}
            attributionControl={false}
          >
            <NavigationControl position="top-right" showCompass={false} />

            {/* Gu-level markers (zoom < 13 or no gu selected) */}
            {(!showDistrictMarkers) &&
              guData.map((gu) => (
                <Marker
                  key={gu.gu_name}
                  longitude={gu.center_lng}
                  latitude={gu.center_lat}
                  anchor="center"
                >
                  <GuMarker
                    gu={gu}
                    colorScore={guColorScores[gu.gu_name] ?? gu.avg_score}
                    size={markerSizes[gu.gu_name] ?? 40}
                    isSelected={selectedGu?.gu_name === gu.gu_name}
                    onClick={() => handleGuClick(gu)}
                  />
                </Marker>
              ))}

            {/* District-level markers (zoom >= 13 with selected gu) */}
            {showDistrictMarkers &&
              districts.map((d) => (
                <Marker
                  key={d.district_code}
                  longitude={d.lng}
                  latitude={d.lat}
                  anchor="center"
                >
                  <DistrictMarker
                    district={d}
                    colorScore={
                      districtColorScores[d.district_code] ??
                      districtScore(d, "score")
                    }
                    isSelected={
                      selectedDistrict?.district_code === d.district_code
                    }
                    onClick={() => handleDistrictClick(d)}
                  />
                </Marker>
              ))}
          </Map>

          {/* Loading overlay */}
          {loadingGu && (
            <div className="absolute inset-0 bg-white/50 flex items-center justify-center z-20">
              <div className="bg-white rounded-xl shadow-lg px-6 py-4 flex items-center gap-3">
                <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-slate-600">
                  데이터 로딩중...
                </span>
              </div>
            </div>
          )}

          {/* Loading districts overlay */}
          {loadingDistricts && (
            <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-20">
              <div className="bg-white/95 backdrop-blur-sm rounded-full shadow-lg px-4 py-2 flex items-center gap-2 border border-slate-200">
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-xs text-slate-600 font-medium">상권 데이터 로딩중...</span>
              </div>
            </div>
          )}

          {/* Guide hint */}
          {showGuide && !loadingGu && guData.length > 0 && (
            <div className="absolute top-16 left-1/2 -translate-x-1/2 z-30 animate-in fade-in slide-in-from-top-2 duration-300">
              <div
                onClick={() => setShowGuide(false)}
                className="bg-blue-600/95 backdrop-blur-sm text-white rounded-2xl px-5 py-3 shadow-xl cursor-pointer max-w-xs text-center"
              >
                <p className="text-sm font-semibold mb-0.5">자치구를 클릭하거나 확대해보세요</p>
                <p className="text-xs text-blue-200">마우스를 올리면 상세 정보를 볼 수 있어요</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Mobile bottom sheet ── */}
      <div className="md:hidden">
        <BottomSheet height={sheetHeight} onChangeHeight={setSheetHeight}>
          {loadingGu ? (
            <div className="flex items-center justify-center py-8 text-slate-400">
              <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-2" />
              <span className="text-sm">로딩중...</span>
            </div>
          ) : (
            <LeftPanel
              selectedGu={selectedGu}
              selectedDistrict={selectedDistrict}
              guData={guData}
              districts={districts}
              industryRankings={industryRankings}
              industryCode={industryCode}

              loadingDistricts={loadingDistricts}
              loadingRankings={loadingRankings}
              onBack={handleBack}
            />
          )}
        </BottomSheet>
      </div>

      {/* ── Bottom Navigation ── */}
      <nav className="flex-shrink-0 bg-white border-t border-slate-200 z-40">
        <div className="flex items-center justify-around py-2">
          <Link
            href="/results"
            className="flex flex-col items-center gap-0.5 px-4 py-1 text-slate-400"
          >
            <Search size={18} />
            <span className="text-[10px] font-medium">조건검색</span>
          </Link>
          <div className="flex flex-col items-center gap-0.5 px-4 py-1 text-blue-600">
            <MapPin size={18} />
            <span className="text-[10px] font-bold">지도탐색</span>
          </div>
          <Link
            href="/"
            className="flex flex-col items-center gap-0.5 px-4 py-1 text-slate-400"
          >
            <MessageCircle size={18} />
            <span className="text-[10px] font-medium">AI 상담</span>
          </Link>
        </div>
      </nav>

      {/* Hide scrollbar for industry chips */}
      <style jsx global>{`
        .scrollbar-hide {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page export with Suspense
// ---------------------------------------------------------------------------

export default function ExplorePage() {
  return (
    <Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-slate-50">
          <div className="text-center text-slate-400">
            <MapPin size={40} className="mx-auto mb-3 animate-pulse" />
            <p className="text-sm">지도 로딩중...</p>
          </div>
        </div>
      }
    >
      <ExploreContent />
    </Suspense>
  );
}
