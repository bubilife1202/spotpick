"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Loader2, Wallet } from "lucide-react";
import { formatMoney } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

type StartupCostItem = {
  name: string;
  min: number;
  max: number;
};

type StartupSubtypeCostResponse = {
  industry_code: string;
  sub_type: string;
  min_budget_man: number;
  items: StartupCostItem[];
  tip: string;
  is_fallback: boolean;
};

const formatMan = (valueMan: number): string => formatMoney(valueMan * 10_000);

export function StartupCostCard({
  industryCode,
  subType,
  userBudget,
}: {
  industryCode: string;
  subType: string;
  userBudget: number;
}) {
  const [data, setData] = useState<StartupSubtypeCostResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestUrl = useMemo(() => {
    const params = new URLSearchParams({
      industry_code: industryCode,
      sub_type: subType,
    });
    return `${API_BASE}/support/startup-cost/subtype?${params.toString()}`;
  }, [industryCode, subType]);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!industryCode || !subType) return;
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(requestUrl);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as StartupSubtypeCostResponse;
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Unknown error");
          setData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [industryCode, subType, requestUrl]);

  const totals = useMemo(() => {
    const items = data?.items || [];
    return items.reduce(
      (acc, item) => {
        acc.min += item.min;
        acc.max += item.max;
        return acc;
      },
      { min: 0, max: 0 },
    );
  }, [data]);

  const minBudget = data?.min_budget_man || 0;
  const deficit = Math.max(0, minBudget - Math.max(0, userBudget));
  const progress = minBudget > 0 ? Math.min(100, (Math.max(0, userBudget) / minBudget) * 100) : 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-extrabold text-slate-900">
            {subType} 예상 창업비용
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            필요 예산 {formatMan(minBudget)} vs 내 예산 {formatMan(userBudget)}
            {deficit > 0 ? ` -> ${formatMan(deficit)} 부족` : " -> 예산 충족"}
          </p>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
          <Wallet className="h-3.5 w-3.5" /> 세부업종 기준
        </span>
      </div>

      {loading && (
        <div className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" /> 창업비용 계산 중
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          창업비용 데이터를 불러오지 못했습니다: {error}
        </div>
      )}

      {!loading && !error && data && (
        <>
          <div className="mt-4 overflow-hidden rounded-xl border border-slate-200">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-4 py-2 text-left font-semibold">항목</th>
                  <th className="px-4 py-2 text-right font-semibold">최소</th>
                  <th className="px-4 py-2 text-right font-semibold">최대</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.name} className="border-t border-slate-100">
                    <td className="px-4 py-2 text-slate-800">{item.name}</td>
                    <td className="px-4 py-2 text-right font-medium text-slate-700">{formatMan(item.min)}</td>
                    <td className="px-4 py-2 text-right font-medium text-slate-700">{formatMan(item.max)}</td>
                  </tr>
                ))}
                <tr className="border-t border-slate-200 bg-slate-50/70">
                  <td className="px-4 py-2 font-bold text-slate-900">합계</td>
                  <td className="px-4 py-2 text-right font-extrabold text-slate-900">{formatMan(totals.min)}</td>
                  <td className="px-4 py-2 text-right font-extrabold text-slate-900">{formatMan(totals.max)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/60 p-4">
            <p className="text-xs font-semibold text-slate-600">
              내 예산 {formatMan(userBudget)} / 최소 필요 {formatMan(minBudget)}
            </p>
            <div className="mt-2 h-3 w-full overflow-hidden rounded-full bg-slate-200">
              <div
                className={deficit > 0 ? "h-full rounded-full bg-gradient-to-r from-rose-400 to-rose-500" : "h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-500"}
                style={{ width: `${progress}%` }}
              />
            </div>
            {deficit > 0 && (
              <div className="mt-3 flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">
                <AlertTriangle className="h-4 w-4" /> {formatMan(deficit)} 추가 필요
              </div>
            )}
          </div>

          {data.tip && (
            <p className="mt-3 text-xs leading-relaxed text-slate-600">팁: {data.tip}</p>
          )}
        </>
      )}
    </div>
  );
}
