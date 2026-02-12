"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { track } from "@/lib/analytics";
import {
  MapPin,
  ArrowLeft,
  Loader2,
  AlertTriangle,
  RefreshCw,
  ClipboardCheck,
  Info,
  Check,
  ArrowRight,
  Calendar,
} from "lucide-react";

// ── Constants ────────────────────────────────────────────────────
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const FETCH_TIMEOUT_MS = 30_000;

function fetchWithTimeout(url: string, options?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  return fetch(url, { ...options, signal: controller.signal }).finally(() =>
    clearTimeout(timeoutId),
  );
}

// ── Format helpers ───────────────────────────────────────────────
function formatWon(value: number): string {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}억원`;
  if (value >= 10_000) return `${Math.round(value / 10_000).toLocaleString()}만원`;
  return `${value.toLocaleString()}원`;
}

// ── Types ────────────────────────────────────────────────────────
interface TimelineMilestone {
  day: number;
  title: string;
  detail: string;
  cost_man: number;
  duration: string;
  category: string;
}

interface Permit {
  name: string;
  agency: string;
  duration: string;
  cost: number;
  order: number;
}

interface TimelineSummary {
  estimated_rent: number;
  budget_man: number;
  district_name: string;
  industry_name: string;
}

interface TimelineResponse {
  timeline: TimelineMilestone[];
  permits: Permit[];
  notes: string[];
  summary: TimelineSummary;
}

// ── Category badge config ────────────────────────────────────────
const CATEGORY_STYLES: Record<string, string> = {
  "인허가": "bg-blue-100 text-blue-700",
  "자금": "bg-emerald-100 text-emerald-700",
  "시설": "bg-orange-100 text-orange-700",
  "운영": "bg-purple-100 text-purple-700",
  "마케팅": "bg-pink-100 text-pink-700",
};

// ── Skeleton ─────────────────────────────────────────────────────
function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse rounded-lg bg-slate-200/60", className)} />
  );
}

function TimelineSkeleton() {
  return (
    <div className="relative space-y-6 pl-8">
      <div className="absolute left-3 top-0 h-full w-0.5 bg-slate-200" />
      {[0, 1, 2, 3, 4].map((i) => (
        <div key={i} className="relative flex items-start gap-4">
          <div className="absolute -left-8 top-1 h-6 w-6 rounded-full bg-slate-200 animate-pulse" />
          <div className="flex-1 rounded-xl border border-slate-100 bg-white p-4 space-y-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Day label formatter ──────────────────────────────────────────
function formatDay(day: number): string {
  if (day < 0) return `D${day}`;
  if (day === 0) return "D-Day";
  return `D+${day}`;
}

// ── Main content ─────────────────────────────────────────────────
function TimelineInner() {
  const searchParams = useSearchParams()!;
  const districtCode = searchParams.get("district_code") ?? "";
  const industryCode = searchParams.get("industry_code") ?? "";
  const budget = searchParams.get("budget") ?? "";

  // ── Missing params guard ──────────────────────────────────────
  if (!districtCode || !industryCode || !budget) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center px-4">
        <Calendar className="h-12 w-12 text-slate-300" />
        <p className="mt-4 text-lg font-bold text-slate-700">분석 정보가 부족합니다</p>
        <p className="mt-1 text-sm text-slate-500">창업 타임라인을 생성하려면 지역·업종·예산 정보가 필요합니다.</p>
        <Link
          href="/analyze"
          className="mt-6 inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/25 transition hover:shadow-xl"
        >
          분석 시작하기
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  return <TimelineContent districtCode={districtCode} industryCode={industryCode} budget={budget} />;
}

function TimelineContent({
  districtCode,
  industryCode,
  budget,
}: {
  districtCode: string;
  industryCode: string;
  budget: string;
}) {
  const [data, setData] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ── Permit localStorage persistence ───────────────────────────
  const storageKey = `sp_permits_${industryCode}`;
  const [checkedPermits, setCheckedPermits] = useState<Set<string>>(() => {
    if (typeof window === "undefined") return new Set<string>();
    try {
      const stored = JSON.parse(localStorage.getItem(storageKey) || "[]");
      return new Set<string>(stored);
    } catch {
      return new Set<string>();
    }
  });

  const togglePermit = useCallback(
    (name: string) => {
      setCheckedPermits((prev) => {
        const next = new Set(prev);
        if (next.has(name)) next.delete(name);
        else next.add(name);
        try {
          localStorage.setItem(storageKey, JSON.stringify(Array.from(next)));
        } catch { /* noop */ }
        return next;
      });
    },
    [storageKey],
  );

  // ── Fetch timeline ────────────────────────────────────────────
  const fetchData = useCallback(() => {
    setLoading(true);
    setError(null);
    const url = `${API_BASE}/timeline/generate?district_code=${encodeURIComponent(districtCode)}&industry_code=${encodeURIComponent(industryCode)}&budget=${encodeURIComponent(budget)}`;
    fetchWithTimeout(url)
      .then((res) => {
        if (!res.ok) throw new Error(`API 오류 (${res.status})`);
        return res.json();
      })
      .then((result: TimelineResponse) => {
        setData(result);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        track("timeline_view" as any, { district_code: districtCode, industry_code: industryCode });
      })
      .catch((err: Error) => {
        const message =
          err.name === "AbortError"
            ? "요청 시간이 초과되었습니다. 다시 시도해주세요."
            : err.message;
        setError(message);
      })
      .finally(() => setLoading(false));
  }, [districtCode, industryCode, budget]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ── Derived ───────────────────────────────────────────────────
  const timeline = data ? [...data.timeline].sort((a, b) => a.day - b.day) : [];
  const permits = data ? [...data.permits].sort((a, b) => a.order - b.order) : [];
  const notes = data?.notes || [];
  const summary = data?.summary;
  const totalCost = timeline.reduce((sum, m) => sum + (m.cost_man || 0), 0);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* ── Header ─────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600">
              <MapPin className="h-3.5 w-3.5 text-white" />
            </div>
            <span className="text-base font-bold text-slate-900">SpotPick</span>
          </Link>
          <Link
            href={`/analyze/report?district_code=${encodeURIComponent(districtCode)}&industry_code=${encodeURIComponent(industryCode)}&budget=${encodeURIComponent(budget)}`}
            className="flex items-center gap-1 text-sm font-medium text-slate-500 transition hover:text-slate-800"
          >
            <ArrowLeft className="h-4 w-4" />
            리포트로
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
        {/* ── Summary chips ──────────────────────────────────── */}
        {summary && !loading && (
          <div className="mb-8">
            <h1 className="text-xl font-extrabold text-slate-900 sm:text-2xl">창업 타임라인</h1>
            <p className="mt-1 text-sm text-slate-500">D-90부터 D+90까지 주요 마일스톤</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
                {summary.district_name}
              </span>
              <span className="inline-flex items-center rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
                {summary.industry_name}
              </span>
              <span className="inline-flex items-center rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                예산 {summary.budget_man.toLocaleString()}만원
              </span>
            </div>
          </div>
        )}

        {/* ── Loading state ──────────────────────────────────── */}
        {loading && (
          <div className="py-8">
            <div className="mb-6 flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
              <p className="text-sm font-semibold text-slate-600">타임라인을 생성하고 있습니다...</p>
            </div>
            <TimelineSkeleton />
          </div>
        )}

        {/* ── Error state ────────────────────────────────────── */}
        {error && !loading && (
          <div className="flex flex-col items-center py-16">
            <AlertTriangle className="h-10 w-10 text-amber-400" />
            <p className="mt-3 text-sm font-medium text-slate-700">{error}</p>
            <button
              type="button"
              onClick={fetchData}
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              다시 시도
            </button>
          </div>
        )}

        {/* ── Timeline ───────────────────────────────────────── */}
        {data && !loading && (
          <div className="space-y-10">
            {/* Vertical timeline */}
            <section>
              <div className="relative pl-8">
                {/* Vertical line */}
                <div className="absolute left-3 top-0 h-full border-l-2 border-slate-200" />

                <div className="space-y-5">
                  {timeline.map((milestone, idx) => {
                    const isDDay = milestone.day === 0;
                    const dayLabel = formatDay(milestone.day);
                    const categoryStyle = CATEGORY_STYLES[milestone.category] || "bg-slate-100 text-slate-600";

                    return (
                      <div key={`${milestone.day}-${idx}`} className="relative">
                        {/* Circle marker */}
                        <div
                          className={cn(
                            "absolute -left-8 top-1 flex items-center justify-center rounded-full text-[10px] font-bold",
                            isDDay
                              ? "h-7 w-7 bg-blue-600 text-white ring-4 ring-blue-100"
                              : "h-6 w-6 bg-white border-2 border-slate-300 text-slate-500",
                          )}
                        >
                          {isDDay ? "D" : ""}
                        </div>

                        {/* Card */}
                        <div
                          className={cn(
                            "rounded-xl border bg-white p-4 transition-all",
                            isDDay
                              ? "border-blue-200 shadow-md shadow-blue-500/10"
                              : "border-slate-100 hover:border-slate-200 hover:shadow-sm",
                          )}
                        >
                          <div className="flex items-center gap-2">
                            <span
                              className={cn(
                                "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold",
                                isDDay ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600",
                              )}
                            >
                              {dayLabel}
                            </span>
                            <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-semibold", categoryStyle)}>
                              {milestone.category}
                            </span>
                            {milestone.cost_man > 0 && (
                              <span className="ml-auto text-xs font-bold text-emerald-600">
                                {milestone.cost_man.toLocaleString()}만원
                              </span>
                            )}
                          </div>
                          <h3
                            className={cn(
                              "mt-2 font-bold",
                              isDDay ? "text-base text-blue-900" : "text-sm text-slate-900",
                            )}
                          >
                            {milestone.title}
                          </h3>
                          <p className="mt-1 text-xs leading-relaxed text-slate-500">{milestone.detail}</p>
                          {milestone.duration && (
                            <p className="mt-1.5 text-[10px] font-medium text-slate-400">
                              소요: {milestone.duration}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Total cost */}
              {totalCost > 0 && (
                <div className="mt-6 rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50 p-4 text-center">
                  <p className="text-xs font-semibold text-emerald-600">총 예상 비용</p>
                  <p className="mt-1 text-xl font-extrabold text-emerald-800">
                    {formatWon(totalCost * 10_000)}
                  </p>
                </div>
              )}
            </section>

            {/* ── Permit checklist ─────────────────────────────── */}
            {permits.length > 0 && (
              <section>
                <div className="mb-4 flex items-center gap-2">
                  <ClipboardCheck className="h-5 w-5 text-orange-500" />
                  <h2 className="text-lg font-extrabold text-slate-900">필수 인허가 체크리스트</h2>
                </div>

                <div className="space-y-2">
                  {permits.map((permit) => {
                    const isChecked = checkedPermits.has(permit.name);
                    return (
                      <div
                        key={`${permit.order}-${permit.name}`}
                        className={cn(
                          "rounded-xl border p-4 transition-all",
                          isChecked
                            ? "border-emerald-200 bg-emerald-50/30"
                            : "border-slate-100 bg-white hover:border-slate-200",
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <button
                            type="button"
                            onClick={() => togglePermit(permit.name)}
                            className={cn(
                              "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-all",
                              isChecked
                                ? "border-emerald-500 bg-emerald-500 text-white"
                                : "border-slate-300 bg-white hover:border-blue-400",
                            )}
                            aria-label={`${permit.name} ${isChecked ? "완료 취소" : "완료 처리"}`}
                          >
                            {isChecked && <Check className="h-3 w-3" strokeWidth={3} />}
                          </button>
                          <div className="flex-1 min-w-0">
                            <p
                              className={cn(
                                "text-sm font-bold transition-all",
                                isChecked ? "text-emerald-700 line-through decoration-emerald-400" : "text-slate-900",
                              )}
                            >
                              {permit.name}
                            </p>
                            <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
                              <span>발급처: {permit.agency}</span>
                              <span>소요: {permit.duration}</span>
                              {permit.cost > 0 && <span>비용: {formatWon(permit.cost)}</span>}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* ── Notes section ────────────────────────────────── */}
            {notes.length > 0 && (
              <section>
                <div className="rounded-xl border border-blue-200 bg-blue-50/60 p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <Info className="h-4 w-4 text-blue-500" />
                    <h3 className="text-sm font-bold text-blue-900">참고 사항</h3>
                  </div>
                  <ul className="space-y-1">
                    {notes.map((note, i) => (
                      <li key={i} className="text-xs leading-relaxed text-blue-800">
                        · {note}
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
            )}

            {/* ── CTA ──────────────────────────────────────────── */}
            <section className="pb-4">
              <Link
                href={`/analyze/action?industry_code=${encodeURIComponent(industryCode)}&budget=${encodeURIComponent(budget)}&district_code=${encodeURIComponent(districtCode)}`}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-xl",
                  "bg-gradient-to-r from-blue-600 to-indigo-600",
                  "px-6 py-3.5 text-sm font-semibold text-white",
                  "shadow-lg shadow-blue-500/25 transition",
                  "hover:shadow-xl hover:shadow-blue-500/30",
                )}
              >
                사업계획서에 반영
                <ArrowRight className="h-4 w-4" />
              </Link>
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

// ── Page export with Suspense wrapper ────────────────────────────
export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <TimelineInner />
    </Suspense>
  );
}
