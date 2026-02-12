"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { track } from "@/lib/analytics";
import { useAnalyzeStore, type TopDistrict } from "@/lib/analyze-store";
import { AnalyzeStepper } from "@/components/AnalyzeStepper";
import { LocationProfile } from "@/components/LocationProfile";
import { RentTrendChart } from "@/components/RentTrendChart";
import { MiniMap } from "@/components/MiniMap";
import { CompetitionMap } from "@/components/CompetitionMap";
import { ProGateSection } from "@/components/ProGateSection";
import { SalesTrendChart } from "@/components/SalesTrendChart";
import { FloatingTOC } from "@/components/FloatingTOC";
import { CafeTypeCard } from "@/components/CafeTypeCard";
import { BenchmarkAnalysisCard } from "@/components/BenchmarkAnalysisCard";
import { CompetitiveInsightCard } from "@/components/CompetitiveInsightCard";
import { TrademarkCheckCard } from "@/components/TrademarkCheckCard";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ErrorCard } from "@/components/ErrorCard";
import {
  MapPin,
  ArrowRight,
  Sparkles,
  Loader2,
  Trophy,
  Target,
  TrendingUp,
  Store,
  Users,
  AlertTriangle,
  Building2,
  ArrowDown,
  ArrowUp,
  Minus,
  Gift,
  SlidersHorizontal,
  ChevronRight,
  ChevronDown,
  CreditCard,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  ShieldCheck,
  ArrowLeft,
  ExternalLink,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const FETCH_TIMEOUT_MS = 30_000;

/** Fetch with 30s AbortController timeout */
function fetchWithTimeout(url: string, options?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  return fetch(url, { ...options, signal: controller.signal }).finally(() =>
    clearTimeout(timeoutId),
  );
}

// ─── Skeleton component ────────────────────────────────────────────────
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

function SectionSkeleton({ title }: { title: string }) {
  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Skeleton className="h-5 w-5" />
        <h3 className="text-sm font-bold text-slate-400">{title}</h3>
      </div>
      <div className="space-y-3">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-20 w-full" />
      </div>
    </div>
  );
}

// ─── Data source label ────────────────────────────────────────────────
function DataSource({ text }: { text: string }) {
  return <p className="mt-4 text-[10px] text-slate-400">출처: {text}</p>;
}

// ─── Format helpers ────────────────────────────────────────────────────
function formatWon(value: number): string {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}억원`;
  if (value >= 10_000) return `${Math.round(value / 10_000).toLocaleString()}만원`;
  return `${value.toLocaleString()}원`;
}

function getVerdictStyle(score: number) {
  if (score >= 75) return { label: "추천", color: "text-emerald-700", bg: "bg-emerald-50 border-emerald-200" };
  if (score >= 50) return { label: "보통", color: "text-amber-700", bg: "bg-amber-50 border-amber-200" };
  return { label: "주의", color: "text-rose-700", bg: "bg-rose-50 border-rose-200" };
}

function getScoreInterpretation(score: number): string {
  if (score >= 80) return "매우 우수한 수준입니다";
  if (score >= 60) return "양호한 수준입니다";
  if (score >= 40) return "보통 수준입니다";
  return "주의가 필요합니다";
}

// ─── Verdict Card (Hero) ────────────────────────────────────────────────
function VerdictHeroCard({
  district,
  industryCode,
  verdictData,
  verdictLoading,
  onViewAlternative,
}: {
  district: TopDistrict;
  industryCode: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  verdictData: any;
  verdictLoading: boolean;
  onViewAlternative?: (code: string) => void;
}) {
  const verdict: "GO" | "CAUTION" | "NO_GO" = verdictData?.verdict || "CAUTION";
  const confidence: number = verdictData?.confidence || 0;
  const summary: string = verdictData?.summary || "";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const reasons: any[] = verdictData?.reasons || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const alternatives: any[] = verdictData?.alternatives || [];
  const hasBudgetGate = reasons.some((r) => r && r.factor === "예산");

  const configMap = {
    GO: {
      icon: <CheckCircle2 className="h-10 w-10 text-emerald-400 sm:h-12 sm:w-12" />,
      emoji: "🟢",
      label: "GO",
      subtitle: "가능성이 있습니다",
      bg: "from-emerald-950 via-emerald-900 to-emerald-950",
      border: "border-emerald-500/40",
      glow: "shadow-emerald-500/20",
      accent: "text-emerald-300",
      accentBg: "bg-emerald-500/15",
      badgeBg: "bg-emerald-500",
      ringColor: "ring-emerald-400/30",
    },
    CAUTION: {
      icon: <ShieldAlert className="h-10 w-10 text-amber-400 sm:h-12 sm:w-12" />,
      emoji: "🟡",
      label: "CAUTION",
      subtitle: "조건부 추천입니다",
      bg: "from-amber-950 via-amber-900 to-amber-950",
      border: "border-amber-500/40",
      glow: "shadow-amber-500/20",
      accent: "text-amber-300",
      accentBg: "bg-amber-500/15",
      badgeBg: "bg-amber-500",
      ringColor: "ring-amber-400/30",
    },
    NO_GO: {
      icon: <XCircle className="h-10 w-10 text-rose-400 sm:h-12 sm:w-12" />,
      emoji: "🔴",
      label: "NO-GO",
      subtitle: "추천하지 않습니다",
      bg: "from-rose-950 via-rose-900 to-rose-950",
      border: "border-rose-500/40",
      glow: "shadow-rose-500/20",
      accent: "text-rose-300",
      accentBg: "bg-rose-500/15",
      badgeBg: "bg-rose-500",
      ringColor: "ring-rose-400/30",
    },
  };
  const config = configMap[verdict];

  if (verdictLoading || !verdictData) {
    return (
      <div className="overflow-hidden rounded-3xl border border-slate-700/50 bg-gradient-to-br from-slate-800 via-slate-900 to-slate-800 p-6 sm:p-10">
        <div className="flex flex-col items-center gap-5">
          <div className="relative">
            <Loader2 className="h-10 w-10 animate-spin text-blue-400 sm:h-12 sm:w-12" />
            <div className="absolute inset-0 animate-ping rounded-full bg-blue-400/10" />
          </div>
          <div className="text-center">
            <p className="text-sm font-semibold text-slate-300">AI 코치가 판정 중...</p>
            <p className="mt-1 text-xs text-slate-500">Go/No-Go 신뢰도를 계산하고 있습니다</p>
          </div>
          <div className="mt-2 w-full max-w-xs space-y-3">
            <Skeleton className="mx-auto h-8 w-20 !bg-slate-700/50" />
            <Skeleton className="mx-auto h-4 w-48 !bg-slate-700/40" />
            <div className="flex justify-center gap-2">
              <Skeleton className="h-3 w-24 !bg-slate-700/30" />
              <Skeleton className="h-3 w-16 !bg-slate-700/30" />
            </div>
            <Skeleton className="mx-auto h-12 w-28 rounded-2xl !bg-slate-700/40" />
          </div>
        </div>
      </div>
    );
  }

  const levelStyles = {
    positive: { bg: "bg-emerald-500/10", text: "text-emerald-200", icon: "✅" },
    warning: { bg: "bg-amber-500/10", text: "text-amber-200", icon: "⚠️" },
    danger: { bg: "bg-rose-500/10", text: "text-rose-200", icon: "🚨" },
  };

  return (
    <div className="animate-scale-in space-y-4">
      <div
        className={cn(
          "relative overflow-hidden rounded-3xl border bg-gradient-to-br p-6 shadow-2xl sm:p-10",
          config.bg,
          config.border,
          config.glow,
        )}
      >
        <div className="pointer-events-none absolute inset-0 opacity-[0.03]" style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='1'/%3E%3C/svg%3E\")" }} />
        <div className={cn("pointer-events-none absolute -right-20 -top-20 h-60 w-60 rounded-full opacity-10 blur-3xl", config.badgeBg)} />

        <div className="relative flex flex-col items-center text-center">
          <div className={cn("mb-3 flex items-center gap-2 rounded-full px-4 py-1.5 ring-1", config.accentBg, config.ringColor)}>
            <span className="text-sm">{config.emoji}</span>
            <span className={cn("text-sm font-extrabold tracking-wider", config.accent)}>
              {config.label}
            </span>
            {confidence > 0 && (
              <span className="ml-1 rounded-full bg-white/10 px-2 py-0.5 text-[10px] font-bold text-white/70">
                신뢰도 {confidence}%
              </span>
            )}
          </div>

          <div className="mb-2">{config.icon}</div>

          <h2 className="mb-1 text-xl font-extrabold text-white sm:text-2xl">
            {config.subtitle}
          </h2>

          <p className="mb-3 text-sm text-white/60">
            1위 추천 상권: <span className="font-bold text-white/90">{district.district_name}</span>
          </p>

          {summary && (
            <p className="mb-5 max-w-lg text-sm leading-relaxed text-white/70">{summary}</p>
          )}

          <div className={cn("mb-6 flex items-baseline gap-1 rounded-2xl px-6 py-3", config.accentBg)}>
            <span className="text-4xl font-black tracking-tight text-white sm:text-5xl">{district.scorecard_total}</span>
            <span className="text-sm font-medium text-white/50">/100</span>
          </div>

          {reasons.length > 0 && (
            <div className="w-full max-w-md space-y-2">
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {reasons.map((reason: any, idx: number) => {
                const style = levelStyles[reason.level as keyof typeof levelStyles] || levelStyles.warning;
                return (
                  <div
                    key={`${reason.factor}-${idx}`}
                    className={cn("flex items-start gap-2.5 rounded-xl px-4 py-2.5 text-left text-sm", style.bg, style.text)}
                  >
                    <span className="mt-0.5 shrink-0">{style.icon}</span>
                    <div className="flex-1 leading-snug">
                      <span className="font-bold">{reason.factor}</span>
                      <span className="mx-1">·</span>
                      <span>{reason.detail}</span>
                      {(reason.data_value || reason.threshold) && (
                        <span className="ml-1 text-xs opacity-70">
                          ({reason.data_value}{reason.threshold ? ` / 기준: ${reason.threshold}` : ""})
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {verdict === "NO_GO" && alternatives.length > 0 && (
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
          <h4 className="mb-3 text-sm font-bold text-slate-900">AI가 추천하는 대안 상권</h4>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {alternatives.slice(0, 3).map((alt: any, i: number) => (
              <button
                key={alt.district_code || i}
                type="button"
                onClick={() => onViewAlternative?.(alt.district_code)}
                className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3 text-left transition hover:border-emerald-300 hover:bg-emerald-50"
              >
                <p className="text-xs font-bold text-emerald-900">{alt.district_name}</p>
                <p className="mt-0.5 text-[10px] text-emerald-700">
                  생존율 {((alt.survival_rate || 0) * 100).toFixed(0)}% ·{" "}
                  임대료 {((alt.estimated_rent || 0) / 10000).toFixed(0)}만원
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {verdict === "NO_GO" && alternatives.length === 0 && (
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
          <h4 className="mb-2 text-sm font-bold text-slate-900">다음 선택지</h4>
          <p className="text-xs leading-relaxed text-slate-600">
            {hasBudgetGate
              ? "현재 예산으로는 표준 매장 기준으로 추천하기 어렵습니다. 예산을 상향하거나, 소형/테이크아웃 형태로 전략을 바꾸는 것을 권장합니다."
              : "리스크가 커서 추천하기 어렵습니다. 조건을 조정하거나 다른 상권을 확인해보세요."}
          </p>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <Link
              href="/analyze"
              className="inline-flex flex-1 items-center justify-center rounded-xl bg-slate-900 px-4 py-2.5 text-xs font-bold text-white transition hover:bg-slate-800"
            >
              조건 변경하기
            </Link>
            <Link
              href={`/explore?industry_code=${encodeURIComponent(industryCode)}`}
              className="inline-flex flex-1 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-xs font-bold text-slate-700 transition hover:bg-slate-50"
            >
              상권 더 둘러보기
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Loading State (Skeleton Verdict) ──────────────────────────────────
function VerdictLoadingSkeleton() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="relative mb-6">
        <Loader2 className="h-12 w-12 animate-spin text-blue-500" />
        <div className="absolute inset-0 h-12 w-12 animate-ping rounded-full bg-blue-400/20" />
      </div>
      <p className="mb-2 px-4 text-center text-sm font-bold text-slate-800 sm:text-base">AI가 1,077개 상권을 분석하고 있어요...</p>
      <p className="mb-8 text-sm text-slate-400">최적의 Go/No-Go 판정을 계산 중입니다</p>

      {/* 3 skeleton verdict cards */}
      <div className="grid w-full max-w-xl grid-cols-3 gap-2 sm:gap-3">
        {[0, 1, 2].map((i) => (
          <div
            key={`skel-${i}`}
            className={cn(
              "animate-pulse rounded-2xl border border-slate-200 bg-white p-4",
              i === 0 && "animation-delay-100",
              i === 1 && "animation-delay-200",
              i === 2 && "animation-delay-300",
            )}
          >
            <Skeleton className="mx-auto mb-3 h-8 w-8 rounded-full" />
            <Skeleton className="mx-auto mb-2 h-3 w-16" />
            <Skeleton className="mx-auto mb-2 h-6 w-12" />
            <Skeleton className="mx-auto h-2 w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── AI Briefing Card ──────────────────────────────────────────────────
function BriefingCard({ districtCode, industryCode }: { districtCode: string; industryCode: string }) {
  const [briefing, setBriefing] = useState<string>("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!districtCode) return;
    setLoading(true);
    setBriefing("");
    setSummary(null);
    fetchWithTimeout(`${API_BASE}/districts/${districtCode}/briefing?industry_code=${industryCode}`)
      .then((r) => r.json())
      .then((data) => {
        setBriefing(data.briefing || "");
        setSummary(data.summary || null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [districtCode, industryCode]);

  if (!districtCode) return null;

  if (loading) {
    return (
      <div className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50/80 to-indigo-50/50 p-5">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 animate-pulse text-blue-500" />
          <h3 className="text-sm font-bold text-blue-900">AI 실시간 브리핑</h3>
        </div>
        <p className="mb-3 text-xs text-blue-600">AI가 상권을 분석하고 있습니다...</p>
        <div className="space-y-2">
          <Skeleton className="h-3 w-full !bg-blue-100/80" />
          <Skeleton className="h-3 w-5/6 !bg-blue-100/80" />
          <Skeleton className="h-3 w-4/6 !bg-blue-100/80" />
        </div>
      </div>
    );
  }

  if (!briefing) return null;

  const formatWonBriefing = (v: number): string => {
    if (v >= 100_000_000) return `${(v / 100_000_000).toFixed(1)}억원`;
    if (v >= 10_000) return `${Math.round(v / 10_000).toLocaleString()}만원`;
    return `${v.toLocaleString()}원`;
  };

  return (
    <div className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50/80 to-indigo-50/50 p-5">
      <div className="mb-2 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-blue-500" />
        <h3 className="text-sm font-bold text-blue-900">AI 실시간 브리핑</h3>
      </div>
      <p className="text-sm leading-relaxed text-blue-900/80">{briefing}</p>
      {summary && (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div className="rounded-lg bg-white/60 px-3 py-2 text-center">
            <p className="text-lg font-bold text-blue-900">{summary.total_score}점</p>
            <p className="text-[10px] text-blue-700">종합점수</p>
          </div>
          <div className="rounded-lg bg-white/60 px-3 py-2 text-center">
            <p className="text-lg font-bold text-blue-900">{(summary.survival_rate * 100).toFixed(0)}%</p>
            <p className="text-[10px] text-blue-700">생존율</p>
          </div>
          <div className="rounded-lg bg-white/60 px-3 py-2 text-center">
            <p className="text-lg font-bold text-blue-900">{formatWonBriefing(summary.sales_per_store)}</p>
            <p className="text-[10px] text-blue-700">점포당 매출</p>
          </div>
          <div className="rounded-lg bg-white/60 px-3 py-2 text-center">
            <p className={cn("text-lg font-bold", summary.risk_level === "high" ? "text-rose-600" : summary.risk_level === "medium" ? "text-amber-600" : "text-emerald-600")}>
              {summary.risk_level === "high" ? "높음" : summary.risk_level === "medium" ? "보통" : "낮음"}
            </p>
            <p className="text-[10px] text-blue-700">위험도</p>
          </div>
        </div>
      )}
      <div className="mt-3 flex items-center gap-3">
        <button onClick={() => document.getElementById("section-scorecard")?.scrollIntoView({ behavior: "smooth" })} className="text-xs font-semibold text-blue-700 underline underline-offset-2">
          자세히 보기
        </button>
        <Link href={`/compare?a=${districtCode}&industry_code=${industryCode}`} className="text-xs font-semibold text-blue-700 underline underline-offset-2">
          비교하기
        </Link>
      </div>
    </div>
  );
}

// ─── Risk Alert Banner ────────────────────────────────────────────────
function RiskAlertBanner({ districtCode, industryCode }: { districtCode: string; industryCode: string }) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [riskData, setRiskAlertData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!districtCode) return;
    setLoading(true);
    fetchWithTimeout(`${API_BASE}/districts/${districtCode}/risk?industry_code=${industryCode}`)
      .then((r) => r.json())
      .then((data) => setRiskAlertData(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [districtCode, industryCode]);

  if (loading || !riskData) return null;

  const level = riskData.risk_level;
  if (level !== "high" && level !== "medium") return null;

  const isHigh = level === "high";
  const signals = (riskData.signals || []).filter(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (s: any) => s.level === "danger" || s.level === "warning"
  );
  const visibleSignals = expanded ? signals : signals.slice(0, 2);

  return (
    <div
      className={cn(
        "rounded-2xl border p-4",
        isHigh
          ? "border-rose-200 bg-rose-50/80"
          : "border-amber-200 bg-amber-50/80",
      )}
    >
      <div className="flex items-center gap-2">
        <AlertTriangle
          className={cn("h-5 w-5", isHigh ? "text-rose-500" : "text-amber-500")}
        />
        <h3
          className={cn(
            "text-sm font-bold",
            isHigh ? "text-rose-800" : "text-amber-800",
          )}
        >
          {isHigh ? "폐업 위험 높음" : "주의 필요"} — 위험도 {riskData.risk_score}점
        </h3>
      </div>
      {visibleSignals.length > 0 && (
        <ul className="mt-2 space-y-1.5">
          {visibleSignals.map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (s: any, i: number) => (
              <li key={`${s.title}-${i}`}>
                <p className={cn("text-xs", isHigh ? "text-rose-700" : "text-amber-700")}>
                  · {s.title}: {s.detail}
                </p>
                {s.advice && (
                  <p className={cn("ml-2 mt-0.5 text-[11px] italic", isHigh ? "text-rose-500" : "text-amber-500")}>
                    {s.advice}
                  </p>
                )}
              </li>
            ),
          )}
        </ul>
      )}
      {signals.length > 2 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className={cn("mt-1.5 text-xs font-medium underline", isHigh ? "text-rose-600" : "text-amber-600")}
        >
          {expanded ? "접기" : `더 보기 (${signals.length - 2}개)`}
        </button>
      )}
      <Link
        href={`/compare?industry_code=${industryCode}`}
        className={cn("mt-3 inline-flex items-center gap-1 text-xs font-semibold underline underline-offset-2", isHigh ? "text-rose-700" : "text-amber-700")}
      >
        대안 상권 찾기 →
      </Link>
    </div>
  );
}

// ─── Section A: TOP 3 Compact Selector ─────────────────────────────────
function Top3Section({
  districts,
  selectedCode,
  onSelect,
  loading,
  industryName,
  benchmarkMarker,
  similarityScores,
}: {
  districts: TopDistrict[];
  selectedCode: string;
  onSelect: (code: string) => void;
  loading: boolean;
  industryName: string;
  benchmarkMarker?: { lat: number; lng: number; label: string } | null;
  similarityScores?: Record<string, number>;
}) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
        <p className="mt-3 text-sm text-slate-500">최적 상권을 분석하고 있습니다...</p>
      </div>
    );
  }

  if (districts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <AlertTriangle className="h-10 w-10 text-amber-400" />
        <p className="mt-3 text-sm text-slate-600">조건에 맞는 상권을 찾지 못했습니다</p>
        <Link href="/analyze" className="mt-3 text-sm font-semibold text-blue-600 hover:text-blue-700">
          조건 변경하기
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Trophy className="h-5 w-5 text-amber-500" />
        <h2 className="text-lg font-extrabold text-slate-900">AI 추천 TOP 3 상권</h2>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {districts.map((d, i) => {
          const isSelected = d.district_code === selectedCode;
          const scoreBadge = d.scorecard_total >= 70
            ? { badge: "bg-emerald-500 text-white", label: "우수" }
            : d.scorecard_total >= 50
              ? { badge: "bg-amber-500 text-white", label: "보통" }
              : { badge: "bg-rose-500 text-white", label: "주의" };
          return (
            <button
              key={d.district_code}
              type="button"
              onClick={() => onSelect(d.district_code)}
              className={cn(
                "relative rounded-xl border-2 p-4 text-left transition-all",
                isSelected
                  ? "border-blue-500 bg-blue-50/50 shadow-md shadow-blue-500/10"
                  : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm",
              )}
            >
              <div
                className={cn(
                  "absolute -top-2.5 left-3 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white",
                  i === 0 ? "bg-amber-500" : i === 1 ? "bg-slate-400" : "bg-amber-700",
                )}
              >
                {i + 1}
              </div>

              <div className="mb-2 flex items-start justify-between">
                <div>
                  <p className="text-sm font-bold text-slate-900">{d.district_name}</p>
                  <span className="text-xs text-slate-500">{d.district_type}</span>
                </div>
                <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-bold", scoreBadge.badge)}>
                  {scoreBadge.label}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] font-medium text-slate-500">AI 종합 점수</p>
                  <p className="text-sm font-extrabold text-slate-900">{d.scorecard_total}<span className="text-[10px] font-normal text-slate-400">/100</span></p>
                </div>
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] font-medium text-slate-500">2년 생존율</p>
                  <p className="text-sm font-extrabold text-slate-900">{(d.survival_rate * 100).toFixed(0)}%</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] font-medium text-slate-500">상권 전체 월 매출</p>
                  <p className="text-sm font-extrabold text-slate-900">{formatWon(d.monthly_sales)}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-1.5">
                  <p className="text-[10px] font-medium text-slate-500">{industryName} 점포 수</p>
                  <p className="text-sm font-extrabold text-slate-900">{d.store_count}개</p>
                </div>
              </div>

               {similarityScores && similarityScores[d.district_code] != null && (
                 <div className="mt-2 flex items-center justify-center gap-1.5 rounded-lg bg-amber-50 px-2 py-1">
                   <Store className="h-3 w-3 text-amber-500" />
                   <span className="text-[10px] font-bold text-amber-700">
                     벤치마크 유사도 {similarityScores[d.district_code]}%
                   </span>
                 </div>
               )}

               <a
                 href={`https://land.naver.com/offices/complexSearch.naver?keyword=${encodeURIComponent(d.district_name)}`}
                 target="_blank"
                 rel="noopener noreferrer"
                 onClick={(e) => e.stopPropagation()}
                 className="mt-2 flex items-center justify-center gap-1 rounded-lg bg-blue-50 px-2 py-1.5 text-[10px] font-semibold text-blue-600 transition hover:bg-blue-100"
               >
                 <Building2 className="h-3 w-3" />
                 매물 보기
                 <ExternalLink className="h-2.5 w-2.5" />
               </a>

               {isSelected && (
                 <div className="mt-2 text-center text-[10px] font-semibold text-blue-600">
                   선택됨 - 아래에서 상세 분석 확인
                 </div>
               )}
            </button>
          );
        })}
      </div>

      {/* Map visualization */}
      <MiniMap
        markers={[
          ...districts.map((d, i) => ({
            lat: d.coordinates?.lat || 37.5665,
            lng: d.coordinates?.lng || 126.9780,
            label: d.district_name,
            type: d.district_code === selectedCode ? ("selected" as const) : ("recommended" as const),
            rank: i + 1,
            successProbability: d.success_probability,
          })),
          ...(benchmarkMarker
            ? [{
                lat: benchmarkMarker.lat,
                lng: benchmarkMarker.lng,
                label: benchmarkMarker.label,
                type: "benchmark" as const,
                rank: 0,
                successProbability: 0,
              }]
            : []),
        ]}
        height={280}
        zoom={12}
      />
    </div>
  );
}

// ─── Section B1: Scorecard ───────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ScorecardSection({ data, loading, districtName, industryName }: { data: any; loading: boolean; districtName: string; industryName: string }) {
  if (loading) return <SectionSkeleton title="성공 점수" />;
  if (!data) return null;

  const categories = data.categories || [];
  const total = data.total_score ?? 0;
  const verdict = getVerdictStyle(total);
  const percentileValue = data.percentile != null ? Math.max(1, Math.round(100 - data.percentile)) : null;

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Target className="h-5 w-5 text-blue-500" />
        <h3 className="text-sm font-bold text-slate-900">B1. {districtName} 성공 점수</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[9px] font-semibold text-blue-600">
          <CreditCard className="h-2.5 w-2.5" />
          카드매출 기반
        </span>
      </div>

      <div className="mb-4 flex items-center gap-4">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50">
          <span className="text-2xl font-extrabold text-blue-600">{total}</span>
        </div>
        <div>
          <span className={cn("rounded-full border px-2.5 py-0.5 text-xs font-bold", verdict.bg, verdict.color)}>
            {verdict.label}
          </span>
          <p className="mt-1 text-xs text-slate-500">
            {percentileValue != null ? `서울 평균 대비 상위 ${percentileValue}%` : ""}
          </p>
        </div>
      </div>

      {/* Interpretation */}
      <div className="mb-4 rounded-lg bg-blue-50/50 p-3">
        <p className="text-xs leading-relaxed text-blue-800">
          이 점수는 서울시 {industryName} 전체 상권 중 {percentileValue != null ? `상위 ${percentileValue}%에 해당하며, ` : ""}매출·인구·경쟁·입지 4개 항목을 종합한 결과입니다.
        </p>
      </div>

      <div className="space-y-2">
        {categories.map(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (cat: any) => {
            const score = cat.score ?? 0;
            const pctWidth = Math.min(100, score);
            return (
              <div key={cat.name}>
                <div className="flex items-center gap-3">
                  <span className="w-16 text-xs font-medium text-slate-600">{cat.name}</span>
                  <div className="flex-1">
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all duration-500",
                          score >= 80 ? "bg-gradient-to-r from-emerald-400 to-emerald-500"
                            : score >= 60 ? "bg-gradient-to-r from-blue-400 to-indigo-500"
                            : score >= 40 ? "bg-gradient-to-r from-amber-400 to-orange-500"
                            : "bg-gradient-to-r from-rose-400 to-rose-500",
                        )}
                        style={{ width: `${pctWidth}%` }}
                      />
                    </div>
                  </div>
                  <span className={cn(
                    "w-12 text-right text-xs font-bold",
                    score >= 80 ? "text-emerald-700"
                      : score >= 60 ? "text-blue-700"
                      : score >= 40 ? "text-amber-700"
                      : "text-rose-700",
                  )}>
                    {score}점
                  </span>
                </div>
                <p className="ml-[76px] hidden text-[10px] text-slate-400 sm:block">{getScoreInterpretation(score)}</p>
              </div>
            );
          },
        )}
      </div>

      <DataSource text="서울시 상권분석서비스 종합" />
    </div>
  );
}

// ─── Section B2: Revenue Waterfall ─────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function RevenueSection({ data, loading, districtName, industryName }: { data: any; loading: boolean; districtName: string; industryName: string }) {
  if (loading) return <SectionSkeleton title="예상 수익 구조" />;
  if (!data) return null;

  const revenue = data.revenue || {};
  const operating = data.operating_cost || {};
  const breakEven = data.break_even || {};
  const assumptions = data.assumptions || {};
  const storeCount = revenue.store_count || data.store_count || 0;
  const areaPyeong = assumptions.area_pyeong || 15;
  const areaSummary = assumptions.summary || `${areaPyeong}평 기준`;

  const monthlySales = revenue.monthly_sales_per_store || 0;
  const netProfit = breakEven.monthly_net_profit || 0;
  const laborAmount = operating.labor || 0;
  const laborCount = laborAmount > 0 ? Math.round(laborAmount / 2_500_000) : 0;
  const cogsRatio = monthlySales > 0 ? Math.round((operating.cogs || 0) / monthlySales * 100) : 32;
  const utilitiesAmount = operating.utilities || 0;
  const otherAmount = operating.other || 0;

  const items = [
    { label: "월 매출", value: monthlySales, color: "bg-blue-500", type: "positive", desc: storeCount > 0 ? `${districtName} ${industryName} 전체 카드매출 ÷ 점포 ${storeCount}개` : "상권 카드매출 데이터 기반" },
    { label: "식재료비", value: -(operating.cogs || 0), color: "bg-orange-400", type: "negative", desc: `KREI 외식업체경영실태조사 기준 매출의 ${cogsRatio}%` },
    { label: "인건비", value: -laborAmount, color: "bg-amber-400", type: "negative", desc: laborCount > 0 ? `직원 ${laborCount}명 × 250만원 (급여+4대보험), KREI 실측 기반` : "KREI 외식업체경영실태조사 기반" },
    { label: "임대료", value: -(operating.rent || 0), color: "bg-rose-400", type: "negative", desc: `${districtName} 상권 등급·${areaPyeong}평 면적 기준 추정 월세` },
    { label: "기타비용", value: -(utilitiesAmount + otherAmount), color: "bg-slate-400", type: "negative", desc: `공과금(${formatWon(utilitiesAmount)}) + 잡비·소모품(${formatWon(otherAmount)})` },
    { label: "순이익", value: netProfit, color: netProfit >= 0 ? "bg-emerald-500" : "bg-rose-500", type: "result", desc: "매출 - 식재료비 - 인건비 - 임대료 - 기타비용" },
  ];

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-emerald-500" />
        <h3 className="text-sm font-bold text-slate-900">B2. {districtName} 예상 수익 구조</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[9px] font-semibold text-emerald-600">
          <CreditCard className="h-2.5 w-2.5" />
          카드매출 기반
        </span>
      </div>

      {/* Explanation box */}
      <div className="mb-4 rounded-lg bg-blue-50/50 p-3">
        <p className="text-xs leading-relaxed text-blue-800">
          <strong>{areaSummary}</strong> 기준 시뮬레이션입니다.
          서울시 공공데이터(카드매출)에서 {districtName} 상권의 {industryName} 실제 월평균 매출을 기반으로 산출했습니다.
          {storeCount > 0 && ` 점포당 매출은 해당 상권 내 같은 업종 가게 수(${storeCount}개)로 나누어 추정한 값입니다.`}
        </p>
      </div>

      {/* Waterfall visualization */}
      <div className="space-y-2">
        {items.map((item) => {
          const absValue = Math.abs(item.value);
          const pct = monthlySales > 0 ? (absValue / monthlySales) * 100 : 0;
          return (
            <div key={item.label}>
              <div className="flex items-center gap-2 sm:gap-3">
                <span className="w-14 shrink-0 text-xs font-medium text-slate-600 sm:w-16">{item.label}</span>
                <div className="flex-1">
                  <div className="h-5 overflow-hidden rounded bg-slate-50">
                    <div
                      className={cn("h-full rounded transition-all duration-500", item.color)}
                      style={{ width: `${Math.min(100, pct)}%` }}
                    />
                  </div>
                </div>
                <span className={cn("w-16 shrink-0 text-right text-[11px] font-bold sm:w-20 sm:text-xs", item.value >= 0 ? "text-slate-700" : "text-rose-600")}>
                  {item.value >= 0 ? "" : "-"}{formatWon(absValue)}
                </span>
              </div>
              {item.desc && (
                <p className="ml-14 hidden text-[10px] text-slate-400 sm:ml-[76px] sm:block">({item.desc})</p>
              )}
            </div>
          );
        })}
      </div>

      {/* Break-even */}
      <div className="mt-4 grid grid-cols-3 gap-2 sm:gap-3">
        <div className="rounded-xl bg-slate-50 p-2 text-center sm:p-3">
          <p className="text-[10px] text-slate-400">순이익률</p>
          <p className="text-xs font-extrabold text-slate-900 sm:text-sm">
            {((breakEven.net_profit_margin || 0) * 100).toFixed(1)}%
          </p>
          <p className="hidden text-[9px] text-slate-400 sm:block">순이익 ÷ 매출</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-2 text-center sm:p-3">
          <p className="text-[10px] text-slate-400">투자회수</p>
          <p className="text-xs font-extrabold text-slate-900 sm:text-sm">
            {breakEven.break_even_months_min || "-"}~{breakEven.break_even_months_max || "-"}개월
          </p>
          <p className="hidden text-[9px] text-slate-400 sm:block">초기투자 ÷ 월순이익</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-2 text-center sm:p-3">
          <p className="text-[10px] text-slate-400">일 손익분기</p>
          <p className="text-xs font-extrabold text-slate-900 sm:text-sm">
            {formatWon(breakEven.daily_break_even_sales || 0)}
          </p>
          <p className="hidden text-[9px] text-slate-400 sm:block">월 고정비 ÷ 30일</p>
        </div>
      </div>

      <a
        href="#section-simulator"
        className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700"
      >
        시뮬레이터로 조정해보기 <ChevronRight className="h-3 w-3" />
      </a>

      <DataSource text="서울시 카드매출 데이터 기반 추정" />
    </div>
  );
}

// ─── Section B3: Competition ───────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CompetitionSection({ data, loading, localdataData, localdataLoading, districtName, industryName }: { data: any; loading: boolean; localdataData?: any; localdataLoading?: boolean; districtName: string; industryName: string }) {
  if (loading) return <SectionSkeleton title="경쟁 환경" />;
  if (!data) return null;

  const stores = data.stores || {};
  const storeCount = stores.store_count || stores.total || 0;
  const newStores = stores.new_stores || 0;
  const closedStores = stores.closed_stores || 0;
  const franchiseStores = stores.franchise_stores || 0;
  const franchiseRatio = storeCount > 0 ? ((franchiseStores / storeCount) * 100).toFixed(0) : "0";
  const netGrowth = newStores - closedStores;

  const strategyText = netGrowth > 0
    ? "신규 진입이 활발한 상권입니다. 차별화 전략이 중요합니다."
    : netGrowth < 0
      ? "폐업이 신규 개업보다 많아 경쟁이 줄어드는 추세입니다."
      : "점포 수가 안정적으로 유지되고 있습니다.";

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Store className="h-5 w-5 text-purple-500" />
        <h3 className="text-sm font-bold text-slate-900">B3. {districtName} 경쟁 환경</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-purple-50 px-2 py-0.5 text-[9px] font-semibold text-purple-600">
          LOCALDATA + 카드매출
        </span>
      </div>

      {/* Interpretation */}
      <div className="mb-4 rounded-lg bg-purple-50/50 p-3">
        <p className="text-xs leading-relaxed text-purple-800">
          현재 {districtName}에는 {industryName} 점포 {storeCount}개가 영업 중입니다. {strategyText}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 text-center">
          <p className="text-[10px] text-slate-400">총 점포</p>
          <p className="text-lg font-extrabold text-slate-900">{storeCount}개</p>
        </div>
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 text-center">
          <p className="text-[10px] text-slate-400">순증감</p>
          <div className="flex items-center justify-center gap-1">
            {netGrowth > 0 ? (
              <ArrowUp className="h-3 w-3 text-emerald-500" />
            ) : netGrowth < 0 ? (
              <ArrowDown className="h-3 w-3 text-rose-500" />
            ) : (
              <Minus className="h-3 w-3 text-slate-400" />
            )}
            <p className={cn("text-lg font-extrabold", netGrowth > 0 ? "text-emerald-600" : netGrowth < 0 ? "text-rose-600" : "text-slate-700")}>
              {netGrowth > 0 ? "+" : ""}{netGrowth}
            </p>
          </div>
        </div>
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 text-center">
          <p className="text-[10px] text-slate-400">프랜차이즈</p>
          <p className="text-lg font-extrabold text-slate-900">{franchiseRatio}%</p>
        </div>
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 text-center">
          <p className="text-[10px] text-slate-400">신규/폐업</p>
          <p className="text-sm font-extrabold text-slate-900">
            <span className="text-emerald-600">+{newStores}</span>
            <span className="mx-1 text-slate-300">/</span>
            <span className="text-rose-600">-{closedStores}</span>
          </p>
        </div>
      </div>

      {/* LOCALDATA Competition Map */}
      <CompetitionMap data={localdataData} loading={localdataLoading || false} />

      <DataSource text="서울시 상권분석서비스 + 네이버 지도" />
    </div>
  );
}

// ─── Section B5: Customer Analysis ─────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomerSection({ data, loading, districtName, industryName }: { data: any; loading: boolean; districtName: string; industryName: string }) {
  if (loading) return <SectionSkeleton title="고객 분석" />;
  if (!data) return null;

  const breakdown = data.breakdown || {};
  const byAge = breakdown.by_age || {};
  const byTime = breakdown.by_time || {};
  const byGender = breakdown.by_gender || {};
  const byDay = breakdown.by_day || {};

  const ageLabels: Record<string, string> = {
    "10s": "10대", "20s": "20대", "30s": "30대", "40s": "40대", "50s": "50대", "60s_plus": "60+",
  };
  const timeLabels: Record<string, string> = {
    "00_06": "0~6시", "06_11": "6~11시", "11_14": "11~14시", "14_17": "14~17시", "17_21": "17~21시", "21_24": "21~24시",
  };
  const dayLabels: Record<string, string> = {
    mon: "월", tue: "화", wed: "수", thu: "목", fri: "금", sat: "토", sun: "일",
  };

  const peakTimeEntry = Object.entries(byTime).sort(([, a], [, b]) => (b as number) - (a as number))[0];
  const peakTimeLabel = peakTimeEntry ? timeLabels[peakTimeEntry[0]] || peakTimeEntry[0] : null;

  const peakDayEntry = Object.entries(byDay).sort(([, a], [, b]) => (b as number) - (a as number))[0];
  const peakDayLabel = peakDayEntry ? dayLabels[peakDayEntry[0]] || peakDayEntry[0] : null;

  const quarterCount = data.quarter_count || data.quarters?.length || 0;

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Users className="h-5 w-5 text-cyan-500" />
        <h3 className="text-sm font-bold text-slate-900">B5. {districtName} 고객 분석</h3>
        <span className="ml-auto flex items-center gap-1 rounded-full bg-cyan-50 px-2 py-0.5 text-[9px] font-semibold text-cyan-600">
          <CreditCard className="h-2.5 w-2.5" />
          {quarterCount > 0 ? `최근 ${quarterCount}분기` : "분기별 카드매출"}
        </span>
      </div>

      {/* Interpretation */}
      <div className="mb-4 rounded-lg bg-cyan-50/50 p-3">
        <p className="text-xs leading-relaxed text-cyan-800">
          {districtName} 상권에서 {industryName} 업종의 카드 결제 데이터를 분석한 결과입니다.
          {peakTimeLabel && ` 피크 시간대는 ${peakTimeLabel}입니다.`}
          {peakDayLabel && ` 가장 매출이 높은 요일은 ${peakDayLabel}요일입니다.`}
        </p>
      </div>

      {/* Gender */}
      <div className="mb-4">
        <p className="mb-2 text-xs font-semibold text-slate-500">성별</p>
        <div className="flex h-4 overflow-hidden rounded-full">
          <div className="bg-blue-400" style={{ width: `${byGender.male_pct || 50}%` }} />
          <div className="bg-pink-400" style={{ width: `${byGender.female_pct || 50}%` }} />
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-slate-500">
          <span>남성 {byGender.male_pct || 50}%</span>
          <span>여성 {byGender.female_pct || 50}%</span>
        </div>
      </div>

      {/* Age distribution */}
      <div className="mb-4">
        <p className="mb-2 text-xs font-semibold text-slate-500">연령대별 매출 비중</p>
        <div className="flex items-end gap-1">
          {Object.entries(ageLabels).map(([key, label]) => {
            const pct = byAge[key] || 0;
            return (
              <div key={key} className="flex-1 text-center">
                <div className="mx-auto w-full overflow-hidden rounded-t bg-slate-100" style={{ height: "60px" }}>
                  <div
                    className="w-full rounded-t bg-gradient-to-t from-cyan-500 to-cyan-400 transition-all duration-500"
                    style={{ height: `${pct}%`, marginTop: `${100 - pct}%` }}
                  />
                </div>
                <p className="mt-1 text-[9px] font-medium text-slate-500">{label}</p>
                <p className="text-[10px] font-bold text-slate-700">{pct}%</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Time distribution */}
      <div className="mb-4">
        <p className="mb-2 text-xs font-semibold text-slate-500">시간대별 매출 비중</p>
        <div className="flex items-end gap-1">
          {Object.entries(timeLabels).map(([key, label]) => {
            const pct = byTime[key] || 0;
            return (
              <div key={key} className="flex-1 text-center">
                <div className="mx-auto w-full overflow-hidden rounded-t bg-slate-100" style={{ height: "60px" }}>
                  <div
                    className="w-full rounded-t bg-gradient-to-t from-indigo-500 to-indigo-400 transition-all duration-500"
                    style={{ height: `${pct}%`, marginTop: `${100 - pct}%` }}
                  />
                </div>
                <p className="mt-1 text-[8px] font-medium text-slate-500">{label}</p>
                <p className="text-[10px] font-bold text-slate-700">{pct}%</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Day distribution */}
      {Object.keys(byDay).length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold text-slate-500">요일별 매출 비중</p>
          <div className="flex items-end gap-1">
            {Object.entries(dayLabels).map(([key, label]) => {
              const pct = byDay[key] || 0;
              return (
                <div key={key} className="flex-1 text-center">
                  <div className="mx-auto w-full overflow-hidden rounded-t bg-slate-100" style={{ height: "50px" }}>
                    <div
                      className="w-full rounded-t bg-gradient-to-t from-violet-500 to-violet-400 transition-all duration-500"
                      style={{ height: `${pct}%`, marginTop: `${100 - pct}%` }}
                    />
                  </div>
                  <p className="mt-1 text-[9px] font-medium text-slate-500">{label}</p>
                  <p className="text-[10px] font-bold text-slate-700">{pct}%</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <DataSource text="서울시 카드매출 데이터" />
    </div>
  );
}

// ─── Section B7: Franchise Comparison ──────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function FranchiseSection({ data, loading, industryName }: { data: any; loading: boolean; industryName: string }) {
  if (loading) return <SectionSkeleton title="프랜차이즈 현황" />;
  if (!data) return null;

  const brands = data.brands || data.top_brands || [];
  const startupCosts = data.startup_costs || [];
  const industryStatus = data.industry_status || [];
  const hasData = brands.length > 0 || startupCosts.length > 0;

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Building2 className="h-5 w-5 text-orange-500" />
        <h3 className="text-sm font-bold text-slate-900">B7. {industryName} 프랜차이즈 현황</h3>
      </div>

      {hasData ? (
        <div className="space-y-2">
          <div className="rounded-lg bg-orange-50/50 p-2">
            <p className="text-[10px] leading-relaxed text-orange-700">
              아래 금액은 공정거래위원회 정보공개서 기준 <strong>가맹 가입비</strong>만 포함합니다.
              실제 총 창업비용은 인테리어·보증금·장비비 등이 추가되어 훨씬 높습니다.
              (비용비교 페이지에서 총 비용을 확인하세요)
            </p>
          </div>
          {startupCosts.length > 0 && startupCosts.map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (item: any) => {
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const status = industryStatus.find((s: any) => s.name === item.name);
              return (
                <div key={`${item.name}-${item.franchise_fee}-${item.education_fee}-${item.other_fee}`} className="rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-slate-900">{item.name}</p>
                    <span className="text-xs font-bold text-slate-700">
                      가맹 가입비 {formatWon(item.total_joining_cost || 0)}
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-3 text-[10px] text-slate-500">
                    <span>가맹비 {formatWon(item.franchise_fee || 0)}</span>
                    <span>교육비 {formatWon(item.education_fee || 0)}</span>
                    <span>기타 {formatWon(item.other_fee || 0)}</span>
                  </div>
                  {status && (
                    <div className="mt-1 flex flex-wrap gap-x-3 text-[10px] text-slate-500">
                      <span>브랜드 {status.brand_count}개</span>
                      <span>가맹점 {(status.store_count || 0).toLocaleString()}개</span>
                      <span>폐점 {(status.closed_store_count || 0).toLocaleString()}개</span>
                    </div>
                  )}
                </div>
              );
            },
          )}
          {brands.length > 0 && brands.slice(0, 5).map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (brand: any) => (
              <div key={`${brand.brand_name || brand.name}-${brand.franchise_fee || brand.initial_cost || 0}`} className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-2">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{brand.brand_name || brand.name}</p>
                  <p className="text-[10px] text-slate-500">
                    가맹비 {formatWon(brand.franchise_fee || brand.initial_cost || 0)}
                    {brand.store_count ? ` / ${brand.store_count}개 매장` : ""}
                  </p>
                </div>
                {brand.avg_monthly_sales && (
                  <span className="text-xs font-bold text-slate-700">
                    월매출 {formatWon(brand.avg_monthly_sales)}
                  </span>
                )}
              </div>
            ),
          )}
          {data.avg_total_startup_cost && (
            <div className="mt-2 rounded-lg bg-orange-50 p-2 text-center">
              <p className="text-[10px] text-orange-500">업종 평균 가맹 가입비</p>
              <p className="text-sm font-extrabold text-orange-700">{formatWon(data.avg_total_startup_cost)}</p>
              <p className="text-[9px] text-orange-400">가맹비+교육비+기타 합산 (인테리어·보증금·장비 별도)</p>
            </div>
          )}
        </div>
      ) : (
        <div className="rounded-lg bg-orange-50/50 p-4 text-center">
          <p className="text-sm text-slate-500">이 업종의 프랜차이즈 데이터가 아직 없습니다.</p>
          <p className="mt-1 text-xs text-slate-400">독립창업 기준으로 비용을 산정합니다.</p>
        </div>
      )}

      <DataSource text={`공정거래위원회 가맹사업 정보 (${data.year || "2024"})`} />
    </div>
  );
}

// ─── Section C: Inline Simulator ───────────────────────────────────────
function InlineSimulatorSection({
  defaults,
  loading,
  districtName,
}: {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  defaults: any;
  loading: boolean;
  districtName: string;
}) {
  const [salesMultiplier, setSalesMultiplier] = useState(1.0);
  const [rentMultiplier, setRentMultiplier] = useState(1.0);
  const [laborMultiplier, setLaborMultiplier] = useState(1.0);

  if (loading) return <SectionSkeleton title="수익 시뮬레이터" />;
  if (!defaults) return null;

  const baseSales = defaults.revenue?.monthly_sales_per_store || 0;
  const baseRent = defaults.operating_cost?.rent || 0;
  const baseLabor = defaults.operating_cost?.labor || 0;
  const baseCogs = defaults.operating_cost?.cogs || 0;
  const baseOther = (defaults.operating_cost?.utilities || 0) + (defaults.operating_cost?.other || 0);

  const adjustedSales = Math.round(baseSales * salesMultiplier);
  const adjustedRent = Math.round(baseRent * rentMultiplier);
  const adjustedLabor = Math.round(baseLabor * laborMultiplier);
  const totalCost = baseCogs + adjustedRent + adjustedLabor + baseOther;
  const adjustedProfit = adjustedSales - totalCost;

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <SlidersHorizontal className="h-5 w-5 text-indigo-500" />
        <h3 className="text-sm font-bold text-slate-900">C. {districtName} 수익 시뮬레이터</h3>
      </div>

      <div className="mb-4 rounded-lg bg-indigo-50/50 p-3">
        <p className="text-xs leading-relaxed text-indigo-800">
          임대료, 인건비, 매출을 조정하면 예상 월 수익이 실시간으로 바뀝니다. 슬라이더를 움직여 다양한 시나리오를 확인해보세요.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label htmlFor="sim-sales" className="mb-1 flex items-center justify-between text-xs text-slate-500">
            <span>매출 조정</span>
            <span className="font-bold text-slate-700">{(salesMultiplier * 100).toFixed(0)}% ({formatWon(adjustedSales)})</span>
          </label>
          <input id="sim-sales" type="range" min={0.5} max={1.5} step={0.05} value={salesMultiplier} onChange={(e) => setSalesMultiplier(parseFloat(e.target.value))} className="w-full accent-indigo-600" />
          <div className="flex justify-between text-[10px] text-slate-400"><span>-50%</span><span>기본</span><span>+50%</span></div>
        </div>
        <div>
          <label htmlFor="sim-rent" className="mb-1 flex items-center justify-between text-xs text-slate-500">
            <span>월 임대료 <span className="text-[10px] text-slate-400">(예상 월세, 보증금 별도)</span></span>
            <span className="font-bold text-slate-700">{formatWon(adjustedRent)}</span>
          </label>
          <input id="sim-rent" type="range" min={0.5} max={2.0} step={0.1} value={rentMultiplier} onChange={(e) => setRentMultiplier(parseFloat(e.target.value))} className="w-full accent-rose-500" />
          <div className="flex justify-between text-[10px] text-slate-400"><span>-50%</span><span>기본</span><span>+100%</span></div>
        </div>
        <div>
          <label htmlFor="sim-labor" className="mb-1 flex items-center justify-between text-xs text-slate-500">
            <span>인건비 <span className="text-[10px] text-slate-400">(직원 급여 + 4대보험)</span></span>
            <span className="font-bold text-slate-700">{formatWon(adjustedLabor)}</span>
          </label>
          <input id="sim-labor" type="range" min={0.5} max={2.0} step={0.1} value={laborMultiplier} onChange={(e) => setLaborMultiplier(parseFloat(e.target.value))} className="w-full accent-amber-500" />
          <div className="flex justify-between text-[10px] text-slate-400"><span>-50%</span><span>기본</span><span>+100%</span></div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 sm:gap-3">
        <div className="rounded-xl bg-blue-50 p-2 text-center sm:p-3">
          <p className="text-[10px] text-blue-500">조정 매출</p>
          <p className="text-xs font-extrabold text-blue-700 sm:text-sm">{formatWon(adjustedSales)}</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-2 text-center sm:p-3">
          <p className="text-[10px] text-slate-500">총 비용</p>
          <p className="text-xs font-extrabold text-slate-700 sm:text-sm">{formatWon(totalCost)}</p>
        </div>
        <div className={cn("rounded-xl p-2 text-center sm:p-3", adjustedProfit >= 0 ? "bg-emerald-50" : "bg-rose-50")}>
          <p className={cn("text-[10px]", adjustedProfit >= 0 ? "text-emerald-500" : "text-rose-500")}>순이익</p>
          <p className={cn("text-xs font-extrabold sm:text-sm", adjustedProfit >= 0 ? "text-emerald-700" : "text-rose-700")}>
            {adjustedProfit < 0 ? "-" : ""}{formatWon(Math.abs(adjustedProfit))}
          </p>
        </div>
      </div>

      <p className="mt-4 text-[10px] text-slate-400">
        순이익 = 매출 - 임대료 - 인건비 - 재료비(매출의 약 35%)
      </p>
    </div>
  );
}

// ─── Section D: Risk & Opportunity ─────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function RiskSection({ data, loading, districtName }: { data: any; loading: boolean; districtName: string }) {
  const [riskExpanded, setRiskExpanded] = useState(false);
  const [oppExpanded, setOppExpanded] = useState(false);

  if (loading) return <SectionSkeleton title="리스크 & 기회" />;
  if (!data) return null;

  const sections = data.sections || data.analysis?.sections || [];
  const riskContent = data.risk_comment || data.competition_comment || "";
  const oppContent = data.verdict_summary || data.profitability_comment || "";
  const customerNote = data.customer_comment || "";

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const riskSection = sections.find((s: any) =>
    s.title?.includes("리스크") || s.title?.includes("위험") || s.title?.includes("약점") || s.title?.includes("threat") || s.title?.includes("risk")
  );
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const oppSection = sections.find((s: any) =>
    s.title?.includes("기회") || s.title?.includes("강점") || s.title?.includes("장점") || s.title?.includes("opportunity") || s.title?.includes("strength")
  );

  const displayRiskText = riskSection?.content || riskContent;
  const displayOppText = oppSection?.content || oppContent;
  const hasContent = displayRiskText || displayOppText || customerNote;

  const COLLAPSE_THRESHOLD = 500;

  const renderCollapsibleText = (text: string, expanded: boolean, setExpanded: (v: boolean) => void, colorClass: string) => {
    const needsCollapse = text.length > COLLAPSE_THRESHOLD;
    const displayText = !needsCollapse || expanded ? text : text;
    return (
      <div>
        <p className={cn("text-xs leading-relaxed", colorClass)}>{displayText}</p>
        {needsCollapse && (
          <button type="button" onClick={() => setExpanded(!expanded)} className="mt-1 flex items-center gap-0.5 text-[10px] font-semibold text-slate-500 hover:text-slate-700">
            {expanded ? "접기" : "더 보기"}
            <ChevronDown className={cn("h-3 w-3 transition-transform", expanded && "rotate-180")} />
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <AlertTriangle className="h-5 w-5 text-amber-500" />
        <h3 className="text-sm font-bold text-slate-900">D. {districtName} 리스크 & 기회 분석</h3>
      </div>

      <div className="mb-4 rounded-lg bg-amber-50/50 p-3">
        <p className="text-xs leading-relaxed text-amber-800">
          AI가 {districtName} 상권의 잠재적 위험 요소와 기회 요인을 분석했습니다.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-rose-100 bg-rose-50/30 p-4">
          <p className="mb-2 text-xs font-bold text-rose-700">{riskSection?.title || "주요 리스크"}</p>
          {displayRiskText ? (
            renderCollapsibleText(displayRiskText, riskExpanded, setRiskExpanded, "text-rose-900/80")
          ) : (
            <p className="text-xs text-rose-500">해당 상권의 특이 리스크 분석 중입니다</p>
          )}
        </div>
        <div className="rounded-xl border border-emerald-100 bg-emerald-50/30 p-4">
          <p className="mb-2 text-xs font-bold text-emerald-700">{oppSection?.title || "주요 기회"}</p>
          {displayOppText ? (
            renderCollapsibleText(displayOppText, oppExpanded, setOppExpanded, "text-emerald-900/80")
          ) : (
            <p className="text-xs text-emerald-500">기회 요인을 탐색 중입니다</p>
          )}
        </div>
      </div>

      {customerNote && (
        <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50/30 p-3">
          <p className="mb-1 text-xs font-bold text-blue-700">고객 분석 인사이트</p>
          <p className="text-xs leading-relaxed text-blue-900/80">{customerNote}</p>
        </div>
      )}

      {hasContent && <DataSource text="AI 종합 분석" />}
    </div>
  );
}

// ─── Section E: Support Programs ───────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function SupportSection({ data, loading, industryName }: { data: any; loading: boolean; industryName: string }) {
  if (loading) return <SectionSkeleton title="지원금 매칭" />;
  if (!data) return null;

  const programs = data.programs || data.matched_programs || [];

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Gift className="h-5 w-5 text-green-500" />
        <h3 className="text-sm font-bold text-slate-900">E. {industryName} 창업 지원금</h3>
        {programs.length > 0 && (
          <span className="rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-bold text-green-700">
            {programs.length}건
          </span>
        )}
      </div>

      <div className="mb-4 rounded-lg bg-green-50/50 p-3">
        <p className="text-xs leading-relaxed text-green-800">
          현재 신청 가능한 정부·지자체 창업 지원 프로그램입니다. 대부분의 지원금은 사업계획서 제출이 필수입니다.
        </p>
      </div>

      {programs.length > 0 ? (
        <div className="space-y-2">
          {programs.slice(0, 3).map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (prog: any) => (
              <div key={`${prog.program_id || prog.program_name || prog.name}-${prog.application_end_date || prog.deadline || ""}`} className="rounded-lg border border-slate-100 bg-slate-50/50 p-3">
                <p className="text-xs font-semibold text-slate-900">{prog.program_name || prog.name}</p>
                <p className="mt-0.5 text-[10px] text-slate-500">{prog.managing_org || prog.organization || ""}</p>
                {prog.max_amount_man > 0 && (
                  <p className="mt-1 text-xs font-bold text-green-700">
                    최대 {prog.max_amount_man >= 10000 ? `${(prog.max_amount_man / 10000).toFixed(1)}억원` : `${prog.max_amount_man.toLocaleString()}만원`}
                  </p>
                )}
                {prog.support_amount && !prog.max_amount_man && (
                  <p className="mt-1 text-xs font-bold text-green-700">{prog.support_amount}</p>
                )}
                {(prog.deadline || prog.application_end_date) && (
                  <p className="mt-1 text-[10px] font-semibold text-rose-600">
                    신청 마감: {prog.deadline || prog.application_end_date}
                  </p>
                )}
              </div>
            ),
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-500">매칭 가능한 지원 프로그램이 없습니다</p>
      )}

      <Link href="/analyze" className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700">
        전체 지원금 보기 <ChevronRight className="h-3 w-3" />
      </Link>

      <DataSource text="중소벤처기업부 비즈인포" />
    </div>
  );
}

// ─── Accordion Item ─────────────────────────────────────────────────────
function AccordionItem({
  id,
  icon,
  title,
  isOpen,
  onToggle,
  loading,
  children,
}: {
  id: string;
  icon: React.ReactNode;
  title: string;
  isOpen: boolean;
  onToggle: () => void;
  loading: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white transition-shadow hover:shadow-sm">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-slate-50/50"
      >
        <span className="shrink-0">{icon}</span>
        <span className="flex-1 text-sm font-bold text-slate-900">{title}</span>
        {loading && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-slate-400 transition-transform duration-300",
            isOpen && "rotate-180",
          )}
        />
      </button>
      {isOpen && (
        <div id={`section-${id}`} className="animate-slide-up border-t border-slate-100 px-1 py-1">
          {children}
        </div>
      )}
    </div>
  );
}

// ─── Section Group (3 grouped categories) ──────────────────────────────
function SectionGroup({
  id,
  emoji,
  title,
  subtitle,
  isOpen,
  onToggle,
  children,
}: {
  id: string;
  emoji: string;
  title: string;
  subtitle: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div id={`group-${id}`} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors hover:bg-slate-50/80"
      >
        <span className="text-xl">{emoji}</span>
        <div className="flex-1">
          <span className="text-sm font-bold text-slate-900">{title}</span>
          <p className="text-[11px] text-slate-400">{subtitle}</p>
        </div>
        <ChevronDown
          className={cn(
            "h-5 w-5 shrink-0 text-slate-400 transition-transform duration-300",
            isOpen && "rotate-180",
          )}
        />
      </button>
      {isOpen && (
        <div className="space-y-3 border-t border-slate-100 px-2 py-3 sm:px-3">
          {children}
        </div>
      )}
    </div>
  );
}

// ─── Main Report Page ──────────────────────────────────────────────────
function ReportContent() {
  const searchParams = useSearchParams();
  const store = useAnalyzeStore();

  const industryCode = searchParams?.get("industry_code") || store.industryCode;
  const budget = Number(searchParams?.get("budget")) || Number(searchParams?.get("budget_max")) || store.budget;
  const experienceLevel = searchParams?.get("experience_level") || store.experienceLevel;
  const employeeCount = searchParams?.get("employee_count") || store.employeeCount;

  useEffect(() => {
    const s = useAnalyzeStore.getState();
    s.setStep(2);
    if (industryCode && industryCode !== s.industryCode) {
      s.setIndustry(industryCode);
    }
    if (experienceLevel && experienceLevel !== s.experienceLevel) {
      s.setExperienceLevel(experienceLevel);
    }
    if (employeeCount && employeeCount !== s.employeeCount) {
      s.setEmployeeCount(employeeCount);
    }
  }, [industryCode, experienceLevel, employeeCount]);

  const industryName = store.industryName;

  const preferredDistricts = searchParams?.get("preferred_districts") || "";

  const [top3Loading, setTop3Loading] = useState(true);
  const [topDistricts, setTopDistricts] = useState<TopDistrict[]>([]);
  const [selectedCode, setSelectedCode] = useState("");

  // Verdict state
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [verdictData, setVerdictData] = useState<any>(null);
  const [verdictLoading, setVerdictLoading] = useState(false);

  // Section data states
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [scorecardData, setScorecardData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [simulationData, setSimulationData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [competitionData, setCompetitionData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [customerData, setCustomerData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [franchiseData, setFranchiseData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [riskData, setRiskData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [supportData, setSupportData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [locationData, setLocationData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [rentData, setRentData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars
  const [localdataData, setLocaldataData] = useState<any>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [salesTrendData, setSalesTrendData] = useState<any>(null);

  // Section loading states
  const [scorecardLoading, setScorecardLoading] = useState(false);
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [competitionLoading, setCompetitionLoading] = useState(false);
  const [customerLoading, setCustomerLoading] = useState(false);
  const [franchiseLoading, setFranchiseLoading] = useState(false);
  const [riskLoading, setRiskLoading] = useState(false);
  const [supportLoading, setSupportLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);
  const [rentLoading, setRentLoading] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [localdataLoading, setLocaldataLoading] = useState(false);
  const [salesTrendLoading, setSalesTrendLoading] = useState(false);
  const [sectionErrors, setSectionErrors] = useState<Record<string, string>>({});

  const setSectionError = useCallback((key: string, msg: string | null) => {
    setSectionErrors((prev) => {
      const next = { ...prev };
      if (msg) {
        next[key] = msg;
      } else {
        delete next[key];
      }
      return next;
    });
  }, []);

  const [similarityScores, setSimilarityScores] = useState<Record<string, number>>({});

  useEffect(() => {
    const bm = store.benchmarkStore;
    if (!bm?.x || !bm?.y || topDistricts.length === 0) return;

    topDistricts.forEach((dist) => {
      fetchWithTimeout(`${API_BASE}/benchmark/similarity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          benchmark_name: bm.name,
          benchmark_x: bm.x,
          benchmark_y: bm.y,
          benchmark_category: bm.category,
          district_code: dist.district_code,
          district_name: dist.district_name,
          industry_code: industryCode,
        }),
      })
        .then((r) => r.json())
        .then((data: { similarity_score: number }) => {
          setSimilarityScores((prev) => ({
            ...prev,
            [dist.district_code]: data.similarity_score,
          }));
        })
        .catch(() => {});
    });
  }, [topDistricts, store.benchmarkStore, industryCode]);

  const benchmarkMapMarker = store.benchmarkStore?.x && store.benchmarkStore?.y
    ? { lat: store.benchmarkStore.y, lng: store.benchmarkStore.x, label: store.benchmarkStore.name }
    : null;
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set(["core"]));
  const toggleGroup = (id: string) => {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Per-section accordion within groups
  const [openSections, setOpenSections] = useState<Set<string>>(new Set(["revenue", "scorecard", "competition"]));
  const toggleSection = (id: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Phase 1: Fetch TOP 3
  useEffect(() => {
    const fetchTop3 = async () => {
      setTop3Loading(true);
      try {
        const params = new URLSearchParams({
          industry_code: industryCode,
          budget_min: String(budget),
          budget_max: String(budget),
          limit: "3",
        });
        if (preferredDistricts && preferredDistricts !== "상관없어요") {
          const areaFilter = preferredDistricts.split("/")[0];
          params.set("district_filter", areaFilter);
        }
        if (experienceLevel) params.set("experience_level", experienceLevel);
        if (employeeCount) params.set("employee_count", employeeCount);
        const res = await fetchWithTimeout(`${API_BASE}/recommendations/dashboard?${params}`);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        const results = (data.results || []).map(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (r: any) => ({
            district_code: r.district_code,
            district_name: r.district_name,
            district_type: r.district_type,
            success_probability: r.success_probability,
            estimated_rent: r.estimated_rent,
            monthly_sales: r.monthly_sales,
            store_count: r.store_count,
            survival_rate: r.survival_rate,
            scorecard_total: r.scorecard_total,
            key_factors: r.key_factors || [],
            coordinates: typeof r.lat === "number" && typeof r.lng === "number" && !(r.lat === 0 && r.lng === 0)
              ? { lat: r.lat, lng: r.lng }
              : undefined,
          }),
        );
        setTopDistricts(results);
        useAnalyzeStore.getState().setTopDistricts(results);
        if (results.length > 0) {
          setSelectedCode(results[0].district_code);
          useAnalyzeStore.getState().setSelectedDistrict(results[0].district_code);
          track("report_view", { district_code: results[0].district_code, industry_code: industryCode });
        }
      } catch (err) {
        console.error("Failed to fetch TOP 3:", err);
      } finally {
        setTop3Loading(false);
      }
    };
    fetchTop3();
  }, [industryCode, budget, preferredDistricts, experienceLevel, employeeCount]);

  // Phase 1.5: Fetch REAL verdict from backend
  useEffect(() => {
    if (!selectedCode) return;
    const fetchVerdict = async () => {
      setVerdictLoading(true);
      try {
        const selectedDist = topDistricts.find(d => d.district_code === selectedCode);
        const params = new URLSearchParams();
        if (budget > 0) params.set("budget_max", String(budget));
        if (experienceLevel) params.set("experience_level", experienceLevel);
        if (selectedDist?.estimated_rent) params.set("estimated_rent", String(selectedDist.estimated_rent));
        const res = await fetchWithTimeout(`${API_BASE}/verdict/${industryCode}/${selectedCode}?${params}`);
        if (res.ok) {
          const data = await res.json();
          setVerdictData(data);
        }
      } catch (err) {
        console.error("Verdict fetch failed:", err);
      } finally {
        setVerdictLoading(false);
      }
    };
    fetchVerdict();
  }, [selectedCode, industryCode, budget, experienceLevel, topDistricts]);

  // Phase 2: Fetch section data when district changes
  const fetchSectionData = useCallback(
    async (districtCode: string) => {
      if (!districtCode) return;

      const state = useAnalyzeStore.getState();
      const cached = state.sectionData[districtCode];
      const selectedDist = state.topDistricts.find((d) => d.district_code === districtCode);
      const distName = selectedDist?.district_name || "";

      // B1: Scorecard
      if (!cached?.scorecard) {
        setSectionError("scorecard", null);
        setScorecardData(null);
        setScorecardLoading(true);
        fetchWithTimeout(`${API_BASE}/scorecard/${industryCode}/${districtCode}`)
          .then((r) => r.json())
          .then((data) => {
            setScorecardData({ ...data, district_code: districtCode, industry_code: industryCode });
            useAnalyzeStore.getState().setSectionData(districtCode, "scorecard", data);
          })
          .catch((err) => {
            console.error("API error:", err);
            setSectionError("scorecard", "데이터를 불러오지 못했습니다");
          })
          .finally(() => setScorecardLoading(false));
      } else {
        setSectionError("scorecard", null);
        setScorecardData({ ...cached.scorecard, district_code: districtCode, industry_code: industryCode });
      }

      // B2: Simulation
      if (!cached?.simulation) {
        setSectionError("simulation", null);
        setSimulationData(null);
        setSimulationLoading(true);
        fetchWithTimeout(`${API_BASE}/simulation/simulate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            district_code: districtCode,
            industry_code: industryCode,
            area_pyeong: 15,
            interior_grade: "mid",
          }),
        })
          .then((r) => r.json())
          .then((data) => {
            setSimulationData({ ...data, district_code: districtCode, industry_code: industryCode });
            useAnalyzeStore.getState().setSectionData(districtCode, "simulation", data);
          })
          .catch((err) => {
            console.error("API error:", err);
            setSectionError("simulation", "데이터를 불러오지 못했습니다");
          })
          .finally(() => setSimulationLoading(false));
      } else {
        setSectionError("simulation", null);
        setSimulationData({ ...cached.simulation, district_code: districtCode, industry_code: industryCode });
      }

      // B3: Competition
      if (!cached?.competition) {
        setSectionError("competition", null);
        setCompetitionData(null);
        setCompetitionLoading(true);
        fetchWithTimeout(`${API_BASE}/explore/stores?district_code=${districtCode}&industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            const storesInfo = {
              stores: data,
              store_count: data.store_count || data.total || 0,
              new_stores: 0,
              closed_stores: 0,
              franchise_stores: 0,
            };
            const query = encodeURIComponent(`${distName} ${industryName}`);
            return fetchWithTimeout(`${API_BASE}/competitive/analyze?district_code=${districtCode}&industry_code=${industryCode}&query=${query}`)
              .then((r2) => r2.json())
              .then((comp) => {
                const merged = { stores: { ...storesInfo, ...comp } };
                setCompetitionData(merged);
                useAnalyzeStore.getState().setSectionData(districtCode, "competition", merged);
              })
              .catch(() => {
                setCompetitionData({ stores: storesInfo });
                useAnalyzeStore.getState().setSectionData(districtCode, "competition", { stores: storesInfo });
              });
          })
          .catch((err) => {
            console.error("API error:", err);
            setSectionError("competition", "데이터를 불러오지 못했습니다");
          })
          .finally(() => setCompetitionLoading(false));
      } else {
        setSectionError("competition", null);
        setCompetitionData(cached.competition);
      }

      // B5: Customer
      if (!cached?.customer) {
        setSectionError("customer", null);
        setCustomerData(null);
        setCustomerLoading(true);
        fetchWithTimeout(`${API_BASE}/explore/sales-breakdown?district_code=${districtCode}&industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            setCustomerData(data);
            useAnalyzeStore.getState().setSectionData(districtCode, "customer", data);
          })
          .catch((err) => {
            console.error("API error:", err);
            setSectionError("customer", "데이터를 불러오지 못했습니다");
          })
          .finally(() => setCustomerLoading(false));
      } else {
        setSectionError("customer", null);
        setCustomerData(cached.customer);
      }

      // B7: Franchise
      if (!cached?.franchise) {
        setSectionError("franchise", null);
        setFranchiseData(null);
        setFranchiseLoading(true);
        fetchWithTimeout(`${API_BASE}/franchise/benchmark/${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            setFranchiseData(data);
            useAnalyzeStore.getState().setSectionData(districtCode, "franchise", data);
          })
          .catch((err) => {
            console.error("API error:", err);
            setSectionError("franchise", "데이터를 불러오지 못했습니다");
          })
          .finally(() => setFranchiseLoading(false));
      } else {
        setSectionError("franchise", null);
        setFranchiseData(cached.franchise);
      }

      // D: Risk
      if (!cached?.risk) {
        setSectionError("risk", null);
        setRiskData(null);
        setRiskLoading(true);
        fetchWithTimeout(`${API_BASE}/districts/${districtCode}/analysis?industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            setRiskData(data);
            useAnalyzeStore.getState().setSectionData(districtCode, "risk", data);
          })
          .catch((err) => {
            console.error("API error:", err);
            setSectionError("risk", "데이터를 불러오지 못했습니다");
          })
          .finally(() => setRiskLoading(false));
      } else {
        setSectionError("risk", null);
        setRiskData(cached.risk);
      }

      // E: Support
      if (!cached?.support) {
        setSectionError("support", null);
        setSupportData(null);
        setSupportLoading(true);
        const districtParam = distName ? `&district=${encodeURIComponent(distName)}` : "";
        const budgetParam = budget > 0 ? `&budget_max=${Math.round(budget * 10000)}` : "";
        fetchWithTimeout(`${API_BASE}/support/programs?industry_code=${industryCode}${districtParam}${budgetParam}`)
          .then((r) => r.json())
          .then((data) => {
            setSupportData(data);
            useAnalyzeStore.getState().setSectionData(districtCode, "support", data);
          })
          .catch((err) => {
            console.error("API error:", err);
            setSectionError("support", "데이터를 불러오지 못했습니다");
          })
          .finally(() => setSupportLoading(false));
      } else {
        setSectionError("support", null);
        setSupportData(cached.support);
      }

      // B4: Location Profile
      if (!cached?.location) {
        setSectionError("location", null);
        setLocationData(null);
        setLocationLoading(true);
        fetchWithTimeout(`${API_BASE}/location/profile?district_code=${districtCode}&industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            setLocationData(data);
            useAnalyzeStore.getState().setSectionData(districtCode, "location", data);
          })
          .catch((err) => {
            console.error("API error:", err);
            setSectionError("location", "데이터를 불러오지 못했습니다");
          })
          .finally(() => setLocationLoading(false));
      } else {
        setSectionError("location", null);
        setLocationData(cached.location);
      }

      // B6: Rent Trend
      if (!cached?.rent) {
        setSectionError("rent", null);
        setRentData(null);
        setRentLoading(true);
        fetchWithTimeout(`${API_BASE}/kosis/rent-trend?district_code=${districtCode}`)
          .then((r) => r.json())
          .then((data) => {
            setRentData(data);
            useAnalyzeStore.getState().setSectionData(districtCode, "rent", data);
          })
          .catch((err) => {
            console.error("API error:", err);
            setSectionError("rent", "데이터를 불러오지 못했습니다");
          })
          .finally(() => setRentLoading(false));
      } else {
        setSectionError("rent", null);
        setRentData(cached.rent);
      }

      // Sales Trend
      if (!cached?.salesTrend) {
        setSectionError("salesTrend", null);
        setSalesTrendData(null);
        setSalesTrendLoading(true);
        fetchWithTimeout(`${API_BASE}/explore/sales-trend?district_code=${districtCode}&industry_code=${industryCode}`)
          .then((r) => r.json())
          .then((data) => {
            setSalesTrendData(data);
            useAnalyzeStore.getState().setSectionData(districtCode, "salesTrend", data);
          })
          .catch((err) => {
            console.error("API error:", err);
            setSectionError("salesTrend", "데이터를 불러오지 못했습니다");
          })
          .finally(() => setSalesTrendLoading(false));
      } else {
        setSectionError("salesTrend", null);
        setSalesTrendData(cached.salesTrend);
      }

      // LOCALDATA competition
      if (!cached?.localdata) {
        setLocaldataLoading(true);
        const district = useAnalyzeStore.getState().topDistricts.find((d) => d.district_code === districtCode);
        if (district?.coordinates) {
          fetchWithTimeout(`${API_BASE}/explore/stores?district_code=${districtCode}&industry_code=${industryCode}`)
            .then((r) => r.json())
            .then((data) => {
              setLocaldataData(data);
              useAnalyzeStore.getState().setSectionData(districtCode, "localdata", data);
            })
            .catch((err) => { console.error("API error:", err); })
            .finally(() => setLocaldataLoading(false));
        } else {
          setLocaldataLoading(false);
        }
      } else {
        setLocaldataData(cached.localdata);
      }
    },
    [industryCode, industryName, budget, setSectionError],
  );

  useEffect(() => {
    if (selectedCode) {
      fetchSectionData(selectedCode);
    }
  }, [selectedCode, fetchSectionData]);

  const handleDistrictSelect = (code: string) => {
    setSelectedCode(code);
    useAnalyzeStore.getState().setSelectedDistrict(code);
  };

  const selectedDistrict = topDistricts.find((d) => d.district_code === selectedCode);
  const districtName = selectedDistrict?.district_name || "";

  const verdict: "GO" | "CAUTION" | "NO_GO" | null = verdictData?.verdict || null;
  const isNoGo = verdict === "NO_GO";
  const [showDetailAnyway, setShowDetailAnyway] = useState(false);

  // Verdict-driven section visibility
  useEffect(() => {
    if (!verdict) return;
    if (verdict === "NO_GO") {
      setOpenGroups(new Set());
      setOpenSections(new Set());
    } else if (verdict === "CAUTION") {
      setOpenGroups(new Set(["core"]));
      setOpenSections(new Set(["scorecard", "revenue", "competition"]));
    } else {
      setOpenGroups(new Set(["core"]));
      setOpenSections(new Set(["scorecard", "revenue", "competition"]));
    }
  }, [verdict]);

  // Build CTA query params
  const ctaParams = new URLSearchParams({
    industry_code: industryCode,
    district_code: selectedCode,
    budget: String(budget),
  });
  if (experienceLevel) ctaParams.set("experience_level", experienceLevel);
  if (employeeCount) ctaParams.set("employee_count", employeeCount);

  const coreSections = [
    {
      id: "scorecard",
      icon: <Target className="h-4 w-4 text-blue-500" />,
      title: "성공 점수",
      loading: scorecardLoading,
      content: (
        sectionErrors.scorecard && !scorecardData
          ? <ErrorCard message={sectionErrors.scorecard} />
          : (
            <ProGateSection feature="detailed_scorecard">
              <ScorecardSection data={scorecardData} loading={scorecardLoading} districtName={districtName} industryName={industryName} />
            </ProGateSection>
          )
      ),
    },
    {
      id: "revenue",
      icon: <TrendingUp className="h-4 w-4 text-emerald-500" />,
      title: "수익 구조",
      loading: simulationLoading,
      content: (
        sectionErrors.simulation && !simulationData
          ? <ErrorCard message={sectionErrors.simulation} />
          : (
            <ProGateSection feature="revenue_waterfall">
              <RevenueSection data={simulationData} loading={simulationLoading} districtName={districtName} industryName={industryName} />
            </ProGateSection>
          )
      ),
    },
    {
      id: "competition",
      icon: <Store className="h-4 w-4 text-purple-500" />,
      title: "경쟁 환경",
      loading: competitionLoading,
      content: (
        sectionErrors.competition && !competitionData
          ? <ErrorCard message={sectionErrors.competition} />
          : (
            <ProGateSection feature="competition_map">
              <CompetitionSection data={competitionData} loading={competitionLoading} localdataData={localdataData} localdataLoading={localdataLoading} districtName={districtName} industryName={industryName} />
            </ProGateSection>
          )
      ),
    },
  ];

  const detailSections = [
    {
      id: "location",
      icon: <MapPin className="h-4 w-4 text-indigo-500" />,
      title: "입지 분석",
      loading: locationLoading,
      content: (
        sectionErrors.location && !locationData
          ? <ErrorCard message={sectionErrors.location} />
          : (
            <ProGateSection feature="location_profile">
              <LocationProfile data={locationData} loading={locationLoading} districtName={districtName} />
            </ProGateSection>
          )
      ),
    },
    {
      id: "rent",
      icon: <Building2 className="h-4 w-4 text-rose-500" />,
      title: "임대료 트렌드",
      loading: rentLoading,
      content: (
        sectionErrors.rent && !rentData
          ? <ErrorCard message={sectionErrors.rent} />
          : (
            <ProGateSection feature="rent_trend">
              <RentTrendChart data={rentData} loading={rentLoading} districtName={districtName} />
            </ProGateSection>
          )
      ),
    },
    {
      id: "salesTrend",
      icon: <TrendingUp className="h-4 w-4 text-violet-500" />,
      title: "매출 트렌드",
      loading: salesTrendLoading,
      content: (
        sectionErrors.salesTrend && !salesTrendData
          ? <ErrorCard message={sectionErrors.salesTrend} />
          : <SalesTrendChart data={salesTrendData} loading={salesTrendLoading} districtName={districtName} industryName={industryName} />
      ),
    },
    {
      id: "customer",
      icon: <Users className="h-4 w-4 text-cyan-500" />,
      title: "고객 분석",
      loading: customerLoading,
      content: (
        sectionErrors.customer && !customerData
          ? <ErrorCard message={sectionErrors.customer} />
          : (
            <ProGateSection feature="full_customer_charts">
              <CustomerSection data={customerData} loading={customerLoading} districtName={districtName} industryName={industryName} />
            </ProGateSection>
          )
      ),
    },
    {
      id: "franchise",
      icon: <Building2 className="h-4 w-4 text-orange-500" />,
      title: "프랜차이즈",
      loading: franchiseLoading,
      content: (
        sectionErrors.franchise && !franchiseData
          ? <ErrorCard message={sectionErrors.franchise} />
          : (
            <ProGateSection feature="franchise_comparison">
              <FranchiseSection data={franchiseData} loading={franchiseLoading} industryName={industryName} />
            </ProGateSection>
          )
      ),
    },
  ];

  const riskSections = [
    {
      id: "risk",
      icon: <AlertTriangle className="h-4 w-4 text-amber-500" />,
      title: "리스크 & 기회",
      loading: riskLoading,
      content: (
        sectionErrors.risk && !riskData
          ? <ErrorCard message={sectionErrors.risk} />
          : (
            <ProGateSection feature="risk_full">
              <RiskSection data={riskData} loading={riskLoading} districtName={districtName} />
            </ProGateSection>
          )
      ),
    },
    {
      id: "support",
      icon: <Gift className="h-4 w-4 text-green-500" />,
      title: "지원금",
      loading: supportLoading,
      content: (
        sectionErrors.support && !supportData
          ? <ErrorCard message={sectionErrors.support} />
          : <SupportSection data={supportData} loading={supportLoading} industryName={industryName} />
      ),
    },
    {
      id: "trademark",
      icon: <ShieldCheck className="h-4 w-4 text-purple-500" />,
      title: "상표 검사",
      loading: false,
      content: <TrademarkCheckCard industryCode={industryCode} />,
    },
    {
      id: "simulator",
      icon: <SlidersHorizontal className="h-4 w-4 text-indigo-500" />,
      title: "수익 시뮬레이터",
      loading: simulationLoading,
      content: (
        sectionErrors.simulation && !simulationData
          ? <ErrorCard message={sectionErrors.simulation} />
          : (
            <ProGateSection feature="simulator_full">
              <InlineSimulatorSection defaults={simulationData} loading={simulationLoading} districtName={districtName} />
            </ProGateSection>
          )
      ),
    },
  ];

  const sectionGroups = [
    {
      id: "core",
      emoji: "🎯",
      title: "핵심 판단 근거",
      subtitle: "성공 점수 · 수익 구조 · 경쟁 환경",
      sections: coreSections,
    },
    {
      id: "detail",
      emoji: "🔍",
      title: "상세 분석",
      subtitle: "입지 · 임대료 · 매출 트렌드 · 고객 · 프랜차이즈",
      sections: detailSections,
    },
    {
      id: "risk",
      emoji: "🛡️",
      title: "리스크 & 지원",
      subtitle: "위험 요소 · 기회 · 지원금 · 시뮬레이터",
      sections: riskSections,
    },
  ];

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
            className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md"
          >
            시작하기
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 pb-20 pt-8 sm:px-6">
        {/* Stepper */}
        <AnalyzeStepper currentStep={2} className="mb-8" />

        {/* Title */}
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-extrabold text-slate-900 sm:text-3xl">
            {store.industryIcon || "🍽️"} {industryName} 창업 분석 리포트
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            예산 {budget.toLocaleString()}만원 · 서울 1,077개 상권 중 AI 추천 TOP 3
          </p>
        </div>

        {/* ── LOADING STATE ── */}
        {top3Loading && <VerdictLoadingSkeleton />}

        {!top3Loading && topDistricts.length > 0 && selectedDistrict && (
          <div className="mb-6">
            <VerdictHeroCard
              district={selectedDistrict}
              industryCode={industryCode}
              verdictData={verdictData}
              verdictLoading={verdictLoading}
              onViewAlternative={(code) => {
                handleDistrictSelect(code);
              }}
            />
          </div>
        )}

        {/* ── CAFE TYPE RECOMMENDATION (카페 업종 전용) ── */}
        {!top3Loading && selectedCode && industryCode === "CS100010" && (
          <div className="mb-6">
            <CafeTypeCard
              industryCode={industryCode}
              districtCode={selectedCode}
              budgetMan={budget}
              experienceLevel={experienceLevel || undefined}
            />
          </div>
        )}

        {/* ── BENCHMARK ANALYSIS ── */}
        {!top3Loading && store.benchmarkStore && store.benchmarkStore.x && store.benchmarkStore.y && (
          <div className="mb-6">
            <BenchmarkAnalysisCard benchmark={store.benchmarkStore} />
          </div>
        )}

        {/* ── COMPETITIVE INSIGHT ── */}
        {!top3Loading && selectedCode && (
          <div className="mb-6">
            <CompetitiveInsightCard
              districtName={districtName}
              industryCode={industryCode}
              industryName={industryName}
              benchmarkSubCategory={store.benchmarkStore?.subCategory}
            />
          </div>
        )}

        {/* ── TOP 3 DISTRICT SELECTOR ── */}
        {!top3Loading && (
          <div id="section-top3" className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 sm:p-6">
            <Top3Section
              districts={topDistricts}
              selectedCode={selectedCode}
              onSelect={handleDistrictSelect}
              loading={false}
              industryName={industryName}
              benchmarkMarker={benchmarkMapMarker}
              similarityScores={Object.keys(similarityScores).length > 0 ? similarityScores : undefined}
            />
          </div>
        )}

        {/* ── AI BRIEFING + RISK ALERT ── */}
        {selectedCode && (
          <div className="mb-6 space-y-3">
            <BriefingCard districtCode={selectedCode} industryCode={industryCode} />
            <RiskAlertBanner districtCode={selectedCode} industryCode={industryCode} />
          </div>
        )}

        {selectedCode && (
          <>
            {isNoGo && !showDetailAnyway ? (
              <div className="mt-8 space-y-4 text-center">
                <div className="rounded-2xl border border-slate-200 bg-gradient-to-b from-slate-50 to-white p-8">
                  <p className="text-base font-semibold text-slate-700">
                    AI 코치가 이 상권을 추천하지 않습니다
                  </p>
                  <p className="mt-1 text-sm text-slate-400">
                    위의 대안 상권을 확인하거나, 조건을 변경해보세요.
                  </p>
                  <div className="mt-5 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
                    <Link
                      href={`/explore?industry_code=${encodeURIComponent(industryCode)}`}
                      className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-6 py-3 text-sm font-bold text-white transition hover:bg-slate-800"
                    >
                      <MapPin className="h-4 w-4" />
                      다른 상권 보기
                    </Link>
                    <Link
                      href="/analyze"
                      className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-6 py-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
                    >
                      <ArrowLeft className="h-4 w-4" />
                      조건 변경하기
                    </Link>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowDetailAnyway(true)}
                    className="mt-5 text-xs font-medium text-slate-400 underline decoration-slate-300 hover:text-slate-600"
                  >
                    그래도 상세 분석 보기
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {sectionGroups.map((group) => (
                  <SectionGroup
                    key={group.id}
                    id={group.id}
                    emoji={group.emoji}
                    title={group.title}
                    subtitle={group.subtitle}
                    isOpen={openGroups.has(group.id)}
                    onToggle={() => toggleGroup(group.id)}
                  >
                    {group.sections.map((section) => (
                      <AccordionItem
                        key={section.id}
                        id={section.id}
                        icon={section.icon}
                        title={section.title}
                        isOpen={openSections.has(section.id)}
                        onToggle={() => toggleSection(section.id)}
                        loading={section.loading}
                      >
                        {section.content}
                      </AccordionItem>
                    ))}
                  </SectionGroup>
                ))}
              </div>
            )}
          </>
        )}

        {/* ── CTA AT BOTTOM ── */}
        {selectedCode && (
          <div className="mt-10 flex flex-col items-center gap-4">
            <Link
              href={`/analyze/action?${ctaParams.toString()}`}
              className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-4 text-base font-bold text-white shadow-lg shadow-blue-500/25 transition hover:shadow-xl"
            >
              <Sparkles className="h-5 w-5" />
              다음 단계: 실행 체크리스트
              <ArrowRight className="h-5 w-5" />
            </Link>
            <div className="flex items-center gap-3">
              <Link
                href={`/timeline?district_code=${selectedCode}&industry_code=${industryCode}&budget=${budget}`}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                타임라인 보기
              </Link>
              <Link
                href="/analyze"
                className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 transition hover:text-slate-700"
              >
                <ArrowLeft className="h-4 w-4" />
                조건 변경
              </Link>
            </div>
          </div>
        )}
      </main>

      {/* Floating TOC for mobile */}
      {selectedCode && <FloatingTOC />}
    </div>
  );
}

export default function AnalyzeReportPage() {
  return (
    <ErrorBoundary>
      <Suspense
        fallback={
          <div className="flex min-h-screen items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          </div>
        }
      >
        <ReportContent />
      </Suspense>
    </ErrorBoundary>
  );
}
