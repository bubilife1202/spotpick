"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import type { BenchmarkStore } from "@/lib/analyze-store";
import { useAnalyzeStore } from "@/lib/analyze-store";
import {
  Star,
  MessageSquare,
  BookOpen,
  MapPin,
  ExternalLink,
  Store,
  Building2,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface NaverProfile {
  naver_id: string;
  name: string;
  category: string;
  review_count: number;
  review_score: number;
  blog_review_count: number;
  visitor_review_count: number;
  keywords: string[];
  business_hours: Record<string, string>;
}

interface Competitor {
  name: string;
  category: string;
  distance: number;
  address: string;
}

interface AnalyzeData {
  store_name: string;
  store_category: string;
  naver_profile: NaverProfile;
  nearby_competitors: Competitor[];
  competitor_count: number;
  location_summary: string;
  demand: {
    search_trend_keyword: string;
    search_trend_data: Array<{ period: string; ratio: number }>;
    trend_direction: string;
    trend_avg_ratio: number;
    same_category_count_nearby: number;
    demand_verdict: string;
    demand_summary: string;
  };
}

function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse rounded-lg bg-amber-100/60", className)} />
  );
}

export function BenchmarkAnalysisCard({
  benchmark,
}: {
  benchmark: BenchmarkStore;
}) {
  const store = useAnalyzeStore();
  const targetArea = store.preferredDistricts?.[0] || "";
  const [data, setData] = useState<AnalyzeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!benchmark.name || !benchmark.x || !benchmark.y) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(false);

    fetch(`${API_BASE}/benchmark/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: benchmark.name,
        x: benchmark.x,
        y: benchmark.y,
        category: benchmark.category,
        industry_code: benchmark.industryCode,
        target_district_name: targetArea,
      }),
    })
      .then((r) => {
        if (!r.ok) throw new Error("API error");
        return r.json();
      })
      .then((d: AnalyzeData) => setData(d))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [benchmark.name, benchmark.x, benchmark.y, benchmark.category, benchmark.industryCode, targetArea]);

  if (!benchmark.x || !benchmark.y) return null;

  if (loading) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50/80 to-orange-50/50 p-5">
        <div className="mb-4 flex items-center gap-2">
          <Store className="h-4 w-4 text-amber-600" />
          <h3 className="text-sm font-bold text-amber-900">
            벤치마크 매장 분석
          </h3>
        </div>
        <div className="space-y-3">
          <Skeleton className="h-4 w-3/4" />
          <div className="grid grid-cols-3 gap-2">
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
            <Skeleton className="h-16" />
          </div>
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
    );
  }

  if (error || !data) return null;

  const np = data.naver_profile;
  const demand = data.demand;
  const hasNaverData = np.review_count > 0 || np.review_score > 0;
  const subCategory = benchmark.subCategory || (
    benchmark.category.includes(" > ")
      ? benchmark.category.split(" > ").pop()?.trim() || ""
      : benchmark.category
  );
  const verdictTone =
    demand.demand_verdict === "충분"
      ? "bg-emerald-100 text-emerald-700 border-emerald-200"
      : demand.demand_verdict === "부족"
        ? "bg-rose-100 text-rose-700 border-rose-200"
        : "bg-amber-100 text-amber-700 border-amber-200";
  const trendText =
    demand.trend_direction === "rising"
      ? "↗ 상승"
      : demand.trend_direction === "declining"
        ? "↘ 하락"
        : "→ 유지";

  return (
    <div className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50/80 to-orange-50/50 p-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Store className="h-4 w-4 text-amber-600" />
          <h3 className="text-sm font-bold text-amber-900">
            벤치마크 매장 분석
          </h3>
        </div>
        {benchmark.placeUrl && (
          <a
            href={benchmark.placeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-semibold text-amber-700 transition hover:bg-amber-200"
          >
            카카오맵 <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>

      <div className="mb-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10">
          <Store className="h-5 w-5 text-amber-600" />
        </div>
        <div>
          <p className="text-sm font-bold text-slate-900">{data.store_name}</p>
          <p className="text-[11px] text-slate-500">{data.store_category}</p>
        </div>
      </div>

      {subCategory && subCategory !== "카페" && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-violet-500">세부 업종</span>
          <span className="text-xs font-bold text-violet-800">{subCategory}</span>
          <span className="text-[10px] text-violet-400">≠ 일반 카페</span>
        </div>
      )}

      {hasNaverData && (
        <div className="mb-4 grid grid-cols-3 gap-2">
          <div className="rounded-xl border border-amber-100 bg-white/80 p-3 text-center">
            <Star className="mx-auto mb-1 h-4 w-4 text-amber-500" />
            <p className="text-lg font-extrabold text-amber-700">
              {np.review_score > 0 ? np.review_score.toFixed(1) : "-"}
            </p>
            <p className="text-[9px] font-medium text-slate-400">네이버 평점</p>
          </div>
          <div className="rounded-xl border border-amber-100 bg-white/80 p-3 text-center">
            <MessageSquare className="mx-auto mb-1 h-4 w-4 text-blue-500" />
            <p className="text-lg font-extrabold text-blue-700">
              {np.visitor_review_count > 0
                ? np.visitor_review_count.toLocaleString()
                : np.review_count > 0
                  ? np.review_count.toLocaleString()
                  : "-"}
            </p>
            <p className="text-[9px] font-medium text-slate-400">방문자 리뷰</p>
          </div>
          <div className="rounded-xl border border-amber-100 bg-white/80 p-3 text-center">
            <BookOpen className="mx-auto mb-1 h-4 w-4 text-emerald-500" />
            <p className="text-lg font-extrabold text-emerald-700">
              {np.blog_review_count > 0
                ? np.blog_review_count.toLocaleString()
                : "-"}
            </p>
            <p className="text-[9px] font-medium text-slate-400">블로그 리뷰</p>
          </div>
        </div>
      )}

      {np.keywords.length > 0 && (
        <div className="mb-4">
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-wider text-amber-500">
            키워드
          </p>
          <div className="flex flex-wrap gap-1.5">
            {np.keywords.slice(0, 6).map((kw) => (
              <span
                key={kw}
                className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700"
              >
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-amber-100 bg-white/60 p-3">
        <div className="mb-2 flex items-center gap-1.5">
          <MapPin className="h-3.5 w-3.5 text-amber-500" />
          <p className="text-[10px] font-bold uppercase tracking-wider text-amber-500">
            주변 경쟁 환경
          </p>
        </div>
        <p className="text-xs font-semibold text-slate-700">
          {data.location_summary}
        </p>
         {data.nearby_competitors.length > 0 && (
           <div className="mt-2 space-y-1">
             {data.nearby_competitors.slice(0, 5).map((comp, i) => (
               <div
                 key={`${comp.name}-${i}`}
                 className="flex items-center justify-between text-[11px]"
               >
                 <span className="font-medium text-slate-600">{comp.name}</span>
                 <span className="text-slate-400">{comp.distance}m</span>
               </div>
             ))}
           </div>
         )}

         {benchmark.address && (
           <a
             href={`https://land.naver.com/offices/complexSearch.naver?keyword=${encodeURIComponent(benchmark.address.split(" ").slice(0, 3).join(" "))}`}
             target="_blank"
             rel="noopener noreferrer"
             className="mt-3 flex items-center justify-center gap-1.5 rounded-xl border border-amber-200 bg-white/80 px-3 py-2 text-[11px] font-semibold text-amber-700 transition hover:bg-amber-50"
           >
             <Building2 className="h-3.5 w-3.5" />
             벤치마크 주변 매물 검색
             <ExternalLink className="h-3 w-3" />
           </a>
         )}
       </div>

      <div className="mt-3 rounded-xl border border-amber-100 bg-white/60 p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="text-[10px] font-bold uppercase tracking-wider text-amber-500">
            수요 검증
          </p>
          {demand.demand_verdict && (
            <span
              className={cn(
                "rounded-full border px-2 py-0.5 text-[10px] font-semibold",
                verdictTone,
              )}
            >
              {demand.demand_verdict}
            </span>
          )}
        </div>

        <p className="text-xs font-semibold text-slate-700">
          {demand.demand_summary || "수요 검증 데이터를 확인할 수 없습니다."}
        </p>

        {demand.search_trend_data.length > 0 && (
          <p className="mt-1 text-[11px] font-medium text-amber-700">
            검색 트렌드: {trendText}
            {demand.search_trend_keyword ? ` (${demand.search_trend_keyword})` : ""}
          </p>
        )}

        {(targetArea || demand.search_trend_keyword) && (
          <p className="mt-1 text-[11px] text-slate-500">
            {targetArea || "대상 지역"} 지역 {demand.search_trend_keyword || "동종 업종"}{" "}
            {demand.same_category_count_nearby}곳
          </p>
        )}
      </div>
    </div>
  );
}
