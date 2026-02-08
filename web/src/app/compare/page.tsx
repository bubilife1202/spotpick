"use client";

import { useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  MapPin,
  Search,
  Loader2,
  ArrowRight,
  Sparkles,
  TrendingUp,
  Store,
  Shield,
  Users,
  Coins,
  X,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface DistrictOption {
  code: string;
  name: string;
  type: string;
}

interface CompareResult {
  a: Record<string, unknown>;
  b: Record<string, unknown>;
  metrics: { name: string; a_value: number; b_value: number; winner: string; unit: string }[];
  verdict: string;
}

/* ─── District Search Dropdown ─────────────────────────────── */
function DistrictSearch({
  label,
  value,
  onChange,
  industryCode,
}: {
  label: string;
  value: DistrictOption | null;
  onChange: (d: DistrictOption | null) => void;
  industryCode: string;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DistrictOption[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const search = useCallback(
    async (q: string) => {
      if (q.length < 1) {
        setResults([]);
        return;
      }
      setLoading(true);
      try {
        const res = await fetch(
          `${API_BASE}/districts/search?q=${encodeURIComponent(q)}&limit=10&industry_code=${industryCode}`,
        );
        if (!res.ok) throw new Error("search failed");
        const data = await res.json();
        setResults(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (data.results || []).map((r: any) => ({
            code: r.code,
            name: r.name,
            type: r.type,
          })),
        );
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [industryCode],
  );

  return (
    <div className="relative flex-1">
      <label className="mb-1.5 block text-xs font-semibold text-slate-500">
        {label}
      </label>
      {value ? (
        <div className="flex items-center justify-between rounded-xl border border-blue-200 bg-blue-50 px-4 py-2.5">
          <div>
            <p className="text-sm font-bold text-slate-900">{value.name}</p>
            <p className="text-[10px] text-slate-500">{value.type}</p>
          </div>
          <button
            onClick={() => {
              onChange(null);
              setQuery("");
            }}
            className="rounded-full p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="상권명, 구, 역 검색..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
              search(e.target.value);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 200)}
            className="w-full rounded-xl border border-slate-200 py-2.5 pl-10 pr-4 text-sm text-slate-900 transition focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
          />
          {open && (results.length > 0 || loading) && (
            <div className="absolute left-0 right-0 top-full z-20 mt-1 max-h-52 overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-lg">
              {loading ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                </div>
              ) : (
                results.map((r) => (
                  <button
                    key={r.code}
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => {
                      onChange(r);
                      setOpen(false);
                      setQuery("");
                    }}
                    className="flex w-full items-center justify-between px-4 py-2.5 text-left text-sm hover:bg-slate-50"
                  >
                    <span className="font-medium text-slate-900">{r.name}</span>
                    <span className="text-[10px] text-slate-400">{r.type}</span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Metric Row ───────────────────────────────────────────── */
function MetricRow({
  icon,
  label,
  aValue,
  bValue,
  winner,
  unit,
  format,
}: {
  icon: React.ReactNode;
  label: string;
  aValue: number;
  bValue: number;
  winner: string;
  unit: string;
  format?: (v: number) => string;
}) {
  const fmt = format || ((v: number) => `${v.toLocaleString()}${unit}`);
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50/50 px-4 py-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white text-slate-400">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-medium text-slate-400">{label}</p>
        <div className="mt-0.5 flex items-center gap-3">
          <span
            className={cn(
              "text-sm font-extrabold",
              winner === "a" ? "text-blue-600" : "text-slate-700",
            )}
          >
            {fmt(aValue)}
          </span>
          <span className="text-[10px] text-slate-300">vs</span>
          <span
            className={cn(
              "text-sm font-extrabold",
              winner === "b" ? "text-emerald-600" : "text-slate-700",
            )}
          >
            {fmt(bValue)}
          </span>
        </div>
      </div>
      {winner !== "tie" && (
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[9px] font-bold",
            winner === "a"
              ? "bg-blue-50 text-blue-600"
              : "bg-emerald-50 text-emerald-600",
          )}
        >
          {winner === "a" ? "A" : "B"} 우세
        </span>
      )}
    </div>
  );
}

/* ─── Compare Content ──────────────────────────────────────── */
function CompareContent() {
  const searchParams = useSearchParams();
  const industryCode = searchParams?.get("industry_code") || "CS100010";

  const [districtA, setDistrictA] = useState<DistrictOption | null>(null);
  const [districtB, setDistrictB] = useState<DistrictOption | null>(null);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runCompare = async () => {
    if (!districtA || !districtB) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/compare?a=${districtA.code}&b=${districtB.code}&industry_code=${industryCode}`,
      );
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch {
      setError("비교 분석에 실패했습니다. 다시 시도해주세요.");
    } finally {
      setLoading(false);
    }
  };

  const METRIC_CONFIG: Record<string, { icon: React.ReactNode; format?: (v: number) => string }> = {
    scorecard: { icon: <TrendingUp className="h-4 w-4" /> },
    monthly_sales: {
      icon: <Coins className="h-4 w-4" />,
      format: (v: number) => {
        if (v >= 10000) return `${Math.round(v / 10000).toLocaleString()}만원`;
        return `${v.toLocaleString()}원`;
      },
    },
    survival_rate: {
      icon: <Shield className="h-4 w-4" />,
      format: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
    store_count: { icon: <Store className="h-4 w-4" /> },
    foot_traffic: { icon: <Users className="h-4 w-4" /> },
  };

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
            className="text-sm font-medium text-slate-500 hover:text-slate-700"
          >
            분석으로 돌아가기
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-20 pt-8 sm:px-6">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-extrabold text-slate-900 sm:text-3xl">
            상권 비교 분석
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            두 상권을 나란히 비교하고 AI 판정을 확인하세요
          </p>
        </div>

        {/* Search inputs */}
        <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row">
            <DistrictSearch
              label="상권 A"
              value={districtA}
              onChange={setDistrictA}
              industryCode={industryCode}
            />
            <div className="flex items-end justify-center pb-2">
              <span className="text-lg font-bold text-slate-300">VS</span>
            </div>
            <DistrictSearch
              label="상권 B"
              value={districtB}
              onChange={setDistrictB}
              industryCode={industryCode}
            />
          </div>

          <button
            onClick={runCompare}
            disabled={!districtA || !districtB || loading}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-3 text-sm font-semibold text-white shadow-md transition hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                비교 분석 중...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                AI 비교 분석
              </>
            )}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-xl border border-rose-200 bg-rose-50 p-4 text-center text-sm text-rose-600">
            {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4">
              <div className="text-center flex-1">
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-[10px] font-bold text-blue-600">
                  A
                </span>
                <p className="mt-1 text-sm font-bold text-slate-900">
                  {(result.a.district_name as string) || "상권 A"}
                </p>
                <p className="text-[10px] text-slate-500">
                  {(result.a.district_type as string) || ""}
                </p>
              </div>
              <div className="text-lg font-bold text-slate-300">VS</div>
              <div className="text-center flex-1">
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-[10px] font-bold text-emerald-600">
                  B
                </span>
                <p className="mt-1 text-sm font-bold text-slate-900">
                  {(result.b.district_name as string) || "상권 B"}
                </p>
                <p className="text-[10px] text-slate-500">
                  {(result.b.district_type as string) || ""}
                </p>
              </div>
            </div>

            {/* Metrics */}
            <div className="space-y-2">
              {result.metrics.map((m) => {
                const cfg = METRIC_CONFIG[m.name] || { icon: <TrendingUp className="h-4 w-4" /> };
                return (
                  <MetricRow
                    key={m.name}
                    icon={cfg.icon}
                    label={m.name}
                    aValue={m.a_value}
                    bValue={m.b_value}
                    winner={m.winner}
                    unit={m.unit}
                    format={cfg.format}
                  />
                );
              })}
            </div>

            {/* AI Verdict */}
            <div className="rounded-2xl border border-blue-100 bg-blue-50/50 p-5">
              <div className="mb-2 flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-blue-500" />
                <h3 className="text-sm font-bold text-blue-900">AI 종합 판정</h3>
              </div>
              <p className="text-sm leading-relaxed text-blue-900/80">
                {result.verdict}
              </p>
            </div>

            {/* CTA */}
            <div className="flex flex-col gap-3 sm:flex-row">
              {districtA && (
                <Link
                  href={`/analyze/report?industry_code=${industryCode}&district_code=${districtA.code}`}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-blue-200 bg-white px-4 py-3 text-sm font-semibold text-blue-600 transition hover:bg-blue-50"
                >
                  A 상세 분석 <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              )}
              {districtB && (
                <Link
                  href={`/analyze/report?industry_code=${industryCode}&district_code=${districtB.code}`}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-emerald-200 bg-white px-4 py-3 text-sm font-semibold text-emerald-600 transition hover:bg-emerald-50"
                >
                  B 상세 분석 <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <CompareContent />
    </Suspense>
  );
}
