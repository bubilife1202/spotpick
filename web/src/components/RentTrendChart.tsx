"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function RentTrendChart({ data, loading }: { data: any; loading: boolean }) {
  if (loading) {
    return (
      <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="h-5 w-5 animate-pulse rounded bg-slate-200" />
          <h3 className="text-sm font-bold text-slate-400">임대료 트렌드</h3>
        </div>
        <div className="space-y-3">
          <div className="h-4 w-3/4 animate-pulse rounded bg-slate-200" />
          <div className="h-32 w-full animate-pulse rounded bg-slate-200" />
        </div>
      </div>
    );
  }

  if (!data || !data.available) return null;

  const quarterly = data.quarterly_rent || [];
  const yoyChange = data.yoy_change || 0;
  const percentile = data.seoul_avg_percentile || 50;

  // Find max for chart scaling
  const maxRent = Math.max(...quarterly.map((q: { rent_per_sqm: number }) => q.rent_per_sqm), 1);

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-rose-500" />
          <h3 className="text-sm font-bold text-slate-900">B6. 임대료 트렌드</h3>
        </div>
        <div className="flex items-center gap-1.5">
          {yoyChange > 0 ? (
            <TrendingUp className="h-3.5 w-3.5 text-rose-500" />
          ) : yoyChange < 0 ? (
            <TrendingDown className="h-3.5 w-3.5 text-emerald-500" />
          ) : (
            <Minus className="h-3.5 w-3.5 text-slate-400" />
          )}
          <span
            className={cn(
              "text-xs font-bold",
              yoyChange > 0 ? "text-rose-600" : yoyChange < 0 ? "text-emerald-600" : "text-slate-600",
            )}
          >
            전년비 {yoyChange > 0 ? "+" : ""}{yoyChange}%
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="mb-4 grid grid-cols-3 gap-3">
        <div className="rounded-lg bg-slate-50 p-2 text-center">
          <p className="text-[10px] text-slate-400">현재 임대료</p>
          <p className="text-sm font-extrabold text-slate-900">
            {data.current_rent_per_sqm?.toFixed(1)}천원/㎡
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-2 text-center">
          <p className="text-[10px] text-slate-400">전년비</p>
          <p className={cn("text-sm font-extrabold", yoyChange > 0 ? "text-rose-600" : "text-emerald-600")}>
            {yoyChange > 0 ? "+" : ""}{yoyChange}%
          </p>
        </div>
        <div className="rounded-lg bg-slate-50 p-2 text-center">
          <p className="text-[10px] text-slate-400">서울 평균 대비</p>
          <p className="text-sm font-extrabold text-slate-900">{percentile.toFixed(0)}%</p>
        </div>
      </div>

      {/* Mini bar chart */}
      {quarterly.length > 0 && (
        <div>
          <p className="mb-2 text-[10px] font-semibold text-slate-400">분기별 추이</p>
          <div className="flex items-end gap-[2px]" style={{ height: "80px" }}>
            {quarterly.map((q: { period: string; rent_per_sqm: number }, i: number) => {
              const pct = (q.rent_per_sqm / maxRent) * 100;
              const isLatest = i === quarterly.length - 1;
              return (
                <div key={i} className="group relative flex-1">
                  <div
                    className={cn(
                      "w-full rounded-t transition-all duration-300",
                      isLatest ? "bg-rose-400" : "bg-rose-200",
                    )}
                    style={{ height: `${Math.max(4, pct)}%` }}
                  />
                  <div className="pointer-events-none absolute -top-8 left-1/2 z-10 hidden -translate-x-1/2 whitespace-nowrap rounded bg-slate-800 px-1.5 py-0.5 text-[8px] text-white shadow group-hover:block">
                    {q.rent_per_sqm.toFixed(1)}천원/㎡
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-1 flex justify-between text-[7px] text-slate-400">
            <span>{quarterly[0].period.slice(0, 4)}.{quarterly[0].period.slice(4)}</span>
            {quarterly.length > 4 && (
              <span>
                {quarterly[Math.floor(quarterly.length / 2)].period.slice(0, 4)}.{quarterly[Math.floor(quarterly.length / 2)].period.slice(4)}
              </span>
            )}
            <span>{quarterly[quarterly.length - 1].period.slice(0, 4)}.{quarterly[quarterly.length - 1].period.slice(4)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
