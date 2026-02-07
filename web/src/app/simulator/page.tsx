"use client";

import { useState, useEffect, useMemo, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  SlidersHorizontal,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
  RotateCcw,
  FileText,
  ArrowLeft,
  Store,
  Users,
  ShoppingCart,
  Home,
  Percent,
} from "lucide-react";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from "recharts";
import { cn } from "@/lib/utils";
import { formatMoney } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE = "/api/v1";

const INDUSTRY_NAMES: Record<string, string> = {
  CS100001: "한식", CS100002: "중식", CS100003: "일식", CS100004: "양식",
  CS100005: "베이커리", CS100006: "패스트푸드", CS100007: "치킨",
  CS100008: "분식", CS100009: "호프/주점", CS100010: "카페",
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SimulatorDefaults {
  district_name: string;
  district_type: string;
  district_code: string;
  area_pyeong: number;
  avg_ticket: number;
  daily_visitors: number;
  cogs_ratio: number;
  monthly_rent: number;
  labor_count: number;
  startup_cost_min: number;
  startup_cost_max: number;
  baseline: Record<string, unknown>;
}

interface SliderConfig {
  key: string;
  label: string;
  icon: React.ReactNode;
  min: number;
  max: number;
  step: number;
  unit: string;
  format: (v: number) => string;
}

// ---------------------------------------------------------------------------
// Slider component
// ---------------------------------------------------------------------------

function SimSlider({
  config,
  value,
  defaultValue,
  onChange,
}: {
  config: SliderConfig;
  value: number;
  defaultValue: number;
  onChange: (v: number) => void;
}) {
  const pct = ((value - config.min) / (config.max - config.min)) * 100;
  const isChanged = value !== defaultValue;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
          {config.icon}
          {config.label}
        </div>
        <span
          className={cn(
            "text-sm font-semibold tabular-nums",
            isChanged ? "text-blue-600" : "text-gray-900"
          )}
        >
          {config.format(value)}
        </span>
      </div>
      <input
        type="range"
        min={config.min}
        max={config.max}
        step={config.step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        style={{
          background: `linear-gradient(to right, #2563eb 0%, #2563eb ${pct}%, #e5e7eb ${pct}%, #e5e7eb 100%)`,
        }}
      />
      <div className="flex justify-between text-xs text-gray-400">
        <span>{config.format(config.min)}</span>
        <span>{config.format(config.max)}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

function SimulatorContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const districtCode = searchParams?.get("district_code") || "";
  const industryCode = searchParams?.get("industry_code") || "CS100010";

  // Data fetching state
  const [defaults, setDefaults] = useState<SimulatorDefaults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Slider values
  const [areaPyeong, setAreaPyeong] = useState(10);
  const [avgTicket, setAvgTicket] = useState(5000);
  const [dailyVisitors, setDailyVisitors] = useState(100);
  const [cogsRatio, setCogsRatio] = useState(32);
  const [monthlyRent, setMonthlyRent] = useState(200);
  const [laborCount, setLaborCount] = useState(2);

  // Default values for reset
  const [defaultValues, setDefaultValues] = useState({
    areaPyeong: 10,
    avgTicket: 5000,
    dailyVisitors: 100,
    cogsRatio: 32,
    monthlyRent: 200,
    laborCount: 2,
  });

  // Fetch defaults
  useEffect(() => {
    if (!districtCode) {
      setError("상권 코드가 필요합니다");
      setLoading(false);
      return;
    }

    const fetchDefaults = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE}/simulation/${districtCode}/defaults?industry_code=${encodeURIComponent(industryCode)}`
        );
        if (!res.ok) throw new Error("데이터를 불러올 수 없습니다");
        const data: SimulatorDefaults = await res.json();
        setDefaults(data);

        // Set slider values from defaults
        const dv = {
          areaPyeong: data.area_pyeong || 10,
          avgTicket: data.avg_ticket || 5000,
          dailyVisitors: data.daily_visitors || 100,
          cogsRatio: Math.round((data.cogs_ratio || 0.32) * 100),
          monthlyRent: Math.round((data.monthly_rent || 2000000) / 10000),
          laborCount: data.labor_count || 2,
        };
        setDefaultValues(dv);
        setAreaPyeong(dv.areaPyeong);
        setAvgTicket(dv.avgTicket);
        setDailyVisitors(dv.dailyVisitors);
        setCogsRatio(dv.cogsRatio);
        setMonthlyRent(dv.monthlyRent);
        setLaborCount(dv.laborCount);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "알 수 없는 오류");
      } finally {
        setLoading(false);
      }
    };

    fetchDefaults();
  }, [districtCode, industryCode]);

  // Reset to defaults
  const handleReset = useCallback(() => {
    setAreaPyeong(defaultValues.areaPyeong);
    setAvgTicket(defaultValues.avgTicket);
    setDailyVisitors(defaultValues.dailyVisitors);
    setCogsRatio(defaultValues.cogsRatio);
    setMonthlyRent(defaultValues.monthlyRent);
    setLaborCount(defaultValues.laborCount);
  }, [defaultValues]);

  // Client-side calculations
  const results = useMemo(() => {
    const monthlyRevenue = avgTicket * dailyVisitors * 30;
    const cogs = Math.round(monthlyRevenue * (cogsRatio / 100));
    const labor = laborCount * 2_500_000;
    const rent = monthlyRent * 10_000;
    const utilities = Math.round(monthlyRevenue * 0.035);
    const other = Math.round(monthlyRevenue * 0.075);
    const operatingCost = rent + cogs + labor + utilities + other;
    const netProfit = monthlyRevenue - operatingCost;
    const netProfitMargin = monthlyRevenue > 0 ? netProfit / monthlyRevenue : 0;

    const startupMin = defaults?.startup_cost_min || 50_000_000;
    const startupMax = defaults?.startup_cost_max || 80_000_000;
    const startupAvg = Math.round((startupMin + startupMax) / 2);

    const breakEvenMonths =
      netProfit > 0 ? Math.ceil(startupAvg / netProfit) : 999;

    // 12-month cumulative P&L chart data
    const chartData = Array.from({ length: 13 }, (_, i) => {
      const cumProfit = netProfit * i - startupAvg;
      return {
        month: i === 0 ? "초기" : `${i}월`,
        cumulative: cumProfit,
        label: cumProfit >= 0 ? "흑자" : "적자",
      };
    });

    return {
      monthlyRevenue,
      cogs,
      labor,
      rent,
      utilities,
      other,
      operatingCost,
      netProfit,
      netProfitMargin,
      startupAvg,
      breakEvenMonths,
      chartData,
    };
  }, [avgTicket, dailyVisitors, cogsRatio, monthlyRent, laborCount, defaults]);

  // Slider configurations
  const sliders: SliderConfig[] = [
    {
      key: "areaPyeong",
      label: "매장 규모",
      icon: <Store className="w-4 h-4" />,
      min: 5,
      max: 30,
      step: 1,
      unit: "평",
      format: (v) => `${v}평`,
    },
    {
      key: "avgTicket",
      label: "객단가",
      icon: <ShoppingCart className="w-4 h-4" />,
      min: 3000,
      max: 15000,
      step: 500,
      unit: "원",
      format: (v) => `${v.toLocaleString()}원`,
    },
    {
      key: "dailyVisitors",
      label: "일 방문객",
      icon: <Users className="w-4 h-4" />,
      min: 20,
      max: 300,
      step: 5,
      unit: "명",
      format: (v) => `${v}명`,
    },
    {
      key: "cogsRatio",
      label: "원가율",
      icon: <Percent className="w-4 h-4" />,
      min: 20,
      max: 50,
      step: 1,
      unit: "%",
      format: (v) => `${v}%`,
    },
    {
      key: "monthlyRent",
      label: "월 임대료",
      icon: <Home className="w-4 h-4" />,
      min: 50,
      max: 1000,
      step: 10,
      unit: "만원",
      format: (v) => `${v}만원`,
    },
    {
      key: "laborCount",
      label: "직원 수",
      icon: <Users className="w-4 h-4" />,
      min: 0,
      max: 8,
      step: 1,
      unit: "명",
      format: (v) => `${v}명`,
    },
  ];

  const sliderValues: Record<string, number> = {
    areaPyeong,
    avgTicket,
    dailyVisitors,
    cogsRatio,
    monthlyRent,
    laborCount,
  };

  const sliderSetters: Record<string, (v: number) => void> = {
    areaPyeong: setAreaPyeong,
    avgTicket: setAvgTicket,
    dailyVisitors: setDailyVisitors,
    cogsRatio: setCogsRatio,
    monthlyRent: setMonthlyRent,
    laborCount: setLaborCount,
  };

  // Check if any slider is changed from default
  const isChanged =
    areaPyeong !== defaultValues.areaPyeong ||
    avgTicket !== defaultValues.avgTicket ||
    dailyVisitors !== defaultValues.dailyVisitors ||
    cogsRatio !== defaultValues.cogsRatio ||
    monthlyRent !== defaultValues.monthlyRent ||
    laborCount !== defaultValues.laborCount;

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-gray-500 text-sm">시뮬레이션 데이터 로딩 중...</p>
        </div>
      </div>
    );
  }

  if (error || !defaults) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center space-y-4 p-6">
          <p className="text-red-500 font-medium">{error || "데이터를 불러올 수 없습니다"}</p>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-gray-100 rounded-lg text-gray-700 hover:bg-gray-200 transition-colors"
          >
            돌아가기
          </button>
        </div>
      </div>
    );
  }

  const industryName = INDUSTRY_NAMES[industryCode] || "외식업";

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-30 bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <SlidersHorizontal className="w-5 h-5 text-blue-600" />
                What-if 시뮬레이터
              </h1>
              <p className="text-xs text-gray-500">
                {defaults.district_name} &middot; {defaults.district_type} &middot; {industryName}
              </p>
            </div>
          </div>
          {isChanged && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              기본값으로 리셋
            </button>
          )}
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Sliders */}
          <div className="lg:col-span-4 space-y-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-5 shadow-sm">
              <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-blue-600" />
                조건 설정
              </h2>
              {sliders.map((config) => (
                <SimSlider
                  key={config.key}
                  config={config}
                  value={sliderValues[config.key]}
                  defaultValue={defaultValues[config.key as keyof typeof defaultValues]}
                  onChange={sliderSetters[config.key]}
                />
              ))}
            </div>
          </div>

          {/* Right: Results */}
          <div className="lg:col-span-8 space-y-4">
            {/* Key metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <MetricCard
                label="월 매출"
                value={formatMoney(results.monthlyRevenue)}
                icon={<DollarSign className="w-4 h-4" />}
                color="blue"
              />
              <MetricCard
                label="월 운영비"
                value={formatMoney(results.operatingCost)}
                icon={<TrendingDown className="w-4 h-4" />}
                color="gray"
              />
              <MetricCard
                label="월 순이익"
                value={formatMoney(Math.abs(results.netProfit))}
                prefix={results.netProfit >= 0 ? "+" : "-"}
                icon={
                  results.netProfit >= 0 ? (
                    <TrendingUp className="w-4 h-4" />
                  ) : (
                    <TrendingDown className="w-4 h-4" />
                  )
                }
                color={results.netProfit >= 0 ? "green" : "red"}
              />
              <MetricCard
                label="순이익률"
                value={`${(results.netProfitMargin * 100).toFixed(1)}%`}
                icon={<Percent className="w-4 h-4" />}
                color={results.netProfitMargin >= 0 ? "green" : "red"}
              />
              <MetricCard
                label="초기 투자비"
                value={formatMoney(results.startupAvg)}
                icon={<Store className="w-4 h-4" />}
                color="purple"
              />
              <MetricCard
                label="투자회수"
                value={
                  results.breakEvenMonths >= 999
                    ? "회수불가"
                    : `${results.breakEvenMonths}개월`
                }
                icon={<Clock className="w-4 h-4" />}
                color={
                  results.breakEvenMonths >= 999
                    ? "red"
                    : results.breakEvenMonths <= 24
                    ? "green"
                    : "amber"
                }
              />
            </div>

            {/* Operating cost breakdown */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <h3 className="font-semibold text-gray-900 mb-4">월 운영비 내역</h3>
              <div className="space-y-2">
                <CostBar label="임대료" value={results.rent} total={results.operatingCost} color="bg-blue-500" />
                <CostBar label="원재료비" value={results.cogs} total={results.operatingCost} color="bg-amber-500" />
                <CostBar label="인건비" value={results.labor} total={results.operatingCost} color="bg-purple-500" />
                <CostBar label="공과금" value={results.utilities} total={results.operatingCost} color="bg-teal-500" />
                <CostBar label="기타" value={results.other} total={results.operatingCost} color="bg-gray-400" />
              </div>
            </div>

            {/* 12-month cumulative P&L chart */}
            <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
              <h3 className="font-semibold text-gray-900 mb-4">
                12개월 누적 손익 추이
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={results.chartData}>
                    <defs>
                      <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#22c55e" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="lossGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ef4444" stopOpacity={0} />
                        <stop offset="100%" stopColor="#ef4444" stopOpacity={0.3} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="month"
                      tick={{ fontSize: 12, fill: "#9ca3af" }}
                      axisLine={{ stroke: "#e5e7eb" }}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "#9ca3af" }}
                      axisLine={{ stroke: "#e5e7eb" }}
                      tickFormatter={(v) => {
                        if (Math.abs(v) >= 100_000_000)
                          return `${(v / 100_000_000).toFixed(1)}억`;
                        return `${Math.round(v / 10_000).toLocaleString()}만`;
                      }}
                    />
                    <Tooltip
                      formatter={(value: number) => [formatMoney(Math.abs(value)), value >= 0 ? "누적 이익" : "누적 손실"]}
                      labelStyle={{ fontWeight: 600 }}
                      contentStyle={{
                        borderRadius: "8px",
                        border: "1px solid #e5e7eb",
                        fontSize: "13px",
                      }}
                    />
                    <ReferenceLine y={0} stroke="#6b7280" strokeWidth={1.5} />
                    <Area
                      type="monotone"
                      dataKey="cumulative"
                      stroke={results.netProfit >= 0 ? "#22c55e" : "#ef4444"}
                      strokeWidth={2.5}
                      fill={results.netProfit >= 0 ? "url(#profitGrad)" : "url(#lossGrad)"}
                      dot={{ r: 3, fill: "#fff", strokeWidth: 2 }}
                      activeDot={{ r: 5 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              {results.breakEvenMonths < 13 && results.breakEvenMonths < 999 && (
                <p className="text-center text-sm text-green-600 mt-2 font-medium">
                  약 {results.breakEvenMonths}개월차에 투자금 회수 예상
                </p>
              )}
            </div>

            {/* CTA */}
            <div className="flex gap-3">
              <button
                onClick={() => {
                  const params = new URLSearchParams({
                    district_code: districtCode,
                    industry_code: industryCode,
                    area_pyeong: String(areaPyeong),
                    avg_ticket: String(avgTicket),
                    daily_visitors: String(dailyVisitors),
                    cogs_ratio: String(cogsRatio),
                    monthly_rent: String(monthlyRent),
                    labor_count: String(laborCount),
                  });
                  router.push(`/business-plan?${params.toString()}`);
                }}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors shadow-sm"
              >
                <FileText className="w-5 h-5" />
                이 조건으로 사업계획서 만들기
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

const COLOR_MAP: Record<string, { bg: string; text: string; iconBg: string }> = {
  blue: { bg: "bg-blue-50", text: "text-blue-700", iconBg: "bg-blue-100" },
  green: { bg: "bg-green-50", text: "text-green-700", iconBg: "bg-green-100" },
  red: { bg: "bg-red-50", text: "text-red-700", iconBg: "bg-red-100" },
  amber: { bg: "bg-amber-50", text: "text-amber-700", iconBg: "bg-amber-100" },
  gray: { bg: "bg-gray-50", text: "text-gray-700", iconBg: "bg-gray-100" },
  purple: { bg: "bg-purple-50", text: "text-purple-700", iconBg: "bg-purple-100" },
};

function MetricCard({
  label,
  value,
  prefix,
  icon,
  color,
}: {
  label: string;
  value: string;
  prefix?: string;
  icon: React.ReactNode;
  color: string;
}) {
  const c = COLOR_MAP[color] || COLOR_MAP.gray;
  return (
    <div className={cn("rounded-xl border p-4 space-y-1", c.bg, "border-transparent")}>
      <div className="flex items-center gap-1.5 text-xs text-gray-500">
        <span className={cn("p-1 rounded-md", c.iconBg, c.text)}>{icon}</span>
        {label}
      </div>
      <p className={cn("text-lg font-bold tabular-nums", c.text)}>
        {prefix}
        {value}
      </p>
    </div>
  );
}

function CostBar({
  label,
  value,
  total,
  color,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="w-16 text-sm text-gray-600 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden relative">
        <div
          className={cn("h-full rounded-full transition-all duration-500", color)}
          style={{ width: `${Math.max(pct, 1)}%` }}
        />
        <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-gray-700">
          {pct.toFixed(0)}%
        </span>
      </div>
      <span className="w-20 text-right text-sm text-gray-700 tabular-nums shrink-0">
        {formatMoney(value)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page export with Suspense
// ---------------------------------------------------------------------------

export default function SimulatorPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 flex items-center justify-center">
          <div className="w-10 h-10 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <SimulatorContent />
    </Suspense>
  );
}
