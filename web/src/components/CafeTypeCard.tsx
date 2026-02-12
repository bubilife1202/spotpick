"use client";

import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { Coffee, Loader2, AlertTriangle } from "lucide-react";

type CafeTypeCode =
  | "EXPRESS"
  | "SPECIALTY"
  | "DESSERT"
  | "NEIGHBORHOOD"
  | "STUDY"
  | "STANDARD";

type WarningSeverity = "low" | "medium" | "high";

type CafeTypeWarning = {
  code: string;
  message: string;
  severity: WarningSeverity;
};

type CafeTypeRanking = {
  rank: number;
  type: CafeTypeCode;
  name_kr: string;
  score: number;
  difficulty: number;
  budget_min_man: number;
  budget_ideal_man: number;
  eliminated: boolean;
  elimination_reason: string;
  reasons: string[];
};

type CafeTypeResult = {
  district_code: string;
  district_name: string;
  industry_code: string;
  confidence: number;
  confidence_label: string;
  rankings: CafeTypeRanking[];
  warnings: CafeTypeWarning[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

function scoreBarColor(score: number) {
  if (score >= 80) return "from-emerald-500 to-emerald-600";
  if (score >= 60) return "from-blue-500 to-indigo-600";
  if (score >= 40) return "from-amber-500 to-orange-600";
  return "from-slate-300 to-slate-400";
}

function severityStyle(severity: WarningSeverity) {
  if (severity === "high") return "border-rose-200 bg-rose-50 text-rose-800";
  if (severity === "medium") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

export function CafeTypeCard({
  industryCode,
  districtCode,
  budgetMan,
  experienceLevel,
  selectedSubType,
}: {
  industryCode: string;
  districtCode: string;
  budgetMan: number;
  experienceLevel?: string;
  selectedSubType?: string;
}) {
  const [data, setData] = useState<CafeTypeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestUrl = useMemo(() => {
    const params = new URLSearchParams();
    if (budgetMan > 0) params.set("budget_max", String(budgetMan));
    if (experienceLevel) params.set("experience_level", experienceLevel);
    if (selectedSubType) params.set("sub_type", selectedSubType);
    return `${API_BASE}/cafe-type/${industryCode}/${districtCode}?${params.toString()}`;
  }, [industryCode, districtCode, budgetMan, experienceLevel, selectedSubType]);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!industryCode || !districtCode) return;
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(requestUrl);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const json = (await res.json()) as CafeTypeResult;
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
  }, [industryCode, districtCode, requestUrl]);

  const top = data?.rankings?.[0];
  const topReasons = top?.reasons || [];
  const topWarnings = data?.warnings || [];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-900 text-white">
              <Coffee className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-slate-900">이 상권에 맞는 카페 타입</h2>
              <p className="mt-0.5 text-xs text-slate-500">
                상권 데이터(시간대·요일·연령·직장/거주·경쟁)를 기반으로 추론합니다
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {selectedSubType ? (
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
              선택: {selectedSubType}
            </span>
          ) : null}
          {loading ? (
            <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> 분석 중
            </span>
          ) : data ? (
            <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
              신뢰도 {data.confidence_label} · {data.confidence.toFixed(1)}
            </span>
          ) : null}
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          카페 타입 분석을 불러오지 못했습니다: {error}
        </div>
      )}

      {!error && !loading && data && top && (
        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          {/* Left: winner */}
          <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-500">추천 1위</p>
                <h3 className="mt-1 text-lg font-extrabold text-slate-900">{top.name_kr}</h3>
                <p className="mt-1 text-xs text-slate-500">
                  난이도 {top.difficulty}/5 · 최소 예산 {top.budget_min_man.toLocaleString()}만원
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-extrabold text-slate-900">{Math.round(top.score)}</div>
                <div className="text-[11px] font-semibold text-slate-500">/ 100</div>
              </div>
            </div>

            <div className="mt-4">
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200">
                <div
                  className={cn(
                    "h-full rounded-full bg-gradient-to-r",
                    scoreBarColor(top.score)
                  )}
                  style={{ width: `${Math.max(0, Math.min(100, top.score))}%` }}
                />
              </div>
            </div>

            {topReasons.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-bold text-slate-700">왜 이 타입인가요</p>
                <ul className="mt-2 space-y-1.5 text-sm text-slate-700">
                  {topReasons.slice(0, 4).map((r) => (
                    <li key={r} className="flex gap-2">
                      <span className="mt-2 h-1.5 w-1.5 flex-none rounded-full bg-slate-400" />
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Right: rankings */}
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
              타입별 적합도 (Top 6)
            </p>
            <div className="mt-3 space-y-2">
              {data.rankings.slice(0, 6).map((row) => (
                <div
                  key={row.type}
                  className={cn(
                    "rounded-xl border p-3",
                    row.rank === 1
                      ? "border-slate-300 bg-white"
                      : "border-slate-200 bg-slate-50"
                  )}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-extrabold text-slate-400">#{row.rank}</span>
                        <span className="truncate text-sm font-bold text-slate-900">
                          {row.name_kr}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs text-slate-500">
                        난이도 {row.difficulty}/5 · 이상치 {row.budget_ideal_man.toLocaleString()}만원
                      </p>
                    </div>
                    <div className="text-sm font-extrabold text-slate-900">{Math.round(row.score)}</div>
                  </div>
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
                    <div
                      className={cn("h-full bg-gradient-to-r", scoreBarColor(row.score))}
                      style={{ width: `${Math.max(0, Math.min(100, row.score))}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {topWarnings.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-bold text-slate-700">주의</p>
                <div className="mt-2 space-y-2">
                  {topWarnings.slice(0, 3).map((w) => (
                    <div
                      key={`${w.code}:${w.message}`}
                      className={cn(
                        "flex items-start gap-2 rounded-xl border p-3 text-sm",
                        severityStyle(w.severity)
                      )}
                    >
                      <AlertTriangle className="mt-0.5 h-4 w-4 flex-none" />
                      <span className="leading-5">{w.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
