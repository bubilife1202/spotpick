"use client";

import { TrendingUp, CreditCard } from "lucide-react";
import { cn } from "@/lib/utils";

interface QuarterData {
  period: string;
  monthly_sales: number;
  transactions: number;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function SalesTrendChart({ data, loading }: { data: any; loading: boolean }) {
  if (loading) {
    return (
      <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="h-5 w-5 animate-pulse rounded bg-slate-200" />
          <h3 className="text-sm font-bold text-slate-400">매출 트렌드</h3>
        </div>
        <div className="h-40 w-full animate-pulse rounded bg-slate-200" />
      </div>
    );
  }

  if (!data || !data.quarters || data.quarters.length === 0) return null;

  const quarters: QuarterData[] = data.quarters;
  const yoyChange: number = data.yoy_change || 0;
  const maxSales = Math.max(...quarters.map((q) => q.monthly_sales));
  const minSales = Math.min(...quarters.map((q) => q.monthly_sales));
  const range = maxSales - minSales || 1;

  // Format won value
  const formatWon = (v: number) => {
    if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(1)}억`;
    if (v >= 10_000) return `${Math.round(v / 10_000).toLocaleString()}만`;
    return `${v.toLocaleString()}`;
  };

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-blue-500" />
        <h3 className="text-sm font-bold text-slate-900">매출 트렌드</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[9px] font-semibold text-blue-600">
          <CreditCard className="h-2.5 w-2.5" />
          카드매출 {quarters.length}분기
        </span>
      </div>

      {/* YoY badge */}
      <div className="mb-3 flex items-center gap-2">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-bold",
            yoyChange > 0
              ? "bg-emerald-50 text-emerald-700"
              : yoyChange < 0
                ? "bg-rose-50 text-rose-700"
                : "bg-slate-50 text-slate-700",
          )}
        >
          전년 대비 {yoyChange > 0 ? "+" : ""}{yoyChange}%
        </span>
        <span className="text-[10px] text-slate-400">
          최근 매출 {formatWon(quarters[quarters.length - 1].monthly_sales)}원
        </span>
      </div>

      {/* Simple bar chart */}
      <div className="flex items-end gap-[2px]" style={{ height: "100px" }}>
        {quarters.map((q, i) => {
          const pct = range > 0 ? ((q.monthly_sales - minSales) / range) * 80 + 20 : 50;
          const isLast = i === quarters.length - 1;
          return (
            <div key={q.period} className="group relative flex-1 text-center">
              <div
                className={cn(
                  "mx-auto w-full rounded-t transition-all duration-300",
                  isLast
                    ? "bg-gradient-to-t from-blue-600 to-blue-400"
                    : "bg-gradient-to-t from-blue-200 to-blue-100 group-hover:from-blue-400 group-hover:to-blue-300",
                )}
                style={{ height: `${pct}%` }}
              />
              {/* Tooltip on hover */}
              <div className="pointer-events-none absolute -top-12 left-1/2 z-10 hidden -translate-x-1/2 rounded bg-slate-800 px-2 py-1 text-[9px] text-white shadow group-hover:block">
                {formatWon(q.monthly_sales)}원
                <br />
                {q.transactions.toLocaleString()}건
              </div>
            </div>
          );
        })}
      </div>

      {/* X-axis labels */}
      <div className="mt-1 flex justify-between text-[8px] text-slate-400">
        <span>{quarters[0].period}</span>
        {quarters.length > 4 && <span>{quarters[Math.floor(quarters.length / 2)].period}</span>}
        <span>{quarters[quarters.length - 1].period}</span>
      </div>
    </div>
  );
}
