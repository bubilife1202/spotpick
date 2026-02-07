"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Search, AlertTriangle, CheckCircle, ShieldAlert } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface TrademarkConflict {
  name: string;
  similarity: number;
}

interface TrademarkResult {
  query: string;
  conflicts: TrademarkConflict[];
  risk_level: "high" | "medium" | "low";
  suggestions: string[];
}

interface TrademarkCheckProps {
  industryCode?: string;
  initialResult?: TrademarkResult;
}

const RISK_CONFIG = {
  high: {
    icon: ShieldAlert,
    color: "text-rose-600",
    bg: "bg-rose-50 border-rose-200",
    label: "높음",
    badge: "bg-rose-100 text-rose-700",
  },
  medium: {
    icon: AlertTriangle,
    color: "text-amber-600",
    bg: "bg-amber-50 border-amber-200",
    label: "주의",
    badge: "bg-amber-100 text-amber-700",
  },
  low: {
    icon: CheckCircle,
    color: "text-emerald-600",
    bg: "bg-emerald-50 border-emerald-200",
    label: "양호",
    badge: "bg-emerald-100 text-emerald-700",
  },
};

export function TrademarkCheck({ industryCode = "CS100010", initialResult }: TrademarkCheckProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TrademarkResult | null>(initialResult ?? null);

  const handleSearch = async () => {
    const name = query.trim();
    if (!name) return;

    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/trademark/check?name=${encodeURIComponent(name)}&industry_code=${encodeURIComponent(industryCode)}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: TrademarkResult = await res.json();
      setResult(data);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const risk = result ? RISK_CONFIG[result.risk_level] : null;
  const RiskIcon = risk?.icon ?? CheckCircle;

  return (
    <div className="space-y-3">
      {/* Search input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="상호명을 입력하세요"
          className={cn(
            "flex-1 px-3 py-2 text-sm rounded-lg border border-slate-200",
            "focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
          )}
        />
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className={cn(
            "px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5",
            "bg-blue-600 text-white hover:bg-blue-700",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "transition-colors"
          )}
        >
          <Search size={14} />
          {loading ? "검색 중..." : "확인"}
        </button>
      </div>

      {/* Results */}
      {result && risk && (
        <div className={cn("rounded-xl border p-4 space-y-3", risk.bg)}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <RiskIcon size={18} className={risk.color} />
              <span className="text-sm font-semibold text-slate-800">
                &ldquo;{result.query}&rdquo; 상표 충돌 확인
              </span>
            </div>
            <span className={cn("text-xs font-semibold px-2.5 py-1 rounded-full", risk.badge)}>
              위험도: {risk.label}
            </span>
          </div>

          {/* Conflicts */}
          {result.conflicts.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-slate-600">유사 상표:</p>
              <div className="flex flex-wrap gap-2">
                {result.conflicts.map((c, i) => (
                  <span
                    key={i}
                    className={cn(
                      "px-2.5 py-1 rounded-lg text-xs font-medium border",
                      c.similarity >= 0.95
                        ? "bg-rose-100 text-rose-800 border-rose-200"
                        : c.similarity >= 0.85
                          ? "bg-amber-100 text-amber-800 border-amber-200"
                          : "bg-slate-100 text-slate-700 border-slate-200"
                    )}
                  >
                    {c.name}
                    <span className="ml-1 opacity-70">
                      ({Math.round(c.similarity * 100)}%)
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.conflicts.length === 0 && (
            <p className="text-sm text-emerald-700">
              등록된 유사 상표를 찾지 못했습니다. 다만 정확한 확인을 위해 KIPRIS 검색을 권장합니다.
            </p>
          )}

          {/* Suggestions */}
          {result.suggestions.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-600">권장 사항:</p>
              <ul className="text-xs text-slate-600 space-y-0.5">
                {result.suggestions.map((s, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="text-slate-400 mt-0.5">•</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
