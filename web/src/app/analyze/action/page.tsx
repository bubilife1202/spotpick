"use client";

import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { cn, formatMoney } from "@/lib/utils";
import { useAnalyzeStore } from "@/lib/analyze-store";
import { AnalyzeStepper } from "@/components/AnalyzeStepper";
import {
  MapPin,
  Loader2,
  ExternalLink,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Check,
  Briefcase,
  DollarSign,
  User,
  Building2,
  FileText,
  Landmark,
  Users,
  ClipboardCheck,
  Rocket,
  AlertTriangle,
  Download,
  TrendingUp,
  Shield,
  Scale,
  Clock,
  Banknote,
  Receipt,
  BadgeCheck,
  CircleDollarSign,
  HardHat,
  Lightbulb,
} from "lucide-react";

// ── Constants ───────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

const EXPERIENCE_LABELS: Record<string, string> = {
  beginner: "🌱 처음이에요",
  experienced: "💼 경험 있어요",
  expert: "🏆 전문가예요",
};

const EMPLOYEE_LABELS: Record<string, string> = {
  solo: "👤 1인 운영",
  "1-2": "👥 1-2명 고용",
  "3+": "👥👥 3명 이상",
};

interface PhaseConfig {
  id: number;
  key: string;
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  gradient: string;
  accentBg: string;
  accentText: string;
  borderActive: string;
}

const PHASES: PhaseConfig[] = [
  {
    id: 1,
    key: "design",
    title: "사업 설계",
    subtitle: "비즈니스 모델 & 컨셉",
    icon: <Lightbulb className="h-4 w-4" />,
    gradient: "from-violet-500 to-purple-600",
    accentBg: "bg-violet-50",
    accentText: "text-violet-700",
    borderActive: "border-violet-500",
  },
  {
    id: 2,
    key: "funding",
    title: "자금 계획",
    subtitle: "예산 배분 & 자금 조달",
    icon: <CircleDollarSign className="h-4 w-4" />,
    gradient: "from-emerald-500 to-teal-600",
    accentBg: "bg-emerald-50",
    accentText: "text-emerald-700",
    borderActive: "border-emerald-500",
  },
  {
    id: 3,
    key: "taxlabor",
    title: "세금·노무",
    subtitle: "절세 전략 & 고용 관리",
    icon: <Receipt className="h-4 w-4" />,
    gradient: "from-blue-500 to-indigo-600",
    accentBg: "bg-blue-50",
    accentText: "text-blue-700",
    borderActive: "border-blue-500",
  },
  {
    id: 4,
    key: "compliance",
    title: "계약·인허가",
    subtitle: "임대 계약 & 허가 절차",
    icon: <Shield className="h-4 w-4" />,
    gradient: "from-amber-500 to-orange-600",
    accentBg: "bg-amber-50",
    accentText: "text-amber-700",
    borderActive: "border-amber-500",
  },
  {
    id: 5,
    key: "launch",
    title: "오픈 준비",
    subtitle: "최종 점검 & 런칭",
    icon: <Rocket className="h-4 w-4" />,
    gradient: "from-rose-500 to-pink-600",
    accentBg: "bg-rose-50",
    accentText: "text-rose-700",
    borderActive: "border-rose-500",
  },
];

// ── Types ────────────────────────────────────────────────────────

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface BlueprintData {
  business_concept?: string;
  target_customer?: string;
  menu_strategy?: string;
  positioning?: string;
  key_differentiator?: string;
  recommendations?: Array<{ title: string; description: string }>;
  risk_factors?: Array<{ title: string; description: string; severity?: string }>;
  [key: string]: unknown;
}

interface FundingCostItem {
  label: string;
  amount: number;
  ratio?: number;
  category?: string;
}

interface FundingSource {
  name: string;
  type: string;
  amount?: number;
  url?: string;
  description?: string;
}

interface FundingData {
  total_budget?: number;
  cost_breakdown?: FundingCostItem[];
  funding_sources?: FundingSource[];
  monthly_fixed_cost?: number;
  reserve_fund?: number;
  summary?: string;
  [key: string]: unknown;
}

interface TaxData {
  tax_type?: string;
  estimated_tax?: number;
  tips?: Array<{ title: string; description: string; link?: { label: string; url: string } }>;
  deductions?: Array<{ name: string; amount?: number; description?: string }>;
  summary?: string;
  [key: string]: unknown;
}

interface LaborData {
  min_wage?: number;
  insurance_items?: Array<{ name: string; rate?: number; description?: string }>;
  tips?: Array<{ title: string; description: string; link?: { label: string; url: string } }>;
  contract_checklist?: string[];
  summary?: string;
  [key: string]: unknown;
}

interface LeaseData {
  avg_deposit?: number;
  avg_monthly_rent?: number;
  tips?: Array<{ title: string; description: string }>;
  negotiation_points?: string[];
  checklist?: string[];
  summary?: string;
  [key: string]: unknown;
}

interface ComplianceData {
  permits?: Array<{ name: string; issuer?: string; duration?: string; url?: string; description?: string }>;
  steps?: Array<{ step: number; title: string; description: string; duration?: string }>;
  tips?: Array<{ title: string; description: string }>;
  summary?: string;
  [key: string]: unknown;
}

// ── Skeleton ────────────────────────────────────────────────────

function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn("animate-pulse rounded-lg bg-slate-200/60", className)}
    />
  );
}

function PhaseSkeleton() {
  return (
    <div className="space-y-4 p-1">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-xl border border-slate-100 bg-white p-4">
            <Skeleton className="mb-2 h-3 w-16" />
            <Skeleton className="mb-1 h-6 w-24" />
            <Skeleton className="h-3 w-20" />
          </div>
        ))}
      </div>
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-xl border border-slate-100 bg-white p-4">
            <Skeleton className="mb-2 h-4 w-3/4" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="mt-1 h-3 w-2/3" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Error Card ──────────────────────────────────────────────────

function ErrorCard({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-xl border border-rose-200 bg-rose-50/50 p-5 text-center">
      <AlertTriangle className="mx-auto mb-2 h-6 w-6 text-rose-400" />
      <p className="text-sm font-medium text-rose-700">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-rose-100 px-3 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-200"
        >
          <RefreshCw className="h-3 w-3" />
          다시 시도
        </button>
      )}
    </div>
  );
}

// ── Stat Card ───────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  icon,
  accent = "blue",
}: {
  label: string;
  value: string;
  sub?: string;
  icon?: React.ReactNode;
  accent?: "blue" | "emerald" | "violet" | "amber" | "rose";
}) {
  const accents = {
    blue: "bg-blue-50 text-blue-600 border-blue-100",
    emerald: "bg-emerald-50 text-emerald-600 border-emerald-100",
    violet: "bg-violet-50 text-violet-600 border-violet-100",
    amber: "bg-amber-50 text-amber-600 border-amber-100",
    rose: "bg-rose-50 text-rose-600 border-rose-100",
  };
  return (
    <div className={cn("rounded-xl border p-3.5 transition-all", accents[accent])}>
      <div className="mb-1 flex items-center gap-1.5">
        {icon && <span className="opacity-70">{icon}</span>}
        <span className="text-[10px] font-semibold uppercase tracking-wider opacity-60">
          {label}
        </span>
      </div>
      <p className="text-lg font-extrabold leading-tight">{value}</p>
      {sub && <p className="mt-0.5 text-[10px] opacity-60">{sub}</p>}
    </div>
  );
}

// ── Action Item ─────────────────────────────────────────────────

function ActionItem({
  title,
  description,
  link,
  checked,
  onToggle,
  priority,
  estimate,
}: {
  title: string;
  description: string;
  link?: { label: string; url: string } | null;
  checked: boolean;
  onToggle: () => void;
  priority?: string;
  estimate?: string;
}) {
  const priorityBadge =
    priority === "high"
      ? "bg-rose-100 text-rose-700"
      : priority === "medium"
        ? "bg-amber-100 text-amber-700"
        : null;

  return (
    <div
      className={cn(
        "group relative rounded-xl border p-4 transition-all duration-200",
        checked
          ? "border-emerald-200 bg-emerald-50/30"
          : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm",
      )}
    >
      <div className="flex items-start gap-3">
        <button
          type="button"
          onClick={onToggle}
          className={cn(
            "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-all duration-200",
            checked
              ? "border-emerald-500 bg-emerald-500 text-white"
              : "border-slate-300 bg-white hover:border-blue-400",
          )}
          aria-label={`${title} ${checked ? "완료 취소" : "완료 처리"}`}
        >
          {checked && <Check className="h-3 w-3" strokeWidth={3} />}
        </button>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h4
              className={cn(
                "text-sm font-bold transition-all",
                checked
                  ? "text-emerald-700 line-through decoration-emerald-400"
                  : "text-slate-900",
              )}
            >
              {title}
            </h4>
            {priorityBadge && !checked && (
              <span className={cn("rounded-full px-1.5 py-0.5 text-[9px] font-bold", priorityBadge)}>
                {priority === "high" ? "중요" : "권장"}
              </span>
            )}
            {estimate && (
              <span className="ml-auto shrink-0 text-[10px] font-medium text-slate-400">
                {checked ? "✓" : estimate}
              </span>
            )}
          </div>
          <p className={cn("mt-1 text-xs leading-relaxed", checked ? "text-slate-400" : "text-slate-600")}>
            {description}
          </p>
          {link && (
            <a
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-semibold text-blue-600 transition hover:bg-blue-100"
            >
              {link.label}
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Hook: useFetch ──────────────────────────────────────────────

function useFetch<T>(url: string | null): FetchState<T> & { refetch: () => void } {
  const [state, setState] = useState<FetchState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const fetchData = useCallback(() => {
    if (!url) return;
    setState({ data: null, loading: true, error: null });
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`API 오류 (${res.status})`);
        return res.json();
      })
      .then((data: T) => setState({ data, loading: false, error: null }))
      .catch((err: Error) =>
        setState({ data: null, loading: false, error: err.message }),
      );
  }, [url]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { ...state, refetch: fetchData };
}

// ── Phase 1: 사업 설계 ──────────────────────────────────────────

function Phase1Content({
  data,
  loading,
  error,
  onRetry,
}: {
  data: BlueprintData | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  if (loading) return <PhaseSkeleton />;
  if (error) return <ErrorCard message={error} onRetry={onRetry} />;
  if (!data) return <ErrorCard message="데이터를 불러올 수 없습니다" onRetry={onRetry} />;

  const recommendations = data.recommendations || [];
  const risks = data.risk_factors || [];

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Key concept cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {data.business_concept && (
          <StatCard
            label="비즈니스 컨셉"
            value={data.business_concept}
            icon={<Lightbulb className="h-3.5 w-3.5" />}
            accent="violet"
          />
        )}
        {data.target_customer && (
          <StatCard
            label="타겟 고객"
            value={data.target_customer}
            icon={<Users className="h-3.5 w-3.5" />}
            accent="blue"
          />
        )}
        {data.menu_strategy && (
          <StatCard
            label="메뉴 전략"
            value={data.menu_strategy}
            icon={<ClipboardCheck className="h-3.5 w-3.5" />}
            accent="emerald"
          />
        )}
        {data.positioning && (
          <StatCard
            label="포지셔닝"
            value={data.positioning}
            icon={<TrendingUp className="h-3.5 w-3.5" />}
            accent="amber"
          />
        )}
      </div>

      {data.key_differentiator && (
        <div className="rounded-xl border border-violet-200 bg-gradient-to-r from-violet-50 to-purple-50 p-4">
          <p className="mb-1 text-[10px] font-bold uppercase tracking-wider text-violet-500">
            핵심 차별화 포인트
          </p>
          <p className="text-sm font-semibold leading-relaxed text-violet-900">
            {data.key_differentiator}
          </p>
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
            AI 추천 전략
          </h4>
          <div className="space-y-2">
            {recommendations.map((rec) => (
              <div
                key={`${rec.title}-${rec.description}`}
                className="rounded-xl border border-slate-100 bg-white p-3.5"
              >
                <p className="text-sm font-bold text-slate-900">{rec.title}</p>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">{rec.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk factors */}
      {risks.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
            리스크 요인
          </h4>
          <div className="space-y-2">
            {risks.map((risk) => (
              <div
                key={`${risk.severity}-${risk.title}`}
                className={cn(
                  "rounded-xl border p-3.5",
                  risk.severity === "high"
                    ? "border-rose-200 bg-rose-50/50"
                    : "border-amber-200 bg-amber-50/50",
                )}
              >
                <div className="flex items-center gap-2">
                  <AlertTriangle
                    className={cn(
                      "h-3.5 w-3.5",
                      risk.severity === "high" ? "text-rose-500" : "text-amber-500",
                    )}
                  />
                  <p
                    className={cn(
                      "text-sm font-bold",
                      risk.severity === "high" ? "text-rose-800" : "text-amber-800",
                    )}
                  >
                    {risk.title}
                  </p>
                </div>
                <p
                  className={cn(
                    "mt-1 text-xs leading-relaxed",
                    risk.severity === "high" ? "text-rose-700" : "text-amber-700",
                  )}
                >
                  {risk.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Phase 2: 자금 계획 ──────────────────────────────────────────

function Phase2Content({
  data,
  loading,
  error,
  onRetry,
  budget,
}: {
  data: FundingData | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  budget: number;
}) {
  if (loading) return <PhaseSkeleton />;
  if (error) return <ErrorCard message={error} onRetry={onRetry} />;
  if (!data) return <ErrorCard message="데이터를 불러올 수 없습니다" onRetry={onRetry} />;

  const costBreakdown = data.cost_breakdown || [];
  const fundingSources = data.funding_sources || [];
  const totalBudget = data.total_budget || budget * 10000;
  const maxAmount = Math.max(...costBreakdown.map((c) => c.amount || 0), 1);

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <StatCard
          label="총 예산"
          value={formatMoney(totalBudget)}
          icon={<Banknote className="h-3.5 w-3.5" />}
          accent="emerald"
        />
        {data.monthly_fixed_cost != null && (
          <StatCard
            label="월 고정비"
            value={formatMoney(data.monthly_fixed_cost)}
            icon={<Receipt className="h-3.5 w-3.5" />}
            accent="blue"
          />
        )}
        {data.reserve_fund != null && (
          <StatCard
            label="예비비"
            value={formatMoney(data.reserve_fund)}
            icon={<Shield className="h-3.5 w-3.5" />}
            accent="amber"
          />
        )}
      </div>

      {data.summary && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4">
          <p className="text-xs leading-relaxed text-emerald-800">{data.summary}</p>
        </div>
      )}

      {/* Cost breakdown bars — driven by API, not hardcoded */}
      {costBreakdown.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h4 className="mb-3 text-xs font-bold text-slate-900">비용 배분</h4>
          <div className="space-y-2.5">
            {costBreakdown.map((row) => {
              const pct =
                row.ratio != null
                  ? Math.round(row.ratio * 100)
                  : totalBudget > 0
                    ? Math.round((row.amount / totalBudget) * 100)
                    : 0;
              const barWidth = maxAmount > 0 ? (row.amount / maxAmount) * 100 : 0;
              return (
                <div key={`cost-${row.label}`}>
                  <div className="flex items-center gap-3">
                    <span className="w-24 shrink-0 text-xs font-medium text-slate-600 sm:w-28">
                      {row.label}
                    </span>
                    <div className="flex flex-1 items-center gap-2">
                      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-teal-400 transition-all duration-500"
                          style={{ width: `${Math.min(100, barWidth)}%` }}
                        />
                      </div>
                      <span className="w-10 shrink-0 text-right text-[11px] font-semibold text-slate-500">
                        {pct}%
                      </span>
                    </div>
                    <span className="w-20 shrink-0 text-right text-xs font-bold text-slate-800 sm:w-24">
                      {formatMoney(row.amount)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2.5">
            <span className="text-xs font-bold text-slate-700">합계</span>
            <span className="text-sm font-extrabold text-slate-900">
              {formatMoney(totalBudget)}
            </span>
          </div>
        </div>
      )}

      {/* Funding sources */}
      {fundingSources.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
            자금 조달 방안
          </h4>
          <div className="space-y-2">
            {fundingSources.map((src) => (
              <div
                key={`${src.type}-${src.name}`}
                className="rounded-xl border border-slate-100 bg-white p-3.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Landmark className="h-3.5 w-3.5 text-emerald-500" />
                    <p className="text-sm font-bold text-slate-900">{src.name}</p>
                    <span className="rounded-full bg-emerald-100 px-1.5 py-0.5 text-[9px] font-bold text-emerald-700">
                      {src.type}
                    </span>
                  </div>
                  {src.amount != null && (
                    <span className="text-xs font-bold text-emerald-700">
                      {formatMoney(src.amount)}
                    </span>
                  )}
                </div>
                {src.description && (
                  <p className="mt-1 text-xs text-slate-600">{src.description}</p>
                )}
                {src.url && (
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:text-blue-700"
                  >
                    바로가기 <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Phase 3: 세금·노무 ──────────────────────────────────────────

function Phase3Content({
  taxData,
  laborData,
  taxLoading,
  laborLoading,
  taxError,
  laborError,
  onRetryTax,
  onRetryLabor,
}: {
  taxData: TaxData | null;
  laborData: LaborData | null;
  taxLoading: boolean;
  laborLoading: boolean;
  taxError: string | null;
  laborError: string | null;
  onRetryTax: () => void;
  onRetryLabor: () => void;
}) {
  const loading = taxLoading || laborLoading;
  if (loading) return <PhaseSkeleton />;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Tax Section */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <Receipt className="h-4 w-4 text-blue-500" />
          <h4 className="text-sm font-bold text-slate-900">세금 어드바이스</h4>
        </div>
        {taxError ? (
          <ErrorCard message={taxError} onRetry={onRetryTax} />
        ) : !taxData ? (
          <ErrorCard message="세금 데이터를 불러올 수 없습니다" onRetry={onRetryTax} />
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              {taxData.tax_type && (
                <StatCard
                  label="사업자 유형"
                  value={taxData.tax_type}
                  icon={<FileText className="h-3.5 w-3.5" />}
                  accent="blue"
                />
              )}
              {taxData.estimated_tax != null && (
                <StatCard
                  label="예상 세금"
                  value={formatMoney(taxData.estimated_tax)}
                  sub="연간 추정"
                  icon={<Scale className="h-3.5 w-3.5" />}
                  accent="rose"
                />
              )}
            </div>

            {taxData.summary && (
              <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-3.5">
                <p className="text-xs leading-relaxed text-blue-800">{taxData.summary}</p>
              </div>
            )}

            {/* Tax deductions */}
            {taxData.deductions && taxData.deductions.length > 0 && (
              <div className="rounded-xl border border-slate-100 bg-white p-3.5">
                <p className="mb-2 text-xs font-bold text-slate-700">절세 공제 항목</p>
                <div className="space-y-1.5">
                  {taxData.deductions.map((d) => (
                    <div
                      key={d.name}
                      className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2"
                    >
                      <span className="text-xs font-medium text-slate-700">{d.name}</span>
                      {d.amount != null && (
                        <span className="text-xs font-bold text-blue-700">
                          {formatMoney(d.amount)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tax tips */}
            {taxData.tips && taxData.tips.length > 0 && (
              <div className="space-y-2">
                {taxData.tips.map((tip) => (
                  <div key={tip.title} className="rounded-xl border border-slate-100 bg-white p-3.5">
                    <p className="text-sm font-bold text-slate-900">{tip.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-600">{tip.description}</p>
                    {tip.link && (
                      <a
                        href={tip.link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600"
                      >
                        {tip.link.label} <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="h-px bg-slate-100" />

      {/* Labor Section */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <Users className="h-4 w-4 text-indigo-500" />
          <h4 className="text-sm font-bold text-slate-900">노무 어드바이스</h4>
        </div>
        {laborError ? (
          <ErrorCard message={laborError} onRetry={onRetryLabor} />
        ) : !laborData ? (
          <ErrorCard message="노무 데이터를 불러올 수 없습니다" onRetry={onRetryLabor} />
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              {laborData.min_wage != null && (
                <StatCard
                  label="최저시급"
                  value={`${laborData.min_wage.toLocaleString()}원`}
                  sub="2025년 기준"
                  icon={<DollarSign className="h-3.5 w-3.5" />}
                  accent="emerald"
                />
              )}
            </div>

            {laborData.summary && (
              <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-3.5">
                <p className="text-xs leading-relaxed text-indigo-800">{laborData.summary}</p>
              </div>
            )}

            {/* Insurance items */}
            {laborData.insurance_items && laborData.insurance_items.length > 0 && (
              <div className="rounded-xl border border-slate-100 bg-white p-3.5">
                <p className="mb-2 text-xs font-bold text-slate-700">4대보험 체크</p>
                <div className="space-y-1.5">
                  {laborData.insurance_items.map((ins) => (
                    <div
                      key={ins.name}
                      className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2"
                    >
                      <span className="text-xs font-medium text-slate-700">{ins.name}</span>
                      {ins.rate != null && (
                        <span className="text-xs font-bold text-indigo-700">
                          {ins.rate}%
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Contract checklist */}
            {laborData.contract_checklist && laborData.contract_checklist.length > 0 && (
              <div className="rounded-xl border border-slate-100 bg-white p-3.5">
                <p className="mb-2 text-xs font-bold text-slate-700">근로계약서 체크리스트</p>
                <ul className="space-y-1">
                  {laborData.contract_checklist.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-xs text-slate-600">
                      <BadgeCheck className="mt-0.5 h-3 w-3 shrink-0 text-indigo-400" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Labor tips */}
            {laborData.tips && laborData.tips.length > 0 && (
              <div className="space-y-2">
                {laborData.tips.map((tip) => (
                  <div key={tip.title} className="rounded-xl border border-slate-100 bg-white p-3.5">
                    <p className="text-sm font-bold text-slate-900">{tip.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-600">{tip.description}</p>
                    {tip.link && (
                      <a
                        href={tip.link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1 text-[11px] font-semibold text-blue-600"
                      >
                        {tip.link.label} <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Phase 4: 계약·인허가 ────────────────────────────────────────

function Phase4Content({
  leaseData,
  complianceData,
  leaseLoading,
  complianceLoading,
  leaseError,
  complianceError,
  onRetryLease,
  onRetryCompliance,
  checked,
  onToggle,
}: {
  leaseData: LeaseData | null;
  complianceData: ComplianceData | null;
  leaseLoading: boolean;
  complianceLoading: boolean;
  leaseError: string | null;
  complianceError: string | null;
  onRetryLease: () => void;
  onRetryCompliance: () => void;
  checked: Set<string>;
  onToggle: (id: string) => void;
}) {
  const loading = leaseLoading || complianceLoading;
  if (loading) return <PhaseSkeleton />;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Lease Section */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <Building2 className="h-4 w-4 text-amber-500" />
          <h4 className="text-sm font-bold text-slate-900">임대 계약 가이드</h4>
        </div>
        {leaseError ? (
          <ErrorCard message={leaseError} onRetry={onRetryLease} />
        ) : !leaseData ? (
          <ErrorCard message="임대 데이터를 불러올 수 없습니다" onRetry={onRetryLease} />
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              {leaseData.avg_deposit != null && (
                <StatCard
                  label="평균 보증금"
                  value={formatMoney(leaseData.avg_deposit)}
                  icon={<Banknote className="h-3.5 w-3.5" />}
                  accent="amber"
                />
              )}
              {leaseData.avg_monthly_rent != null && (
                <StatCard
                  label="평균 월세"
                  value={formatMoney(leaseData.avg_monthly_rent)}
                  icon={<Building2 className="h-3.5 w-3.5" />}
                  accent="amber"
                />
              )}
            </div>

            {leaseData.summary && (
              <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3.5">
                <p className="text-xs leading-relaxed text-amber-800">{leaseData.summary}</p>
              </div>
            )}

            {/* Negotiation points */}
            {leaseData.negotiation_points && leaseData.negotiation_points.length > 0 && (
              <div className="rounded-xl border border-slate-100 bg-white p-3.5">
                <p className="mb-2 text-xs font-bold text-slate-700">협상 포인트</p>
                <ul className="space-y-1.5">
                  {leaseData.negotiation_points.map((point) => (
                    <li key={point} className="flex items-start gap-2 text-xs text-slate-600">
                      <ChevronRight className="mt-0.5 h-3 w-3 shrink-0 text-amber-400" />
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Lease checklist */}
            {leaseData.checklist && leaseData.checklist.length > 0 && (
              <div className="space-y-2">
                {leaseData.checklist.map((item, i) => {
                  const id = `lease-${i}`;
                  return (
                    <ActionItem
                      key={id}
                      title={item}
                      description=""
                      checked={checked.has(id)}
                      onToggle={() => onToggle(id)}
                    />
                  );
                })}
              </div>
            )}

            {/* Lease tips */}
            {leaseData.tips && leaseData.tips.length > 0 && (
              <div className="space-y-2">
                {leaseData.tips.map((tip) => (
                  <div key={tip.title} className="rounded-xl border border-slate-100 bg-white p-3.5">
                    <p className="text-sm font-bold text-slate-900">{tip.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-600">{tip.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="h-px bg-slate-100" />

      {/* Compliance / Permits Section */}
      <div>
        <div className="mb-3 flex items-center gap-2">
          <ClipboardCheck className="h-4 w-4 text-orange-500" />
          <h4 className="text-sm font-bold text-slate-900">인허가 절차</h4>
        </div>
        {complianceError ? (
          <ErrorCard message={complianceError} onRetry={onRetryCompliance} />
        ) : !complianceData ? (
          <ErrorCard message="인허가 데이터를 불러올 수 없습니다" onRetry={onRetryCompliance} />
        ) : (
          <div className="space-y-3">
            {complianceData.summary && (
              <div className="rounded-xl border border-orange-200 bg-orange-50/50 p-3.5">
                <p className="text-xs leading-relaxed text-orange-800">{complianceData.summary}</p>
              </div>
            )}

            {/* Required Permits */}
            {complianceData.permits && complianceData.permits.length > 0 && (
              <div className="rounded-xl border border-slate-100 bg-white p-3.5">
                <p className="mb-2 text-xs font-bold text-slate-700">필요 인허가 목록</p>
                <div className="space-y-2">
                  {complianceData.permits.map((permit, i) => {
                    const id = `permit-${i}`;
                    return (
                      <div
                        key={id}
                        className={cn(
                          "rounded-lg border p-3 transition-all",
                          checked.has(id)
                            ? "border-emerald-200 bg-emerald-50/30"
                            : "border-slate-100 bg-slate-50/50",
                        )}
                      >
                        <div className="flex items-start gap-2">
                          <button
                            type="button"
                            onClick={() => onToggle(id)}
                            className={cn(
                              "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border-2 transition-all",
                              checked.has(id)
                                ? "border-emerald-500 bg-emerald-500 text-white"
                                : "border-slate-300 bg-white",
                            )}
                          >
                            {checked.has(id) && <Check className="h-2.5 w-2.5" strokeWidth={3} />}
                          </button>
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <p className="text-xs font-bold text-slate-900">{permit.name}</p>
                              {permit.duration && (
                                <span className="rounded bg-slate-100 px-1 py-0.5 text-[9px] font-medium text-slate-500">
                                  <Clock className="mr-0.5 inline h-2.5 w-2.5" />
                                  {permit.duration}
                                </span>
                              )}
                            </div>
                            {permit.issuer && (
                              <p className="text-[10px] text-slate-500">발급처: {permit.issuer}</p>
                            )}
                            {permit.description && (
                              <p className="mt-0.5 text-[10px] text-slate-500">{permit.description}</p>
                            )}
                            {permit.url && (
                              <a
                                href={permit.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-1 inline-flex items-center gap-1 text-[10px] font-semibold text-blue-600"
                              >
                                바로가기 <ExternalLink className="h-2.5 w-2.5" />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Step-by-step process */}
            {complianceData.steps && complianceData.steps.length > 0 && (
              <div className="rounded-xl border border-slate-100 bg-white p-3.5">
                <p className="mb-2 text-xs font-bold text-slate-700">진행 순서</p>
                <div className="relative space-y-3 pl-6">
                  <div className="absolute left-[9px] top-1 h-[calc(100%-8px)] w-0.5 bg-slate-200" />
                  {complianceData.steps.map((step) => (
                    <div key={`step-${step.step}`} className="relative">
                      <div className="absolute -left-6 top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-orange-500 text-[8px] font-bold text-white">
                        {step.step}
                      </div>
                      <p className="text-xs font-bold text-slate-900">{step.title}</p>
                      <p className="mt-0.5 text-[10px] text-slate-600">{step.description}</p>
                      {step.duration && (
                        <span className="mt-0.5 inline-block text-[9px] text-slate-400">
                          소요: {step.duration}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Phase 5: 오픈 준비 ──────────────────────────────────────────

function Phase5Content({
  blueprintData,
  fundingData,
  checked,
  onToggle,
}: {
  blueprintData: BlueprintData | null;
  fundingData: FundingData | null;
  complianceData: ComplianceData | null;
  checked: Set<string>;
  onToggle: (id: string) => void;
}) {
  // Synthesize final checklist from all phase data
  const launchItems: Array<{
    id: string;
    title: string;
    description: string;
    priority: string;
    estimate?: string;
    link?: { label: string; url: string } | null;
  }> = [
    {
      id: "launch-interior",
      title: "인테리어 & 설비 시공",
      description:
        "최소 3곳 이상 견적을 받고, 소방 설비 기준을 확인하세요. 주방 동선은 업종 특성에 맞게 배치합니다.",
      priority: "high",
      estimate: "4-8주",
    },
    {
      id: "launch-menu",
      title: "메뉴 확정 & 가격 설정",
      description: blueprintData?.menu_strategy
        ? `AI 추천: ${blueprintData.menu_strategy}. 원가율 30-35% 기준으로 가격을 설정하세요.`
        : "원가율 30-35%를 기준으로 메뉴 가격을 설정하세요. 주변 경쟁 매장의 가격대도 참고하세요.",
      priority: "high",
      estimate: "1-2주",
    },
    {
      id: "launch-pos",
      title: "POS·키오스크 설치",
      description:
        "카드 결제 단말기, POS 시스템, 필요시 키오스크를 설치하세요. 배달앱 연동도 이 시점에 설정합니다.",
      priority: "high",
      estimate: "3-5일",
    },
    {
      id: "launch-hiring",
      title: "직원 채용 & 교육",
      description:
        "오픈 2주 전까지 직원을 확보하고 교육을 완료하세요. 4대보험 가입도 잊지 마세요.",
      priority: "medium",
      estimate: "2-3주",
      link: { label: "사람인", url: "https://www.saramin.co.kr" },
    },
    {
      id: "launch-marketing",
      title: "마케팅 & SNS 개설",
      description:
        "인스타그램/블로그 계정 개설, 오픈 이벤트 기획, 배달앱 등록을 준비하세요.",
      priority: "medium",
      estimate: "1-2주",
    },
    {
      id: "launch-preopen",
      title: "프리오픈 & 동선 점검",
      description:
        "정식 오픈 전 지인 초대 프리오픈으로 운영 동선과 메뉴 품질을 점검하세요.",
      priority: "high",
      estimate: "3-5일",
    },
    {
      id: "launch-signage",
      title: "간판 & 외부 홍보물",
      description:
        "간판 허가 여부를 확인하고 제작하세요. 어닝, A보드 등 외부 홍보물도 준비합니다.",
      priority: "medium",
      estimate: "1-2주",
    },
    {
      id: "launch-insurance",
      title: "영업배상책임보험 가입",
      description:
        "식중독, 화재 등 만약의 사고에 대비하여 영업배상책임보험에 가입하세요.",
      priority: "medium",
      estimate: "1일",
    },
  ];

  const checkedCount = launchItems.filter((i) => checked.has(i.id)).length;
  const progressPct =
    launchItems.length > 0
      ? Math.round((checkedCount / launchItems.length) * 100)
      : 0;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Progress */}
      <div className="rounded-xl border border-rose-200 bg-gradient-to-r from-rose-50 to-pink-50 p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-bold text-rose-800">오픈 준비 진행률</span>
          <span className="text-xs font-extrabold text-rose-600">
            {checkedCount}/{launchItems.length} ({progressPct}%)
          </span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-rose-100">
          <div
            className="h-full rounded-full bg-gradient-to-r from-rose-400 to-pink-500 transition-all duration-500 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Timeline hint */}
      {fundingData?.total_budget && (
        <div className="grid grid-cols-2 gap-3">
          <StatCard
            label="투자 총액"
            value={formatMoney(fundingData.total_budget)}
            icon={<Banknote className="h-3.5 w-3.5" />}
            accent="rose"
          />
          <StatCard
            label="남은 할 일"
            value={`${launchItems.length - checkedCount}건`}
            sub="완료하면 오픈 준비 끝!"
            icon={<HardHat className="h-3.5 w-3.5" />}
            accent="rose"
          />
        </div>
      )}

      {/* Launch checklist */}
      <div className="space-y-2.5">
        {launchItems.map((item) => (
          <ActionItem
            key={item.id}
            title={item.title}
            description={item.description}
            link={item.link}
            checked={checked.has(item.id)}
            onToggle={() => onToggle(item.id)}
            priority={item.priority}
            estimate={item.estimate}
          />
        ))}
      </div>

      {/* Useful links */}
      <div className="mt-2">
        <h4 className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-400">
          유용한 링크
        </h4>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {[
            { label: "소진공 창업교육", url: "https://edu.semas.or.kr", icon: "🎓" },
            { label: "서울신용보증재단", url: "https://www.seoulshinbo.co.kr", icon: "🏦" },
            { label: "네이버 부동산", url: "https://land.naver.com", icon: "🏠" },
            { label: "홈택스", url: "https://www.hometax.go.kr", icon: "📋" },
            { label: "정부24", url: "https://www.gov.kr", icon: "🏛️" },
            { label: "소상공인마당", url: "https://www.sbiz.or.kr", icon: "📊" },
          ].map((link) => (
            <a
              key={link.url}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-2.5 transition hover:border-blue-200 hover:bg-blue-50/50 hover:shadow-sm"
            >
              <span className="text-base">{link.icon}</span>
              <span className="text-[11px] font-semibold text-slate-700">{link.label}</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Phase Navigator ─────────────────────────────────────────────

function PhaseNav({
  activePhase,
  onSelect,
  completedPhases,
}: {
  activePhase: number;
  onSelect: (id: number) => void;
  completedPhases: Set<number>;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={scrollRef}
      className="scrollbar-hide -mx-4 flex gap-2 overflow-x-auto px-4 pb-2 sm:mx-0 sm:grid sm:grid-cols-5 sm:gap-2 sm:overflow-visible sm:px-0"
    >
      {PHASES.map((phase) => {
        const isActive = phase.id === activePhase;
        const isCompleted = completedPhases.has(phase.id);
        return (
          <button
            key={phase.id}
            type="button"
            onClick={() => onSelect(phase.id)}
            className={cn(
              "group relative flex shrink-0 items-center gap-2.5 rounded-xl border-2 px-3.5 py-3 text-left transition-all duration-200 sm:flex-col sm:items-start sm:gap-1 sm:px-3 sm:py-2.5",
              isActive
                ? cn(phase.borderActive, "bg-white shadow-md")
                : isCompleted
                  ? "border-emerald-200 bg-emerald-50/50 hover:shadow-sm"
                  : "border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm",
            )}
          >
            {/* Phase number badge */}
            <div
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-xs font-bold text-white transition-all sm:h-6 sm:w-6",
                isActive
                  ? cn("bg-gradient-to-br", phase.gradient)
                  : isCompleted
                    ? "bg-emerald-500"
                    : "bg-slate-300",
              )}
            >
              {isCompleted && !isActive ? (
                <Check className="h-3 w-3" strokeWidth={3} />
              ) : (
                phase.id
              )}
            </div>
            <div className="min-w-0">
              <p
                className={cn(
                  "text-xs font-bold leading-tight",
                  isActive ? phase.accentText : isCompleted ? "text-emerald-700" : "text-slate-700",
                )}
              >
                {phase.title}
              </p>
              <p className="hidden text-[10px] text-slate-400 sm:block">{phase.subtitle}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ── Main Content ────────────────────────────────────────────────

function ActionContent() {
  const searchParams = useSearchParams();
  const store = useAnalyzeStore();

  // Extract params
  const industryCode =
    searchParams?.get("industry_code") || store.industryCode;
  const districtCode =
    searchParams?.get("district_code") || store.selectedDistrictCode;
  const budget =
    Number(searchParams?.get("budget")) ||
    Number(searchParams?.get("budget_max")) ||
    store.budget;
  const experienceLevel =
    searchParams?.get("experience_level") || store.experienceLevel || "";
  const employeeCount =
    searchParams?.get("employee_count") || store.employeeCount || "";

  // Set step in store
  useEffect(() => {
    useAnalyzeStore.getState().setStep(3);
  }, []);

  useEffect(() => {
    const { setExperienceLevel, setEmployeeCount } = useAnalyzeStore.getState();
    if (experienceLevel) setExperienceLevel(experienceLevel);
    if (employeeCount) setEmployeeCount(employeeCount);
  }, [experienceLevel, employeeCount]);

  // Active phase
  const [activePhase, setActivePhase] = useState(1);
  const [completedPhases, setCompletedPhases] = useState<Set<number>>(new Set());

  // Checklist state (persisted)
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [checklistLoaded, setChecklistLoaded] = useState(false);

  const storageKey = `spotpick:action:${industryCode}:${districtCode || "none"}`;

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) {
        setChecked(new Set());
        setChecklistLoaded(true);
        return;
      }
      const parsed: unknown = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        const ids = parsed.filter((x): x is string => typeof x === "string");
        setChecked(new Set(ids));
      } else {
        setChecked(new Set());
      }
    } catch {
      setChecked(new Set());
    } finally {
      setChecklistLoaded(true);
    }
  }, [storageKey]);

  useEffect(() => {
    if (!checklistLoaded) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify(Array.from(checked)));
    } catch {
      // ignore storage failures
    }
  }, [checked, storageKey, checklistLoaded]);

  const toggle = (id: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const buildQuery = (params: Record<string, string | number | boolean | null | undefined>) => {
    const usp = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v === undefined || v === null) return;
      usp.set(k, String(v));
    });
    return usp.toString();
  };

  const common = {
    industry_code: industryCode,
    district_code: districtCode || undefined,
  };

  const blueprintQuery = buildQuery({
    ...common,
    budget_man: budget,
    experience_level: experienceLevel || undefined,
    employee_count: employeeCount || undefined,
    area_pyeong: 10,
  });

  const fundingQuery = buildQuery({
    ...common,
    area_pyeong: 10,
    use_ecos: true,
  });

  const taxQuery = buildQuery({
    ...common,
  });

  const laborQuery = buildQuery({
    ...common,
    employee_plan: employeeCount || undefined,
  });

  const leaseQuery = buildQuery({
    ...common,
    region: "seoul",
  });

  const complianceQuery = buildQuery({
    ...common,
  });

  // API fetches
  const blueprint = useFetch<BlueprintData>(
    districtCode ? `${API_BASE}/blueprint/generate?${blueprintQuery}` : null,
  );
  const funding = useFetch<FundingData>(
    districtCode ? `${API_BASE}/funding/plan?${fundingQuery}` : null,
  );
  const tax = useFetch<TaxData>(
    districtCode ? `${API_BASE}/tax/advice?${taxQuery}` : null,
  );
  const labor = useFetch<LaborData>(
    districtCode ? `${API_BASE}/labor/advice?${laborQuery}` : null,
  );
  const lease = useFetch<LeaseData>(
    districtCode ? `${API_BASE}/lease/advice?${leaseQuery}` : null,
  );
  const compliance = useFetch<ComplianceData>(
    districtCode ? `${API_BASE}/compliance/advice?${complianceQuery}` : null,
  );

  // Track completed phases (simple heuristic: data loaded without error)
  useEffect(() => {
    const completed = new Set<number>();
    if (blueprint.data && !blueprint.error) completed.add(1);
    if (funding.data && !funding.error) completed.add(2);
    if ((tax.data || labor.data) && !tax.error && !labor.error) completed.add(3);
    if ((lease.data || compliance.data) && !lease.error && !compliance.error)
      completed.add(4);
    // Phase 5 is manually tracked
    setCompletedPhases(completed);
  }, [
    blueprint.data,
    blueprint.error,
    funding.data,
    funding.error,
    tax.data,
    tax.error,
    labor.data,
    labor.error,
    lease.data,
    lease.error,
    compliance.data,
    compliance.error,
  ]);

  // Derived data
  const selectedDistrict = store.topDistricts.find(
    (d) => d.district_code === districtCode,
  );
  const districtName = selectedDistrict?.district_name || "선택된 상권";
  const industryName = store.industryName || "업종";
  const experienceLabel =
    EXPERIENCE_LABELS[experienceLevel] || experienceLevel || "미입력";
  const employeeLabel =
    EMPLOYEE_LABELS[employeeCount] || employeeCount || "미입력";
  const profileLabel = [experienceLabel, employeeLabel]
    .filter(Boolean)
    .join(" · ");

  // Navigation query string
  const queryString = new URLSearchParams({
    industry_code: industryCode,
    ...(districtCode ? { district_code: districtCode } : {}),
    budget: String(budget),
  }).toString();

  // Render active phase content
  const renderPhaseContent = () => {
    switch (activePhase) {
      case 1:
        return (
          <Phase1Content
            data={blueprint.data}
            loading={blueprint.loading}
            error={blueprint.error}
            onRetry={blueprint.refetch}
          />
        );
      case 2:
        return (
          <Phase2Content
            data={funding.data}
            loading={funding.loading}
            error={funding.error}
            onRetry={funding.refetch}
            budget={budget}
          />
        );
      case 3:
        return (
          <Phase3Content
            taxData={tax.data}
            laborData={labor.data}
            taxLoading={tax.loading}
            laborLoading={labor.loading}
            taxError={tax.error}
            laborError={labor.error}
            onRetryTax={tax.refetch}
            onRetryLabor={labor.refetch}
          />
        );
      case 4:
        return (
          <Phase4Content
            leaseData={lease.data}
            complianceData={compliance.data}
            leaseLoading={lease.loading}
            complianceLoading={compliance.loading}
            leaseError={lease.error}
            complianceError={compliance.error}
            onRetryLease={lease.refetch}
            onRetryCompliance={compliance.refetch}
            checked={checked}
            onToggle={toggle}
          />
        );
      case 5:
        return (
          <Phase5Content
            blueprintData={blueprint.data}
            fundingData={funding.data}
            complianceData={compliance.data}
            checked={checked}
            onToggle={toggle}
          />
        );
      default:
        return null;
    }
  };

  const currentPhase = PHASES.find((p) => p.id === activePhase);

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
          <div className="flex items-center gap-2">
            {/* Export stub */}
            <button
              type="button"
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-semibold text-slate-500 transition hover:bg-slate-50"
              title="PDF 내보내기 (준비 중)"
              disabled
            >
              <Download className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Export</span>
            </button>
            <Link
              href="/analyze"
              className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md"
            >
              시작하기
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-20 pt-8 sm:px-6">
        {/* Stepper */}
        <AnalyzeStepper currentStep={3} className="mb-8" />

        {/* Title */}
        <div className="mb-6 text-center animate-slide-up">
          <h1 className="text-2xl font-extrabold text-slate-900 sm:text-3xl">
            🚀 창업 실행 대시보드
          </h1>
          <p className="mt-1.5 text-sm text-slate-500">
            {districtName} {industryName} 창업을 위한 5단계 실행 가이드
          </p>
        </div>

        {/* Context Card */}
        <div className="mb-6 animate-slide-up rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                <Briefcase className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  업종
                </p>
                <p className="truncate text-xs font-bold text-slate-800">
                  {store.industryIcon} {industryName}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                <Building2 className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  상권
                </p>
                <p className="truncate text-xs font-bold text-slate-800">
                  {districtName}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
                <DollarSign className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  예산
                </p>
                <p className="truncate text-xs font-bold text-slate-800">
                  {formatMoney(budget * 10000)}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
                <User className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                  프로필
                </p>
                <p className="truncate text-xs font-bold text-slate-800">{profileLabel}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Phase Navigator */}
        <div className="mb-6 animate-slide-up">
          <PhaseNav
            activePhase={activePhase}
            onSelect={setActivePhase}
            completedPhases={completedPhases}
          />
        </div>

        {/* Phase Content */}
        <div className="animate-slide-up">
          {/* Phase header */}
          {currentPhase && (
            <div className="mb-4 flex items-center gap-3">
              <div
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br text-white",
                  currentPhase.gradient,
                )}
              >
                {currentPhase.icon}
              </div>
              <div>
                <h2 className="text-lg font-extrabold text-slate-900">
                  Phase {currentPhase.id}. {currentPhase.title}
                </h2>
                <p className="text-xs text-slate-500">{currentPhase.subtitle}</p>
              </div>
              {/* Phase nav arrows */}
              <div className="ml-auto flex gap-1">
                <button
                  type="button"
                  onClick={() => setActivePhase(Math.max(1, activePhase - 1))}
                  disabled={activePhase === 1}
                  className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-400 transition hover:bg-slate-50 disabled:opacity-30"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  type="button"
                  onClick={() => setActivePhase(Math.min(5, activePhase + 1))}
                  disabled={activePhase === 5}
                  className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-400 transition hover:bg-slate-50 disabled:opacity-30"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {/* Phase body */}
          <div className="min-h-[300px]">{renderPhaseContent()}</div>
        </div>

        {/* Bottom CTAs */}
        <div className="mt-12 flex flex-col gap-3 sm:flex-row">
          <Link
            href={`/analyze/report?${queryString}`}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          >
            <ChevronLeft className="h-4 w-4" />
            진단 결과 다시 보기
          </Link>
          <Link
            href="/analyze"
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            처음부터 다시 분석하기
          </Link>
        </div>
      </main>
    </div>
  );
}

export default function AnalyzeActionPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <ActionContent />
    </Suspense>
  );
}
