"use client";

import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { track } from "@/lib/analytics";
import { ErrorCard } from "@/components/ErrorCard";
import {
  MapPin,
  Sparkles,
  Loader2,
  Search,
  ArrowRight,
  Trophy,
  Users,
  Store,
  TrendingUp,
  Building2,
  Scale,
} from "lucide-react";

// ─── Constants ──────────────────────────────────────────────────────────
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const FETCH_TIMEOUT_MS = 30_000;
const DEBOUNCE_MS = 300;

// ─── Types ──────────────────────────────────────────────────────────────
interface DistrictSearchResult {
  code: string;
  name: string;
  type: string;
  monthly_sales: number;
  store_count: number;
  survival_rate: number;
}

interface DistrictDetail {
  district_code: string;
  district_name: string;
  district_type: string;
  scorecard_total: number;
  monthly_sales_per_store: number;
  survival_rate: number;
  store_count: number;
  foot_traffic: number;
  estimated_rent: number;
  peak_time: string;
  main_age_group: string;
}

interface ComparisonMetric {
  a: number;
  b: number;
  winner: "A" | "B" | "TIE";
}

interface CompareResponse {
  district_a: DistrictDetail;
  district_b: DistrictDetail;
  comparison: {
    scorecard: ComparisonMetric;
    monthly_sales: ComparisonMetric;
    survival_rate: ComparisonMetric;
    store_count: ComparisonMetric;
    foot_traffic: ComparisonMetric;
  };
  ai_verdict: string;
}

// ─── Helpers ────────────────────────────────────────────────────────────
function fetchWithTimeout(url: string, options?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  return fetch(url, { ...options, signal: controller.signal }).finally(() =>
    clearTimeout(timeoutId),
  );
}

function formatWon(v: number): string {
  if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(1)}억원`;
  if (v >= 10_000) return `${Math.round(v / 10_000).toLocaleString()}만원`;
  return `${v.toLocaleString()}원`;
}

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg bg-slate-200/60",
        className,
      )}
    />
  );
}

// ─── District Search Input ──────────────────────────────────────────────
function DistrictSearchInput({
  label,
  side,
  selected,
  onSelect,
  industryCode,
}: {
  label: string;
  side: "A" | "B";
  selected: { code: string; name: string } | null;
  onSelect: (code: string, name: string) => void;
  industryCode: string;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DistrictSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Click-outside closes dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Debounced search
  const handleInputChange = useCallback(
    (value: string) => {
      setQuery(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (value.trim().length < 1) {
        setResults([]);
        setOpen(false);
        return;
      }
      debounceRef.current = setTimeout(() => {
        setSearching(true);
        fetchWithTimeout(
          `${API_BASE}/districts/search?q=${encodeURIComponent(value)}&industry_code=${encodeURIComponent(industryCode)}&limit=10`,
        )
          .then((r) => r.json())
          .then((data) => {
            setResults(data.results || []);
            setOpen(true);
          })
          .catch(() => setResults([]))
          .finally(() => setSearching(false));
      }, DEBOUNCE_MS);
    },
    [industryCode],
  );

  const handleSelect = (r: DistrictSearchResult) => {
    onSelect(r.code, r.name);
    setQuery(r.name);
    setOpen(false);
  };

  const sideColor = side === "A" ? "blue" : "violet";

  return (
    <div ref={containerRef} className="relative flex-1">
      <label className="mb-1.5 flex items-center gap-1.5 text-xs font-bold text-slate-600">
        <span
          className={cn(
            "flex h-5 w-5 items-center justify-center rounded-md text-[10px] font-extrabold text-white",
            sideColor === "blue"
              ? "bg-gradient-to-br from-blue-500 to-blue-600"
              : "bg-gradient-to-br from-violet-500 to-violet-600",
          )}
        >
          {side}
        </span>
        {label}
      </label>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={selected ? selected.name : query}
          onChange={(e) => {
            if (selected) onSelect("", "");
            handleInputChange(e.target.value);
          }}
          onFocus={() => {
            if (results.length > 0) setOpen(true);
          }}
          placeholder="상권 이름 검색..."
          className={cn(
            "w-full rounded-xl border bg-white py-2.5 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 outline-none transition",
            selected
              ? sideColor === "blue"
                ? "border-blue-300 bg-blue-50/40 ring-1 ring-blue-200"
                : "border-violet-300 bg-violet-50/40 ring-1 ring-violet-200"
              : "border-slate-200 focus:border-slate-300 focus:ring-1 focus:ring-slate-200",
          )}
        />
        {searching && (
          <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-slate-400" />
        )}
      </div>

      {/* Dropdown results */}
      {open && results.length > 0 && (
        <div className="absolute left-0 right-0 top-full z-40 mt-1 max-h-64 overflow-y-auto rounded-xl border border-slate-200 bg-white py-1 shadow-xl shadow-slate-200/50">
          {results.map((r) => (
            <button
              key={r.code}
              type="button"
              onClick={() => handleSelect(r)}
              className="flex w-full items-center justify-between px-3 py-2.5 text-left transition hover:bg-slate-50"
            >
              <div>
                <p className="text-sm font-semibold text-slate-900">{r.name}</p>
                <p className="text-[11px] text-slate-500">{r.type}</p>
              </div>
              <div className="text-right">
                <p className="text-[11px] font-bold text-slate-700">
                  {formatWon(r.monthly_sales)}
                </p>
                <p className="text-[10px] text-slate-400">
                  점포 {r.store_count}개 · 생존율 {(r.survival_rate * 100).toFixed(0)}%
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Comparison Table ───────────────────────────────────────────────────
function ComparisonTable({
  data,
  industryCode,
}: {
  data: CompareResponse;
  industryCode: string;
}) {
  const { district_a, district_b, comparison, ai_verdict } = data;

  // Rent comparison: lower = better
  const rentWinner =
    district_a.estimated_rent === district_b.estimated_rent
      ? "TIE"
      : district_a.estimated_rent < district_b.estimated_rent
        ? "A"
        : "B";

  const metrics: {
    label: string;
    valueA: string;
    valueB: string;
    winner: "A" | "B" | "TIE";
    icon: React.ReactNode;
  }[] = [
    {
      label: "종합점수",
      valueA: `${comparison.scorecard.a}점`,
      valueB: `${comparison.scorecard.b}점`,
      winner: comparison.scorecard.winner,
      icon: <Trophy className="h-4 w-4 text-amber-500" />,
    },
    {
      label: "점포당 월매출",
      valueA: formatWon(comparison.monthly_sales.a),
      valueB: formatWon(comparison.monthly_sales.b),
      winner: comparison.monthly_sales.winner,
      icon: <TrendingUp className="h-4 w-4 text-emerald-500" />,
    },
    {
      label: "생존율",
      valueA: `${(comparison.survival_rate.a * 100).toFixed(1)}%`,
      valueB: `${(comparison.survival_rate.b * 100).toFixed(1)}%`,
      winner: comparison.survival_rate.winner,
      icon: <Scale className="h-4 w-4 text-blue-500" />,
    },
    {
      label: "경쟁점포",
      valueA: `${comparison.store_count.a}개`,
      valueB: `${comparison.store_count.b}개`,
      winner: comparison.store_count.winner,
      icon: <Store className="h-4 w-4 text-purple-500" />,
    },
    {
      label: "유동인구",
      valueA: `${comparison.foot_traffic.a.toLocaleString()}명`,
      valueB: `${comparison.foot_traffic.b.toLocaleString()}명`,
      winner: comparison.foot_traffic.winner,
      icon: <Users className="h-4 w-4 text-cyan-500" />,
    },
    {
      label: "추정임대료",
      valueA: formatWon(district_a.estimated_rent),
      valueB: formatWon(district_b.estimated_rent),
      winner: rentWinner as "A" | "B" | "TIE",
      icon: <Building2 className="h-4 w-4 text-rose-500" />,
    },
  ];

  const winnerCell = "bg-emerald-50 border-emerald-200 font-bold text-emerald-700";

  return (
    <div className="space-y-6">
      {/* Table header */}
      <div className="grid grid-cols-[1fr_1fr_auto_1fr] items-end gap-2 sm:gap-4">
        <div className="text-center">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1">
            <span className="flex h-5 w-5 items-center justify-center rounded-md bg-gradient-to-br from-blue-500 to-blue-600 text-[10px] font-extrabold text-white">
              A
            </span>
            <span className="text-sm font-bold text-blue-800">{district_a.district_name}</span>
          </div>
          <p className="mt-1 text-[10px] text-slate-400">{district_a.district_type} · 피크 {district_a.peak_time} · 주고객 {district_a.main_age_group}</p>
        </div>
        <div />
        <div className="flex items-center justify-center text-xs font-bold text-slate-400">VS</div>
        <div className="text-center">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-violet-50 px-3 py-1">
            <span className="flex h-5 w-5 items-center justify-center rounded-md bg-gradient-to-br from-violet-500 to-violet-600 text-[10px] font-extrabold text-white">
              B
            </span>
            <span className="text-sm font-bold text-violet-800">{district_b.district_name}</span>
          </div>
          <p className="mt-1 text-[10px] text-slate-400">{district_b.district_type} · 피크 {district_b.peak_time} · 주고객 {district_b.main_age_group}</p>
        </div>
      </div>

      {/* Metric rows */}
      <div className="space-y-2">
        {metrics.map((m) => (
          <div
            key={m.label}
            className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 sm:gap-4"
          >
            {/* A value */}
            <div
              className={cn(
                "rounded-xl border px-3 py-3 text-center transition-all sm:px-4",
                m.winner === "A" ? winnerCell : "border-slate-200 bg-white text-slate-700",
              )}
            >
              <p className="text-base font-extrabold sm:text-lg">{m.valueA}</p>
              {m.winner === "A" && (
                <span className="text-[10px] font-semibold text-emerald-600">우세</span>
              )}
            </div>

            {/* Label */}
            <div className="flex min-w-[80px] flex-col items-center gap-0.5 sm:min-w-[100px]">
              {m.icon}
              <span className="text-[11px] font-bold text-slate-500">{m.label}</span>
            </div>

            {/* B value */}
            <div
              className={cn(
                "rounded-xl border px-3 py-3 text-center transition-all sm:px-4",
                m.winner === "B" ? winnerCell : "border-slate-200 bg-white text-slate-700",
              )}
            >
              <p className="text-base font-extrabold sm:text-lg">{m.valueB}</p>
              {m.winner === "B" && (
                <span className="text-[10px] font-semibold text-emerald-600">우세</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* AI Verdict card */}
      <div className="rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50/80 to-indigo-50/60 p-5 sm:p-6">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-blue-500" />
          <h3 className="text-sm font-extrabold text-blue-900">AI 판정</h3>
        </div>
        <p className="text-sm leading-relaxed text-blue-900/80">{ai_verdict}</p>
      </div>

      {/* CTA buttons */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Link
          href={`/analyze/report?district_code=${encodeURIComponent(district_a.district_code)}&industry_code=${encodeURIComponent(industryCode)}`}
          className={cn(
            "flex items-center justify-center gap-2 rounded-xl border-2 border-blue-200 bg-blue-50/60 px-4 py-3 text-sm font-bold text-blue-700 transition",
            "hover:border-blue-300 hover:bg-blue-100/60 hover:shadow-sm",
          )}
        >
          <span className="flex h-5 w-5 items-center justify-center rounded-md bg-gradient-to-br from-blue-500 to-blue-600 text-[10px] font-extrabold text-white">
            A
          </span>
          {district_a.district_name} 상세 분석
          <ArrowRight className="h-4 w-4" />
        </Link>
        <Link
          href={`/analyze/report?district_code=${encodeURIComponent(district_b.district_code)}&industry_code=${encodeURIComponent(industryCode)}`}
          className={cn(
            "flex items-center justify-center gap-2 rounded-xl border-2 border-violet-200 bg-violet-50/60 px-4 py-3 text-sm font-bold text-violet-700 transition",
            "hover:border-violet-300 hover:bg-violet-100/60 hover:shadow-sm",
          )}
        >
          <span className="flex h-5 w-5 items-center justify-center rounded-md bg-gradient-to-br from-violet-500 to-violet-600 text-[10px] font-extrabold text-white">
            B
          </span>
          {district_b.district_name} 상세 분석
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}

// ─── Loading Skeleton ───────────────────────────────────────────────────
function ComparisonSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-[1fr_auto_1fr] gap-4">
        <Skeleton className="h-10 w-full" />
        <div className="flex items-center text-xs font-bold text-slate-300">VS</div>
        <Skeleton className="h-10 w-full" />
      </div>
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={`skel-row-${i}`} className="grid grid-cols-[1fr_auto_1fr] gap-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-4 w-16 self-center" />
          <Skeleton className="h-16 w-full" />
        </div>
      ))}
      <Skeleton className="h-32 w-full rounded-2xl" />
    </div>
  );
}

// ─── Main Inner Component ───────────────────────────────────────────────
function CompareInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const paramA = searchParams?.get("a") || "";
  const paramB = searchParams?.get("b") || "";
  const industryCode = searchParams?.get("industry_code") || "CS100010";

  const [selectedA, setSelectedA] = useState<{ code: string; name: string } | null>(
    paramA ? { code: paramA, name: paramA } : null,
  );
  const [selectedB, setSelectedB] = useState<{ code: string; name: string } | null>(
    paramB ? { code: paramB, name: paramB } : null,
  );

  const [compareData, setCompareData] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const doCompare = useCallback(
    (codeA: string, codeB: string) => {
      if (!codeA || !codeB) return;
      setLoading(true);
      setError(null);
      setCompareData(null);

      fetchWithTimeout(
        `${API_BASE}/compare?a=${encodeURIComponent(codeA)}&b=${encodeURIComponent(codeB)}&industry_code=${encodeURIComponent(industryCode)}`,
      )
        .then((r) => {
          if (!r.ok) throw new Error(`서버 오류 (${r.status})`);
          return r.json();
        })
        .then((data: CompareResponse) => {
          setCompareData(data);
          setSelectedA({ code: codeA, name: data.district_a.district_name });
          setSelectedB({ code: codeB, name: data.district_b.district_name });

          track("compare_start" as never, { a: codeA, b: codeB });
        })
        .catch((err) => {
          if (err.name === "AbortError") {
            setError("요청 시간이 초과되었습니다. 다시 시도해주세요.");
          } else {
            setError(err.message || "비교 데이터를 불러오지 못했습니다.");
          }
        })
        .finally(() => setLoading(false));
    },
    [industryCode],
  );

  // Auto-fetch if both params present on mount
  useEffect(() => {
    if (paramA && paramB) {
      doCompare(paramA, paramB);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCompare = () => {
    if (!selectedA?.code || !selectedB?.code) return;
    const params = new URLSearchParams();
    params.set("a", selectedA.code);
    params.set("b", selectedB.code);
    params.set("industry_code", industryCode);
    router.push(`/compare?${params.toString()}`);
    doCompare(selectedA.code, selectedB.code);
  };

  const bothSelected = Boolean(selectedA?.code && selectedB?.code);

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600">
              <MapPin className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-bold text-slate-900">SpotPick</span>
          </Link>
          <Link
            href="/analyze"
            className="text-sm font-medium text-slate-600 hover:text-slate-900"
          >
            ← 분석으로
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
        {/* Page title */}
        <div className="mb-8 text-center">
          <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            <Scale className="h-3.5 w-3.5" />
            상권 비교
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
            두 상권, 나란히 비교하기
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            관심 상권 2곳을 선택하면 6가지 핵심 지표를 한눈에 비교합니다
          </p>
        </div>

        {/* Search inputs */}
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:gap-3">
          <DistrictSearchInput
            label="첫 번째 상권"
            side="A"
            selected={selectedA}
            onSelect={(code, name) =>
              setSelectedA(code ? { code, name } : null)
            }
            industryCode={industryCode}
          />
          <DistrictSearchInput
            label="두 번째 상권"
            side="B"
            selected={selectedB}
            onSelect={(code, name) =>
              setSelectedB(code ? { code, name } : null)
            }
            industryCode={industryCode}
          />
        </div>

        {/* Compare button */}
        <div className="mb-10 flex justify-center">
          <button
            type="button"
            onClick={handleCompare}
            disabled={!bothSelected || loading}
            className={cn(
              "inline-flex items-center gap-2 rounded-xl px-8 py-3 text-sm font-bold shadow-lg transition",
              bothSelected && !loading
                ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-blue-500/25 hover:shadow-xl hover:shadow-blue-500/30"
                : "cursor-not-allowed bg-slate-200 text-slate-400 shadow-none",
            )}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                비교 분석 중...
              </>
            ) : (
              <>
                <Scale className="h-4 w-4" />
                비교 시작
              </>
            )}
          </button>
        </div>

        {/* States */}
        {loading && <ComparisonSkeleton />}

        {error && !loading && <ErrorCard message={error} onRetry={() => handleCompare()} />}

        {!loading && !error && !compareData && (
          <div className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-10 text-center">
            <Scale className="mx-auto h-10 w-10 text-slate-300" />
            <p className="mt-4 text-sm font-semibold text-slate-500">
              비교할 두 상권을 선택해주세요
            </p>
            <p className="mt-1 text-xs text-slate-400">
              위 검색창에서 상권을 검색하고 선택하세요
            </p>
          </div>
        )}

        {!loading && !error && compareData && (
          <ComparisonTable data={compareData} industryCode={industryCode} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-10">
        <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
          <p className="text-sm text-slate-500">&copy; 2026 SpotPick</p>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">
            데이터 출처: 서울시 우리마을가게 상권분석 · 소상공인시장진흥공단 · 공정거래위원회 정보공개서
          </p>
        </div>
      </footer>
    </div>
  );
}

// ─── Page Export (Suspense wrapper) ─────────────────────────────────────
export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <CompareInner />
    </Suspense>
  );
}
