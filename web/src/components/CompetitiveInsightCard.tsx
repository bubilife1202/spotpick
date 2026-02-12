"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import {
  Shield,
  Target,
  Lightbulb,
  Store,
  ExternalLink,
  ChevronDown,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const FETCH_TIMEOUT_MS = 30_000;

// ─── Types ──────────────────────────────────────────────────────────────

interface CafeTypeBreakdown {
  type: string;
  count: number;
  ratio: number;
  examples: string[];
}

interface MarketGap {
  gap_type: string;
  description: string;
  opportunity_score: number;
}

interface DifferentiationStrategy {
  strategy: string;
  reason: string;
  priority: string;
}

interface TopCompetitor {
  name: string;
  category: string;
  address: string;
  place_url: string;
}

interface CompetitiveData {
  total_nearby_cafes: number;
  cafe_types: CafeTypeBreakdown[];
  market_gaps: MarketGap[];
  strategies: DifferentiationStrategy[];
  top_competitors: TopCompetitor[];
}

interface CompetitiveInsightCardProps {
  districtName: string;
  industryCode: string;
  industryName: string;
  benchmarkSubCategory?: string;
}

// ─── Skeleton ───────────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn("animate-pulse rounded-lg bg-teal-100/60", className)}
    />
  );
}

// ─── Helpers ────────────────────────────────────────────────────────────

function opportunityColor(score: number): string {
  if (score >= 7) return "bg-emerald-500";
  if (score >= 4) return "bg-amber-500";
  return "bg-rose-400";
}

function priorityBadge(priority: string): string {
  if (priority === "높음") return "border-rose-200 bg-rose-50 text-rose-700";
  if (priority === "중간") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-slate-200 bg-slate-50 text-slate-600";
}

// ─── Component ──────────────────────────────────────────────────────────

export function CompetitiveInsightCard({
  districtName,
  industryCode,
  industryName,
  benchmarkSubCategory,
}: CompetitiveInsightCardProps) {
  const [data, setData] = useState<CompetitiveData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [competitorsOpen, setCompetitorsOpen] = useState(false);

  useEffect(() => {
    if (!districtName || !industryCode) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(false);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

    fetch(
      `${API_BASE}/competitive/analyze?query=${encodeURIComponent(districtName)}&industry_code=${industryCode}`,
      { signal: controller.signal },
    )
      .then((r) => {
        if (!r.ok) throw new Error("API error");
        return r.json();
      })
      .then((d: CompetitiveData) => setData(d))
      .catch(() => setError(true))
      .finally(() => {
        clearTimeout(timeoutId);
        setLoading(false);
      });

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, [districtName, industryCode]);

  // ── Loading ──
  if (loading) {
    return (
      <div className="rounded-2xl border border-teal-200 bg-gradient-to-br from-teal-50/80 to-cyan-50/50 p-5">
        <div className="mb-4 flex items-center gap-2">
          <Shield className="h-4 w-4 text-teal-600" />
          <h3 className="text-sm font-bold text-teal-900">
            경쟁 차별화 분석
          </h3>
        </div>
        <div className="space-y-3">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-20" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-16" />
        </div>
      </div>
    );
  }

  // ── Error / No data ──
  if (error || !data) return null;

  const maxCount = Math.max(...data.cafe_types.map((t) => t.count), 1);

  // Check if benchmarkSubCategory is a blue ocean
  const subCategoryIsBlueOcean =
    benchmarkSubCategory &&
    benchmarkSubCategory !== industryName &&
    !data.cafe_types.some(
      (t) =>
        t.type === benchmarkSubCategory ||
        t.examples.includes(benchmarkSubCategory),
    );

  return (
    <div className="rounded-2xl border border-teal-200 bg-gradient-to-br from-teal-50/80 to-cyan-50/50 p-5">
      {/* ── Header ── */}
      <div className="mb-4 flex items-center gap-2">
        <Shield className="h-4 w-4 text-teal-600" />
        <h3 className="text-sm font-bold text-teal-900">경쟁 차별화 분석</h3>
      </div>

      {/* ── 1. Market Overview ── */}
      <div className="mb-3 rounded-xl border border-teal-100 bg-white/60 p-3">
        <div className="mb-2 flex items-center gap-1.5">
          <Store className="h-3.5 w-3.5 text-teal-500" />
          <p className="text-[10px] font-bold uppercase tracking-wider text-teal-500">
            시장 현황
          </p>
        </div>
        <p className="mb-3 text-xs font-semibold text-slate-700">
          {districtName}에 {data.total_nearby_cafes}개 {industryName} 매장
        </p>

        <div className="space-y-1.5">
          {data.cafe_types.map((ct) => (
            <div key={ct.type} className="flex items-center gap-2 text-[11px]">
              <span className="w-16 shrink-0 truncate font-medium text-slate-600">
                {ct.type}
              </span>
              <div className="relative h-3 flex-1 overflow-hidden rounded-full bg-teal-100/60">
                <div
                  className="absolute inset-y-0 left-0 rounded-full bg-teal-500"
                  style={{ width: `${(ct.count / maxCount) * 100}%` }}
                />
              </div>
              <span className="w-20 shrink-0 text-right text-slate-500">
                {ct.count}개 ({ct.ratio}%)
              </span>
            </div>
          ))}
        </div>

        {data.cafe_types.some((ct) => ct.examples.length > 0) && (
          <div className="mt-2 flex flex-wrap gap-1">
            {data.cafe_types
              .flatMap((ct) => ct.examples.slice(0, 2))
              .slice(0, 6)
              .map((ex) => (
                <span
                  key={ex}
                  className="rounded-full bg-teal-100 px-2 py-0.5 text-[10px] font-medium text-teal-700"
                >
                  {ex}
                </span>
              ))}
          </div>
        )}
      </div>

      {/* ── 2. Market Gaps ── */}
      {(data.market_gaps.length > 0 || subCategoryIsBlueOcean) && (
        <div className="mb-3 rounded-xl border border-teal-100 bg-white/60 p-3">
          <div className="mb-2 flex items-center gap-1.5">
            <Target className="h-3.5 w-3.5 text-teal-500" />
            <p className="text-[10px] font-bold uppercase tracking-wider text-teal-500">
              시장 기회 (블루오션)
            </p>
          </div>

          {subCategoryIsBlueOcean && (
            <div className="mb-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
              <p className="text-xs font-bold text-emerald-800">
                {benchmarkSubCategory}
              </p>
              <p className="text-[11px] text-emerald-600">
                이 상권에 없는 업종! 블루오션
              </p>
            </div>
          )}

          <div className="space-y-2">
            {data.market_gaps.map((gap, i) => (
              <div
                key={`${gap.gap_type}-${i}`}
                className="rounded-lg border border-teal-100 bg-teal-50/50 p-2.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs font-bold text-slate-800">
                      {gap.gap_type}
                    </p>
                    <p className="mt-0.5 text-[11px] leading-relaxed text-slate-600">
                      {gap.description}
                    </p>
                  </div>
                  <span className="mt-0.5 inline-flex items-center">
                    <span
                      className={cn(
                        "h-2.5 w-2.5 rounded-full",
                        opportunityColor(gap.opportunity_score),
                      )}
                    />
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 3. Differentiation Strategies ── */}
      {data.strategies.length > 0 && (
        <div className="mb-3 rounded-xl border border-teal-100 bg-white/60 p-3">
          <div className="mb-2 flex items-center gap-1.5">
            <Lightbulb className="h-3.5 w-3.5 text-teal-500" />
            <p className="text-[10px] font-bold uppercase tracking-wider text-teal-500">
              차별화 전략
            </p>
          </div>

          <div className="space-y-2">
            {data.strategies.map((s, i) => (
              <div
                key={`${s.strategy}-${i}`}
                className="rounded-lg border border-teal-100 bg-teal-50/50 p-2.5"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs font-bold text-slate-800">
                      {s.strategy}
                    </p>
                    <p className="mt-0.5 text-[11px] leading-relaxed text-slate-600">
                      {s.reason}
                    </p>
                  </div>
                  <span
                    className={cn(
                      "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold",
                      priorityBadge(s.priority),
                    )}
                  >
                    {s.priority}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 4. Top Competitors (collapsible) ── */}
      {data.top_competitors.length > 0 && (
        <div className="rounded-xl border border-teal-100 bg-white/60">
          <button
            type="button"
            onClick={() => setCompetitorsOpen((prev) => !prev)}
            className="flex w-full items-center justify-between p-3 text-left"
          >
            <div className="flex items-center gap-1.5">
              <Store className="h-3.5 w-3.5 text-teal-500" />
              <p className="text-[10px] font-bold uppercase tracking-wider text-teal-500">
                상위 경쟁자 {data.top_competitors.length}개
              </p>
            </div>
            <ChevronDown
              className={cn(
                "h-4 w-4 text-teal-400 transition-transform",
                competitorsOpen && "rotate-180",
              )}
            />
          </button>

          {competitorsOpen && (
            <div className="border-t border-teal-100 px-3 pb-3 pt-2">
              <div className="space-y-2">
                {data.top_competitors.map((comp, i) => {
                  const shortCategory =
                    comp.category.includes(">")
                      ? comp.category.split(">").pop()?.trim() || comp.category
                      : comp.category;

                  return (
                    <div
                      key={`${comp.name}-${i}`}
                      className="flex items-start justify-between gap-2 text-[11px]"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-slate-700">
                          {comp.name}
                        </p>
                        <p className="truncate text-slate-400">
                          {shortCategory} · {comp.address}
                        </p>
                      </div>
                      {comp.place_url && (
                        <a
                          href={comp.place_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-0.5 shrink-0 text-teal-500 hover:text-teal-700"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
