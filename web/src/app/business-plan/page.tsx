"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  FileText,
  TrendingUp,
  DollarSign,
  Store,
  Shield,
  CalendarDays,
  ChevronRight,
  Loader2,
  CheckCircle,
  RefreshCw,
  Pencil,
  ShoppingBag,
  Megaphone,
  AlertTriangle,
  Users,
  Clock,
  Target,
  BarChart3,
} from "lucide-react";
import DOMPurify from "dompurify";
import { cn } from "@/lib/utils";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

// ============================================================================
// Constants
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

const INDUSTRY_NAMES: Record<string, string> = {
  CS100001: "한식", CS100002: "중식", CS100003: "일식", CS100004: "양식",
  CS100005: "베이커리", CS100006: "패스트푸드", CS100007: "치킨",
  CS100008: "분식", CS100009: "호프/주점", CS100010: "카페",
};

const INDUSTRY_ICONS: Record<string, string> = {
  CS100001: "🍚", CS100002: "🥟", CS100003: "🍣", CS100004: "🍝",
  CS100005: "🍞", CS100006: "🍔", CS100007: "🍗",
  CS100008: "🍜", CS100009: "🍺", CS100010: "☕",
};

const SECTION_ICONS: Record<string, React.ReactNode> = {
  overview: <FileText className="w-4 h-4" />,
  market: <TrendingUp className="w-4 h-4" />,
  competition: <Store className="w-4 h-4" />,
  menu: <ShoppingBag className="w-4 h-4" />,
  marketing: <Megaphone className="w-4 h-4" />,
  financials: <DollarSign className="w-4 h-4" />,
  risk: <Shield className="w-4 h-4" />,
  roadmap: <CalendarDays className="w-4 h-4" />,
};

const SECTION_NUMBERS: Record<string, string> = {
  overview: "01",
  market: "02",
  competition: "03",
  menu: "04",
  marketing: "05",
  financials: "06",
  risk: "07",
  roadmap: "08",
};

const DONUT_COLORS = ["#3B82F6", "#8B5CF6", "#F59E0B", "#10B981", "#EF4444", "#EC4899"];

// ============================================================================
// Types
// ============================================================================

interface PlanSection {
  id: string;
  title: string;
  content: string;
  data?: Record<string, unknown>;
}

interface BusinessPlanData {
  business_name: string;
  district_name: string;
  industry_name: string;
  sections: PlanSection[];
  generated_at: string;
}

type Stage = "confirm" | "loading" | "preview";

interface LoadingStep {
  label: string;
  done: boolean;
}

// ============================================================================
// Helpers
// ============================================================================

function formatMoney(val: number): string {
  if (val >= 10000) return `${(val / 10000).toFixed(1)}억`;
  if (val >= 1000) return `${(val / 1000).toFixed(1)}천만`;
  return `${val.toLocaleString()}만`;
}

// ============================================================================
// Markdown → HTML (simple converter for generated content)
// ============================================================================

function markdownToHtml(md: string): string {
  let html = md;

  html = html
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  html = html.replace(/^&gt;\s?(.*)$/gm, "<blockquote>$1</blockquote>");
  html = html.replace(/<\/blockquote>\n<blockquote>/g, "<br/>");

  // Tables
  html = html.replace(
    /^\|(.+)\|\s*\n\|[-| :]+\|\s*\n((?:\|.+\|\s*\n?)*)/gm,
    (_match, headerRow: string, bodyRows: string) => {
      const headers = headerRow.split("|").map((h: string) => h.trim()).filter(Boolean);
      const thRow = headers.map((h: string) => `<th>${h}</th>`).join("");
      const rows = bodyRows.trim().split("\n").map((row: string) => {
        const cells = row.split("|").map((c: string) => c.trim()).filter(Boolean);
        return `<tr>${cells.map((c: string) => `<td>${c}</td>`).join("")}</tr>`;
      }).join("");
      return `<div class="table-wrap"><table><thead><tr>${thRow}</tr></thead><tbody>${rows}</tbody></table></div>`;
    },
  );

  html = html.replace(/^#### (.+)$/gm, '<h4 class="bp-h4">$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3 class="bp-h3">$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2 class="bp-h2">$1</h2>');

  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  html = html.replace(/^(\d+)\.\s+(.+)$/gm, '<li class="bp-oli">$2</li>');
  html = html.replace(/((?:<li class="bp-oli">.*<\/li>\n?)+)/g, '<ol class="bp-ol">$1</ol>');

  html = html.replace(/^- (.+)$/gm, '<li class="bp-uli">$1</li>');
  html = html.replace(/((?:<li class="bp-uli">.*<\/li>\n?)+)/g, '<ul class="bp-ul">$1</ul>');

  html = html
    .split("\n\n")
    .map((block) => {
      const trimmed = block.trim();
      if (!trimmed) return "";
      if (trimmed.startsWith("<") || trimmed.startsWith("#")) return trimmed;
      return `<p>${trimmed.replace(/\n/g, "<br/>")}</p>`;
    })
    .join("\n");

  return html;
}

// ============================================================================
// Data-driven visual components
// ============================================================================

/** KPI hero card */
function KpiCard({
  icon,
  label,
  value,
  sub,
  accent = "blue",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  accent?: "blue" | "emerald" | "amber" | "violet" | "red";
}) {
  const colorMap = {
    blue: "from-blue-500 to-blue-600 shadow-blue-200",
    emerald: "from-emerald-500 to-emerald-600 shadow-emerald-200",
    amber: "from-amber-500 to-amber-600 shadow-amber-200",
    violet: "from-violet-500 to-violet-600 shadow-violet-200",
    red: "from-red-500 to-red-600 shadow-red-200",
  };
  return (
    <div className={cn(
      "relative overflow-hidden rounded-2xl bg-gradient-to-br text-white p-5 shadow-lg",
      colorMap[accent],
    )}>
      <div className="absolute top-3 right-3 opacity-20 text-3xl">{icon}</div>
      <p className="text-xs font-medium opacity-80 mb-1">{label}</p>
      <p className="text-2xl font-extrabold tracking-tight">{value}</p>
      {sub && <p className="text-xs opacity-70 mt-1">{sub}</p>}
    </div>
  );
}

/** Score gauge (circular) */
function ScoreGauge({ score, maxScore = 100, label }: { score: number; maxScore?: number; label?: string }) {
  const pct = Math.min(score / maxScore, 1);
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - pct);
  const color = pct >= 0.7 ? "#10B981" : pct >= 0.4 ? "#F59E0B" : "#EF4444";

  return (
    <div className="flex flex-col items-center">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r={radius} fill="none" stroke="#E2E8F0" strokeWidth="10" />
        <circle
          cx="70" cy="70" r={radius} fill="none"
          stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          transform="rotate(-90 70 70)"
          className="transition-all duration-1000"
        />
        <text x="70" y="65" textAnchor="middle" className="text-3xl font-extrabold" fill="#1E293B" fontSize="28" fontWeight="800">
          {score}
        </text>
        <text x="70" y="85" textAnchor="middle" fill="#94A3B8" fontSize="11">
          / {maxScore}점
        </text>
      </svg>
      {label && <p className="text-sm font-semibold text-slate-700 mt-2">{label}</p>}
    </div>
  );
}

/** Budget warning banner */
function BudgetWarningBanner({ budgetMan, startupMin }: { budgetMan: number; startupMin: number }) {
  const gap = startupMin - budgetMan;
  if (gap <= 0) return null;
  return (
    <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl p-4 mb-4">
      <AlertTriangle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-bold text-red-800">예산 초과 경고</p>
        <p className="text-xs text-red-600 mt-0.5">
          예상 초기 투자비가 예산보다 <strong>{formatMoney(gap)}원</strong> 부족합니다.
          추가 자금 확보 또는 비용 절감 방안을 검토하세요.
        </p>
      </div>
    </div>
  );
}

/** Financials section: KPI cards + donut chart + 3-year projection */
function FinancialsVisual({ data }: { data: Record<string, unknown> }) {
  const monthlyRev = Number(data.monthly_revenue || 0);
  const monthlyOpCost = Number(data.monthly_operating_cost || 0);
  const monthlyNet = Number(data.monthly_net_profit || 0);
  const startupMin = Number(data.startup_total_min || 0);
  const startupMax = Number(data.startup_total_max || 0);
  const beMin = Number(data.break_even_months_min || 0);
  const beMax = Number(data.break_even_months_max || 0);
  const budgetMan = Number(data.budget_man || 0);
  const budgetOk = Boolean(data.budget_ok);

  // Operating cost breakdown for donut (simulated proportions)
  const rent = monthlyOpCost * 0.35;
  const labor = monthlyOpCost * 0.28;
  const material = monthlyOpCost * 0.22;
  const misc = monthlyOpCost * 0.15;

  const donutData = [
    { name: "임대료", value: Math.round(rent) },
    { name: "인건비", value: Math.round(labor) },
    { name: "재료비", value: Math.round(material) },
    { name: "기타", value: Math.round(misc) },
  ];

  // 3-year projection line chart
  const projectionData = [
    { month: "현재", revenue: monthlyRev, cost: monthlyOpCost, profit: monthlyNet },
    { month: "6개월", revenue: Math.round(monthlyRev * 1.05), cost: monthlyOpCost, profit: Math.round(monthlyRev * 1.05 - monthlyOpCost) },
    { month: "1년", revenue: Math.round(monthlyRev * 1.12), cost: Math.round(monthlyOpCost * 1.02), profit: Math.round(monthlyRev * 1.12 - monthlyOpCost * 1.02) },
    { month: "2년", revenue: Math.round(monthlyRev * 1.2), cost: Math.round(monthlyOpCost * 1.05), profit: Math.round(monthlyRev * 1.2 - monthlyOpCost * 1.05) },
    { month: "3년", revenue: Math.round(monthlyRev * 1.3), cost: Math.round(monthlyOpCost * 1.08), profit: Math.round(monthlyRev * 1.3 - monthlyOpCost * 1.08) },
  ];

  return (
    <div className="space-y-6">
      {/* Budget warning */}
      {!budgetOk && <BudgetWarningBanner budgetMan={budgetMan} startupMin={startupMin} />}

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          icon={<DollarSign className="w-6 h-6" />}
          label="월 예상 매출"
          value={`${formatMoney(monthlyRev)}원`}
          accent="blue"
        />
        <KpiCard
          icon={<TrendingUp className="w-6 h-6" />}
          label="월 순이익"
          value={`${formatMoney(monthlyNet)}원`}
          sub={monthlyRev > 0 ? `마진율 ${((monthlyNet / monthlyRev) * 100).toFixed(0)}%` : undefined}
          accent={monthlyNet > 0 ? "emerald" : "red"}
        />
        <KpiCard
          icon={<BarChart3 className="w-6 h-6" />}
          label="초기 투자비"
          value={`${formatMoney(startupMin)}~${formatMoney(startupMax)}원`}
          accent="violet"
        />
        <KpiCard
          icon={<Clock className="w-6 h-6" />}
          label="투자 회수"
          value={`${beMin}~${beMax}개월`}
          sub="손익분기 도달"
          accent="amber"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Donut chart */}
        <div className="bg-slate-50 rounded-2xl border border-slate-200 p-5">
          <h4 className="text-sm font-bold text-slate-700 mb-4">월 운영비 구성</h4>
          <div className="flex items-center justify-center gap-4">
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie
                  data={donutData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  paddingAngle={3}
                  dataKey="value"
                  stroke="none"
                >
                  {donutData.map((_, idx) => (
                    <Cell key={idx} fill={DONUT_COLORS[idx % DONUT_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(val: number) => `${formatMoney(val)}원`} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-2">
              {donutData.map((d, idx) => (
                <div key={d.name} className="flex items-center gap-2 text-xs">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: DONUT_COLORS[idx] }} />
                  <span className="text-slate-600">{d.name}</span>
                  <span className="font-semibold text-slate-800 ml-auto">{formatMoney(d.value)}원</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Line chart: 3-year projection */}
        <div className="bg-slate-50 rounded-2xl border border-slate-200 p-5">
          <h4 className="text-sm font-bold text-slate-700 mb-4">3년 매출·비용 전망</h4>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={projectionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${formatMoney(v)}`} />
              <Tooltip formatter={(val: number) => `${formatMoney(val)}원`} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="revenue" name="매출" stroke="#3B82F6" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="cost" name="비용" stroke="#F59E0B" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="profit" name="순이익" stroke="#10B981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

/** Risk/verdict section: radar + score gauge */
function RiskVisual({ data }: { data: Record<string, unknown> }) {
  const riskLevel = String(data.risk_level || "보통");
  const riskScore = Number(data.risk_score || 50);
  const survivalRate = Number(data.survival_rate || 0);
  const scorecardTotal = Number(data.scorecard_total || 0);

  // Radar chart data (5 categories)
  const radarData = [
    { category: "상권", value: Math.min(Math.round(survivalRate), 100) },
    { category: "경쟁력", value: Math.min(100 - riskScore, 100) },
    { category: "수익성", value: Math.round(scorecardTotal * 1.2) || 60 },
    { category: "안정성", value: Math.round(survivalRate * 0.9) || 50 },
    { category: "성장성", value: Math.round((100 - riskScore) * 0.8) || 55 },
  ];

  const verdictColor = riskLevel === "낮음" || riskLevel === "안전"
    ? "emerald" : riskLevel === "높음" || riskLevel === "위험"
    ? "red" : "amber";

  const verdictColorMap = {
    emerald: { bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-700", badge: "bg-emerald-500" },
    amber: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", badge: "bg-amber-500" },
    red: { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", badge: "bg-red-500" },
  };
  const vc = verdictColorMap[verdictColor];

  return (
    <div className="space-y-6">
      {/* Verdict banner */}
      <div className={cn("flex items-center gap-4 rounded-2xl p-5 border", vc.bg, vc.border)}>
        <span className={cn("shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm", vc.badge)}>
          {riskLevel.charAt(0)}
        </span>
        <div>
          <p className={cn("text-base font-bold", vc.text)}>종합 리스크 판정: {riskLevel}</p>
          <p className="text-xs text-slate-500 mt-0.5">생존율 {survivalRate}% · 리스크 점수 {riskScore}점</p>
        </div>
      </div>

      {/* Gauge + Radar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="flex flex-col items-center justify-center bg-slate-50 rounded-2xl border border-slate-200 py-6">
          <ScoreGauge score={scorecardTotal || Math.round(100 - riskScore)} label="종합 점수" />
        </div>
        <div className="bg-slate-50 rounded-2xl border border-slate-200 p-4">
          <h4 className="text-sm font-bold text-slate-700 mb-2 text-center">5대 카테고리 분석</h4>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#CBD5E1" />
              <PolarAngleAxis dataKey="category" tick={{ fontSize: 11, fill: "#475569" }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 9 }} />
              <Radar name="점수" dataKey="value" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.2} strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

/** Market section KPI strip */
function MarketVisual({ data }: { data: Record<string, unknown> }) {
  const footTraffic = Number(data.foot_traffic || 0);
  const residentTotal = Number(data.resident_total || 0);
  const workerTotal = Number(data.worker_total || 0);
  const peakTime = String(data.peak_time || "-");
  const mainAgeGroup = String(data.main_age_group || "-");

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
      <MiniStat icon={<Users className="w-4 h-4" />} label="유동인구" value={footTraffic.toLocaleString()} unit="명/일" />
      <MiniStat icon={<Users className="w-4 h-4" />} label="거주인구" value={residentTotal.toLocaleString()} unit="명" />
      <MiniStat icon={<Users className="w-4 h-4" />} label="직장인구" value={workerTotal.toLocaleString()} unit="명" />
      <MiniStat icon={<Clock className="w-4 h-4" />} label="피크 시간" value={peakTime} />
      <MiniStat icon={<Target className="w-4 h-4" />} label="주요 연령대" value={mainAgeGroup} />
    </div>
  );
}

/** Competition section KPI strip */
function CompetitionVisual({ data }: { data: Record<string, unknown> }) {
  const storeCount = Number(data.store_count || 0);
  const franchiseRatio = Number(data.franchise_ratio || 0);
  const newStores = Number(data.new_stores || 0);
  const closedStores = Number(data.closed_stores || 0);
  const survivalRate = Number(data.survival_rate || 0);

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-4">
      <MiniStat icon={<Store className="w-4 h-4" />} label="매장 수" value={String(storeCount)} unit="개" />
      <MiniStat icon={<BarChart3 className="w-4 h-4" />} label="프랜차이즈 비율" value={`${franchiseRatio}%`} />
      <MiniStat icon={<TrendingUp className="w-4 h-4" />} label="신규 개점" value={String(newStores)} unit="개" color="emerald" />
      <MiniStat icon={<AlertTriangle className="w-4 h-4" />} label="폐점" value={String(closedStores)} unit="개" color="red" />
      <MiniStat icon={<Shield className="w-4 h-4" />} label="생존율" value={`${survivalRate}%`} color={survivalRate >= 60 ? "emerald" : "amber"} />
    </div>
  );
}

function MiniStat({
  icon,
  label,
  value,
  unit,
  color = "blue",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit?: string;
  color?: "blue" | "emerald" | "amber" | "red";
}) {
  const colorMap = {
    blue: "text-blue-600 bg-blue-50",
    emerald: "text-emerald-600 bg-emerald-50",
    amber: "text-amber-600 bg-amber-50",
    red: "text-red-600 bg-red-50",
  };
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-3 flex flex-col gap-1">
      <div className="flex items-center gap-1.5">
        <span className={cn("w-6 h-6 rounded-md flex items-center justify-center", colorMap[color])}>
          {icon}
        </span>
        <span className="text-[10px] text-slate-500 font-medium">{label}</span>
      </div>
      <p className="text-lg font-bold text-slate-800 leading-tight">
        {value}
        {unit && <span className="text-xs font-normal text-slate-400 ml-0.5">{unit}</span>}
      </p>
    </div>
  );
}

/** Roadmap timeline */
function RoadmapTimeline({ data }: { data: Record<string, unknown> }) {
  const phases = (data.phases as string[]) || ["준비기", "시공기", "오픈 준비", "안정화"];
  const totalDays = Number(data.total_days || 90);
  const daysPerPhase = Math.round(totalDays / phases.length);

  const phaseColors = ["#3B82F6", "#8B5CF6", "#F59E0B", "#10B981"];
  const phaseIcons = ["📋", "🔨", "🎯", "📈"];

  return (
    <div className="relative mb-4">
      <div className="flex flex-col gap-0">
        {phases.map((phase, i) => (
          <div key={i} className="flex gap-4">
            {/* Timeline bar */}
            <div className="flex flex-col items-center">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0 shadow-md"
                style={{ backgroundColor: phaseColors[i % phaseColors.length] }}
              >
                {phaseIcons[i] || (i + 1)}
              </div>
              {i < phases.length - 1 && (
                <div className="w-0.5 h-16 bg-gradient-to-b from-slate-300 to-slate-200" />
              )}
            </div>
            {/* Card */}
            <div className="flex-1 pb-6">
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm hover:shadow-md transition-shadow">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="text-xs font-bold px-2 py-0.5 rounded-full text-white"
                    style={{ backgroundColor: phaseColors[i % phaseColors.length] }}
                  >
                    Phase {i + 1}
                  </span>
                  <span className="text-xs text-slate-400">{daysPerPhase}일</span>
                </div>
                <p className="font-semibold text-slate-800">{phase}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2 text-center text-xs text-slate-400">
        총 {totalDays}일 계획
      </div>
    </div>
  );
}

// ============================================================================
// Components
// ============================================================================

function ConfirmScreen({
  industryCode,
  districtName,
  industryName,
  budget,
  areaPyeong,
  onGenerate,
}: {
  industryCode: string;
  districtName: string;
  industryName: string;
  budget: number;
  areaPyeong: number;
  onGenerate: (businessName: string) => void;
}) {
  const [businessName, setBusinessName] = useState("");
  const icon = INDUSTRY_ICONS[industryCode] || "🏪";

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-8 text-white text-center">
            <div className="text-4xl mb-3">{icon}</div>
            <h1 className="text-xl font-bold">AI 사업계획서</h1>
            <p className="text-blue-100 text-sm mt-1">입력 정보를 확인하고 생성하세요</p>
          </div>

          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <InfoCard label="업종" value={`${icon} ${industryName}`} />
              <InfoCard label="상권" value={districtName} />
              <InfoCard label="총 예산" value={`${budget.toLocaleString()}만원`} />
              <InfoCard label="매장 면적" value={`${areaPyeong}평`} />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                상호명 (선택)
              </label>
              <input
                type="text"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                placeholder="예) 카페 모닝글로우"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              />
            </div>

            <button
              onClick={() => onGenerate(businessName)}
              className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold text-lg hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg active:scale-[0.98]"
            >
              사업계획서 생성하기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-50 rounded-xl px-4 py-3 border border-slate-100">
      <div className="text-xs text-slate-500 mb-0.5">{label}</div>
      <div className="text-sm font-semibold text-slate-800 truncate">{value}</div>
    </div>
  );
}

function LoadingScreen({ steps }: { steps: LoadingStep[] }) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-50 rounded-2xl mb-4">
              <FileText className="w-8 h-8 text-blue-600" />
            </div>
            <h2 className="text-lg font-bold text-slate-800">사업계획서 생성 중</h2>
            <p className="text-sm text-slate-500 mt-1">잠시만 기다려주세요...</p>
          </div>

          <div className="space-y-3">
            {steps.map((step, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-500",
                  step.done
                    ? "bg-emerald-50 border border-emerald-100"
                    : i === steps.findIndex((s) => !s.done)
                    ? "bg-blue-50 border border-blue-100"
                    : "bg-slate-50 border border-slate-100",
                )}
              >
                {step.done ? (
                  <CheckCircle className="w-5 h-5 text-emerald-500 shrink-0" />
                ) : i === steps.findIndex((s) => !s.done) ? (
                  <Loader2 className="w-5 h-5 text-blue-500 animate-spin shrink-0" />
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-slate-200 shrink-0" />
                )}
                <span
                  className={cn(
                    "text-sm font-medium",
                    step.done ? "text-emerald-700" : i === steps.findIndex((s) => !s.done) ? "text-blue-700" : "text-slate-400",
                  )}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-6 h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-700"
              style={{
                width: `${(steps.filter((s) => s.done).length / steps.length) * 100}%`,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function PreviewScreen({
  plan,
  onRegenerate,
}: {
  plan: BusinessPlanData;
  onRegenerate: () => void;
}) {
  const [activeSection, setActiveSection] = useState(0);
  const sectionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  };

  const scrollToSection = (idx: number) => {
    setActiveSection(idx);
    sectionRefs.current[idx]?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const idx = sectionRefs.current.findIndex((ref) => ref === entry.target);
            if (idx >= 0) setActiveSection(idx);
          }
        }
      },
      { rootMargin: "-20% 0px -60% 0px" },
    );

    sectionRefs.current.forEach((ref) => {
      if (ref) observer.observe(ref);
    });

    return () => observer.disconnect();
  }, [plan]);

  /** Render data-driven visuals above markdown content per section */
  const renderSectionVisuals = (sec: PlanSection) => {
    if (!sec.data) return null;
    const d = sec.data;

    switch (sec.id) {
      case "financials":
        return <FinancialsVisual data={d} />;
      case "risk":
        return <RiskVisual data={d} />;
      case "market":
        return <MarketVisual data={d} />;
      case "competition":
        return <CompetitionVisual data={d} />;
      case "roadmap":
        return <RoadmapTimeline data={d} />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-slate-800 text-white px-6 py-3 rounded-xl shadow-lg text-sm animate-fade-in">
          {toast}
        </div>
      )}

      {/* Header */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center">
              <FileText className="w-4.5 h-4.5 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-800">{plan.business_name}</h1>
              <p className="text-xs text-slate-500">
                {plan.industry_name} · {plan.district_name}
              </p>
            </div>
          </div>
          <div className="text-xs text-slate-400">
            {new Date(plan.generated_at).toLocaleDateString("ko-KR")} 생성
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto flex">
        {/* Sidebar */}
        <aside className="hidden lg:block w-64 shrink-0 sticky top-14 h-[calc(100vh-3.5rem)] overflow-y-auto border-r border-slate-200 bg-white">
          <nav className="p-4 space-y-1">
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-3">
              목차
            </div>
            {plan.sections.map((sec, i) => (
              <button
                key={sec.id}
                onClick={() => scrollToSection(i)}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left transition-all text-sm",
                  activeSection === i
                    ? "bg-blue-50 text-blue-700 font-semibold border-l-2 border-blue-500"
                    : "text-slate-600 hover:bg-slate-50",
                )}
              >
                <span className="text-[10px] font-mono text-slate-400 w-5">{SECTION_NUMBERS[sec.id] || `0${i + 1}`}</span>
                <span className="shrink-0">{SECTION_ICONS[sec.id] || <ChevronRight className="w-4 h-4" />}</span>
                <span className="truncate">{sec.title.replace(/^\d+\.\s*/, "")}</span>
              </button>
            ))}
          </nav>
        </aside>

        {/* Mobile Section Navigation */}
        <div className="lg:hidden sticky top-14 z-30 bg-white border-b border-slate-200 overflow-x-auto">
          <div className="flex gap-1 p-2 min-w-max">
            {plan.sections.map((sec, i) => (
              <button
                key={sec.id}
                onClick={() => scrollToSection(i)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs whitespace-nowrap transition",
                  activeSection === i
                    ? "bg-blue-50 text-blue-700 font-semibold"
                    : "text-slate-500 hover:bg-slate-50",
                )}
              >
                {SECTION_ICONS[sec.id]}
                <span>{sec.title.replace(/^\d+\.\s*/, "")}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <main className="flex-1 min-w-0 px-4 lg:px-8 py-8 space-y-6">
          {plan.sections.map((sec, i) => (
            <div
              key={sec.id}
              ref={(el) => { sectionRefs.current[i] = el; }}
              className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden"
            >
              {/* Section header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono font-bold text-slate-400">{SECTION_NUMBERS[sec.id] || `0${i + 1}`}</span>
                  <span className="text-blue-600">{SECTION_ICONS[sec.id]}</span>
                  <h2 className="font-bold text-slate-800">{sec.title}</h2>
                </div>
                <button
                  onClick={() => showToast("향후 AI 수정 기능 지원 예정입니다")}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                >
                  <Pencil className="w-3.5 h-3.5" />
                  수정
                </button>
              </div>

              {/* Data-driven visual */}
              <div className="px-6 pt-6">
                {renderSectionVisuals(sec)}
              </div>

              {/* Markdown content */}
              <div
                className="bp-content px-6 py-6"
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(markdownToHtml(sec.content), {
                    ALLOWED_TAGS: [
                      "h2", "h3", "h4", "p", "br", "strong", "em",
                      "table", "thead", "tbody", "tr", "th", "td",
                      "ul", "ol", "li", "blockquote", "div", "span",
                    ],
                    ALLOWED_ATTR: ["class"],
                  }),
                }}
              />
            </div>
          ))}

          {/* Bottom CTA */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4 pb-12">
            <button
              onClick={onRegenerate}
              className="flex items-center justify-center gap-2 px-6 py-3.5 bg-white border border-slate-200 rounded-xl text-slate-700 font-medium hover:bg-slate-50 transition shadow-sm"
            >
              <RefreshCw className="w-4 h-4" />
              조건 바꿔서 다시 생성
            </button>
          </div>
        </main>
      </div>

      {/* Inline styles for business-plan content */}
      <style jsx global>{`
        .bp-content .bp-h2 {
          display: none;
        }
        .bp-content .bp-h3 {
          font-size: 1rem;
          font-weight: 700;
          color: #1e293b;
          margin: 1.5rem 0 0.75rem 0;
          padding-bottom: 0.5rem;
          border-bottom: 2px solid #EEF2FF;
        }
        .bp-content .bp-h3::before {
          content: "▸ ";
          color: #3B82F6;
        }
        .bp-content .bp-h4 {
          font-size: 0.925rem;
          font-weight: 600;
          color: #334155;
          margin: 1.25rem 0 0.5rem 0;
        }
        .bp-content p {
          color: #475569;
          line-height: 1.8;
          margin: 0.5rem 0;
          font-size: 0.9rem;
        }
        .bp-content strong {
          color: #1e293b;
          font-weight: 700;
          background: linear-gradient(to bottom, transparent 60%, #DBEAFE 60%);
          padding: 0 2px;
        }
        .bp-content .table-wrap {
          overflow-x: auto;
          margin: 1rem 0;
          border-radius: 0.75rem;
          border: 1px solid #e2e8f0;
          box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .bp-content table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.85rem;
        }
        .bp-content th {
          background: linear-gradient(135deg, #F8FAFC, #EFF6FF);
          color: #1E40AF;
          font-weight: 700;
          text-align: left;
          padding: 0.75rem 1rem;
          border-bottom: 2px solid #BFDBFE;
          white-space: nowrap;
          font-size: 0.8rem;
          text-transform: uppercase;
          letter-spacing: 0.02em;
        }
        .bp-content td {
          padding: 0.625rem 1rem;
          border-bottom: 1px solid #f1f5f9;
          color: #334155;
        }
        .bp-content tr:nth-child(even) td {
          background: #F8FAFC;
        }
        .bp-content tr:last-child td {
          border-bottom: none;
        }
        .bp-content tr:hover td {
          background: #EFF6FF;
        }
        .bp-content .bp-ul, .bp-content .bp-ol {
          margin: 0.75rem 0;
          padding-left: 0;
        }
        .bp-content .bp-uli, .bp-content .bp-oli {
          color: #475569;
          font-size: 0.875rem;
          line-height: 1.8;
          margin: 0.375rem 0;
          padding: 0.25rem 0.5rem 0.25rem 1.75rem;
          position: relative;
          list-style: none;
        }
        .bp-content .bp-uli::before {
          content: "";
          position: absolute;
          left: 0.5rem;
          top: 0.75rem;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #3B82F6;
        }
        .bp-content .bp-oli {
          counter-increment: bp-counter;
        }
        .bp-content .bp-ol {
          counter-reset: bp-counter;
        }
        .bp-content .bp-oli::before {
          content: counter(bp-counter);
          position: absolute;
          left: 0.25rem;
          top: 0.25rem;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          background: #EEF2FF;
          color: #3B82F6;
          font-size: 0.7rem;
          font-weight: 700;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .bp-content blockquote {
          margin: 1rem 0;
          padding: 1rem 1.25rem;
          background: linear-gradient(135deg, #F0F9FF, #EFF6FF);
          border-left: 4px solid #3B82F6;
          border-radius: 0 0.75rem 0.75rem 0;
          color: #1E40AF;
          font-size: 0.875rem;
          font-weight: 500;
        }
        @keyframes fade-in {
          from { opacity: 0; transform: translate(-50%, -8px); }
          to { opacity: 1; transform: translate(-50%, 0); }
        }
        .animate-fade-in {
          animation: fade-in 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}

// ============================================================================
// Main Page (inner, uses useSearchParams)
// ============================================================================

function BusinessPlanPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const industryCode = searchParams?.get("industry_code") || "CS100010";
  const districtCode = searchParams?.get("district_code") || "";
  const budgetParam = parseInt(searchParams?.get("budget") || "0", 10);
  const areaParam = parseInt(searchParams?.get("area_pyeong") || "15", 10);
  const districtNameParam = searchParams?.get("district_name") || "";

  const [budget, setBudget] = useState(budgetParam || 8000);
  const [areaPyeong, setAreaPyeong] = useState(areaParam || 15);
  const [districtName, setDistrictName] = useState(districtNameParam || "");

  useEffect(() => {
    if (!budgetParam) {
      const stored = localStorage.getItem("builder_curation_onboarding_context");
      if (stored) {
        try {
          const ctx = JSON.parse(stored);
          if (ctx.budget) setBudget(ctx.budget);
          if (ctx.area_pyeong) setAreaPyeong(ctx.area_pyeong);
        } catch {}
      }
    }
    if (!districtNameParam) {
      setDistrictName(districtCode);
    }
  }, [budgetParam, districtNameParam, districtCode]);

  const industryName = INDUSTRY_NAMES[industryCode] || "카페";

  const [stage, setStage] = useState<Stage>("confirm");
  const [plan, setPlan] = useState<BusinessPlanData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [loadingSteps, setLoadingSteps] = useState<LoadingStep[]>([
    { label: "상권 데이터 수집", done: false },
    { label: "경쟁 분석", done: false },
    { label: "재무 시뮬레이션", done: false },
    { label: "분석 & 작성", done: false },
    { label: "완료", done: false },
  ]);

  const [lastBusinessName, setLastBusinessName] = useState("");

  const handleGenerate = async (businessName: string) => {
    setStage("loading");
    setError(null);
    setLastBusinessName(businessName);

    const steps = [
      { label: "데이터 수집 중...", done: false },
      { label: "AI 분석 중...", done: false },
      { label: "보고서 생성 중...", done: false },
      { label: "경쟁 분석", done: false },
      { label: "완료", done: false },
    ];
    setLoadingSteps([...steps]);

    const stepDelays = [800, 3000, 8000, 15000];
    const timers: ReturnType<typeof setTimeout>[] = [];
    for (let i = 0; i < stepDelays.length; i++) {
      timers.push(
        setTimeout(() => {
          setLoadingSteps((prev) =>
            prev.map((s, j) => (j <= i ? { ...s, done: true } : s)),
          );
        }, stepDelays[i]),
      );
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);

    try {
      const res = await fetch(`${API_BASE}/business-plan/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry_code: industryCode,
          district_code: districtCode,
          budget,
          area_pyeong: areaPyeong,
          business_name: businessName || undefined,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `서버 오류가 발생했습니다 (${res.status})`);
      }

      const data: BusinessPlanData = await res.json();
      setPlan(data);

      setLoadingSteps((prev) => prev.map((s) => ({ ...s, done: true })));

      setTimeout(() => setStage("preview"), 600);
    } catch (e: unknown) {
      timers.forEach(clearTimeout);
      clearTimeout(timeoutId);

      let msg: string;
      if (e instanceof DOMException && e.name === "AbortError") {
        msg = "요청 시간이 초과되었습니다. 네트워크 상태를 확인 후 다시 시도해주세요.";
      } else if (e instanceof TypeError && e.message === "Failed to fetch") {
        msg = "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.";
      } else {
        msg = e instanceof Error ? e.message : "알 수 없는 오류가 발생했습니다.";
      }
      setError(msg);
      setStage("confirm");
    }
  };

  const handleRetry = () => {
    if (lastBusinessName !== undefined) {
      handleGenerate(lastBusinessName);
    }
  };

  const handleRegenerate = () => {
    setPlan(null);
    setStage("confirm");
  };

  if (!districtCode) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 text-center max-w-sm">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h2 className="font-bold text-slate-800 mb-2">상권을 먼저 선택해주세요</h2>
          <p className="text-sm text-slate-500 mb-6">
            대시보드에서 상권을 선택한 후 사업계획서를 생성할 수 있습니다.
          </p>
          <button
            onClick={() => router.push("/results")}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition"
          >
            상권 탐색하기
          </button>
        </div>
      </div>
    );
  }

  if (stage === "loading") {
    return <LoadingScreen steps={loadingSteps} />;
  }

  if (stage === "preview" && plan) {
    return <PreviewScreen plan={plan} onRegenerate={handleRegenerate} />;
  }

  return (
    <>
      {error && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-red-600 text-white px-6 py-4 rounded-xl shadow-lg text-sm animate-fade-in max-w-md">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium mb-1">생성에 실패했습니다</p>
              <p className="text-red-100 text-xs">{error}</p>
            </div>
            <button
              onClick={handleRetry}
              className="shrink-0 flex items-center gap-1 px-3 py-1.5 bg-white/20 hover:bg-white/30 rounded-lg text-xs font-medium transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              다시 시도
            </button>
          </div>
        </div>
      )}
      <ConfirmScreen
        industryCode={industryCode}
        districtName={districtName || districtCode}
        industryName={industryName}
        budget={budget}
        areaPyeong={areaPyeong}
        onGenerate={handleGenerate}
      />
    </>
  );
}

// ============================================================================
// Page export (with Suspense for useSearchParams)
// ============================================================================

export default function BusinessPlanPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      }
    >
      <BusinessPlanPageInner />
    </Suspense>
  );
}
