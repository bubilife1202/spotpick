"use client";

import { type FormEvent, useMemo, useState } from "react";
import { AlertTriangle, Loader2, Search, ShieldAlert, ShieldCheck, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const REQUEST_TIMEOUT_MS = 15_000;

type RiskLevel = "high" | "medium" | "low";

interface TrademarkConflict {
  name: string;
  similarity: number;
}

interface TrademarkCheckResponse {
  query: string;
  conflicts: TrademarkConflict[];
  risk_level: RiskLevel;
  suggestions: string[];
}

interface TrademarkCheckCardProps {
  industryCode: string;
}

function riskBadgeStyle(level: RiskLevel) {
  if (level === "high") {
    return {
      label: "높음",
      className: "border-rose-200 bg-rose-50 text-rose-700",
      icon: ShieldAlert,
    };
  }
  if (level === "medium") {
    return {
      label: "보통",
      className: "border-amber-200 bg-amber-50 text-amber-700",
      icon: AlertTriangle,
    };
  }
  return {
    label: "낮음",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
    icon: ShieldCheck,
  };
}

function formatSimilarity(similarity: number) {
  const value = similarity <= 1 ? similarity * 100 : similarity;
  return `${Math.max(0, Math.min(100, value)).toFixed(1)}%`;
}

export function TrademarkCheckCard({ industryCode }: TrademarkCheckCardProps) {
  const [brandName, setBrandName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TrademarkCheckResponse | null>(null);

  const canSubmit = useMemo(() => brandName.trim().length > 0 && !loading, [brandName, loading]);

  const runCheck = async () => {
    const query = brandName.trim();
    if (!query || !industryCode || loading) return;

    setLoading(true);
    setError(null);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const params = new URLSearchParams({ name: query, industry_code: industryCode });
      const res = await fetch(`${API_BASE}/trademark/check?${params.toString()}`, {
        method: "GET",
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const json = (await res.json()) as TrademarkCheckResponse;
      setResult(json);
    } catch (err) {
      setResult(null);
      if (err instanceof Error && err.name === "AbortError") {
        setError("요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.");
      } else {
        setError("상표 검사를 불러오지 못했습니다. 다시 시도해 주세요.");
      }
    } finally {
      clearTimeout(timeoutId);
      setLoading(false);
    }
  };

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void runCheck();
  };

  const riskStyle = result ? riskBadgeStyle(result.risk_level) : null;
  const RiskIcon = riskStyle?.icon;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-slate-900 text-white">
          <ShieldCheck className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <h3 className="text-base font-extrabold text-slate-900">상표 충돌 검사</h3>
          <p className="mt-0.5 text-xs text-slate-500">브랜드명을 입력하면 유사 상표와 위험도를 빠르게 확인합니다</p>
        </div>
      </div>

      <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-2 sm:flex-row">
        <label htmlFor="trademark-name" className="sr-only">상호명</label>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            id="trademark-name"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            placeholder="예: 스타벅스"
            className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-900 outline-none transition focus:border-slate-400"
          />
        </div>
        <button
          type="submit"
          disabled={!canSubmit}
          className={cn(
            "inline-flex h-10 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition",
            canSubmit
              ? "bg-slate-900 text-white hover:bg-slate-800"
              : "cursor-not-allowed bg-slate-100 text-slate-400",
          )}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
          검사
        </button>
      </form>

      {error && (
        <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {!error && !loading && result && riskStyle && RiskIcon && (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-slate-700">위험도</span>
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold",
                riskStyle.className,
              )}
            >
              <RiskIcon className="h-3.5 w-3.5" />
              {riskStyle.label}
            </span>
            <span className="text-xs text-slate-500">검사어: {result.query}</span>
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">충돌 후보</p>
            {result.conflicts.length > 0 ? (
              <div className="mt-2 space-y-2">
                {result.conflicts.map((conflict) => (
                  <div
                    key={`${conflict.name}-${conflict.similarity}`}
                    className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-2"
                  >
                    <span className="truncate pr-3 text-sm font-medium text-slate-800">{conflict.name}</span>
                    <span className="text-xs font-bold text-slate-600">유사도 {formatSimilarity(conflict.similarity)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                현재 충돌 가능성이 높은 상표가 발견되지 않았습니다.
              </div>
            )}
          </div>

          {result.suggestions.length > 0 && (
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">추천 대안명</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {result.suggestions.map((suggestion) => (
                  <span
                    key={suggestion}
                    className="inline-flex items-center gap-1.5 rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-700"
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    {suggestion}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
