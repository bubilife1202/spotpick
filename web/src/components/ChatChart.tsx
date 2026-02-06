"use client";

import { useState, useCallback } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Area,
  AreaChart,
} from "recharts";
import { ChevronDown, Clock, Calendar, Users, UserCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { ChartData } from "@/types/chat";

// Re-export for backward compatibility
export type { ChartData };

// ============================================
// Types
// ============================================

interface ChatChartProps {
  chart: ChartData;
  expanded?: boolean;
}

interface ChatChartSectionProps {
  charts: ChartData[];
}

// ============================================
// Color Palettes - Distinctive, not generic
// ============================================

const CHART_THEMES = {
  time: {
    gradient: ["#0ea5e9", "#6366f1"],
    fill: "#0ea5e9",
    bg: "from-sky-50 to-indigo-50",
    border: "border-sky-200/60",
    icon: Clock,
    accent: "text-sky-600",
    badge: "bg-sky-100 text-sky-700",
  },
  day: {
    gradient: ["#10b981", "#059669"],
    fill: "#10b981",
    bg: "from-emerald-50 to-teal-50",
    border: "border-emerald-200/60",
    icon: Calendar,
    accent: "text-emerald-600",
    badge: "bg-emerald-100 text-emerald-700",
  },
  age: {
    gradient: ["#f59e0b", "#d97706"],
    fill: "#f59e0b",
    bg: "from-amber-50 to-orange-50",
    border: "border-amber-200/60",
    icon: Users,
    accent: "text-amber-600",
    badge: "bg-amber-100 text-amber-700",
  },
  gender: {
    gradient: ["#ec4899", "#8b5cf6"],
    fill: "#ec4899",
    bg: "from-pink-50 to-violet-50",
    border: "border-pink-200/60",
    icon: UserCircle,
    accent: "text-pink-600",
    badge: "bg-pink-100 text-pink-700",
  },
};

const GENDER_COLORS = ["#3b82f6", "#ec4899"];
const AGE_GRADIENT = ["#fcd34d", "#fbbf24", "#f59e0b", "#ea580c", "#c2410c", "#9a3412"];

// ============================================
// Custom Tooltip
// ============================================

const CustomTooltip = ({
  active,
  payload,
  theme,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: { name: string } }>;
  theme: (typeof CHART_THEMES)[keyof typeof CHART_THEMES];
}) => {
  if (!active || !payload || !payload.length) return null;
  const label = (payload[0].payload as { label?: string }).label;

  return (
    <div className="bg-white/95 backdrop-blur-sm px-3 py-2 rounded-lg shadow-lg border border-gray-100">
      <p className="text-xs font-medium text-gray-600">{payload[0].payload.name}</p>
      <p className={cn("text-sm font-bold", theme.accent)}>
        {payload[0].value.toFixed(1)}%
      </p>
      {label && <p className="text-[11px] text-gray-500">{label}</p>}
    </div>
  );
};

// ============================================
// Main Component
// ============================================

export function ChatChart({ chart, expanded: initialExpanded = false }: ChatChartProps) {
  const [expanded, setExpanded] = useState(initialExpanded);
  const theme = CHART_THEMES[chart.type];
  const Icon = theme.icon;

  const handleToggle = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleToggle();
      }
    },
    [handleToggle]
  );

  // Peak value calculation
  const peakItem = chart.data.reduce(
    (max, item) => (item.value > max.value ? item : max),
    chart.data[0]
  );

  const topBuckets = [...chart.data].sort((a, b) => b.value - a.value).slice(0, 3);

  const renderChart = () => {
    switch (chart.type) {
      case "gender":
        return <GenderChart data={chart.data} expanded={expanded} />;
      case "age":
        return <AgeChart data={chart.data} expanded={expanded} theme={theme} />;
      case "time":
      case "day":
      default:
        return <TimeBarChart data={chart.data} expanded={expanded} theme={theme} />;
    }
  };

  return (
    <div
      className={cn(
        "relative rounded-xl border overflow-hidden my-2",
        "bg-gradient-to-br",
        theme.bg,
        theme.border,
        "transition-all duration-300 ease-out",
        expanded ? "shadow-md" : "shadow-sm"
      )}
    >
      {/* Header */}
      <button
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        className={cn(
          "flex items-center justify-between w-full px-3 py-2.5",
          "text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1",
          "focus-visible:ring-blue-500 rounded-t-xl",
          "hover:bg-white/30 transition-colors"
        )}
        aria-expanded={expanded}
        aria-controls={`chart-${chart.type}`}
      >
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "w-7 h-7 rounded-lg flex items-center justify-center",
              "bg-white/70 shadow-sm"
            )}
          >
            <Icon size={14} className={theme.accent} />
          </div>
          <span className="text-sm font-semibold text-gray-700">{chart.title}</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Peak badge */}
          <span className={cn("text-[10px] font-medium px-2 py-0.5 rounded-full", theme.badge)}>
            {chart.highlight || `피크: ${peakItem.name}`}
          </span>

          {/* Chevron with rotation */}
          <ChevronDown
            size={16}
            className={cn(
              "text-gray-400 transition-transform duration-300",
              expanded && "rotate-180"
            )}
          />
        </div>
      </button>

      {/* Chart Container with height animation */}
      <div
        id={`chart-${chart.type}`}
        className={cn(
          "overflow-hidden transition-all duration-300 ease-out",
          expanded ? "max-h-[220px] opacity-100" : "max-h-[100px] opacity-90"
        )}
      >
        <div className="px-3 pb-3">{renderChart()}</div>
      </div>

      {expanded && topBuckets.length > 0 && (
        <div className="px-3 pb-3">
          <div className="grid gap-1">
            {topBuckets.map((item) => (
              <div key={item.name} className="flex items-baseline justify-between gap-3">
                <span className="text-[11px] font-medium text-gray-700">{item.name}</span>
                <span className="text-[11px] text-gray-500 text-right">
                  {item.value.toFixed(1)}%{item.label ? ` · ${item.label}` : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Decorative corner element */}
      <div
        className={cn(
          "absolute top-0 right-0 w-16 h-16 opacity-[0.07] pointer-events-none",
          "bg-gradient-to-br from-current to-transparent rounded-bl-full",
          theme.accent
        )}
      />
    </div>
  );
}

// ============================================
// Chart Variants
// ============================================

function TimeBarChart({
  data,
  expanded,
  theme,
}: {
  data: ChartData["data"];
  expanded: boolean;
  theme: (typeof CHART_THEMES)[keyof typeof CHART_THEMES];
}) {
  return (
    <ResponsiveContainer width="100%" height={expanded ? 180 : 80}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id={`gradient-${theme.fill}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={theme.gradient[0]} stopOpacity={0.4} />
            <stop offset="100%" stopColor={theme.gradient[1]} stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="name"
          tick={{ fontSize: 9, fill: "#6b7280" }}
          axisLine={false}
          tickLine={false}
          interval={0}
        />
        {expanded && (
          <YAxis
            tick={{ fontSize: 9, fill: "#9ca3af" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
            width={32}
          />
        )}
        <Tooltip content={<CustomTooltip theme={theme} />} />
        <Area
          type="monotone"
          dataKey="value"
          stroke={theme.gradient[0]}
          strokeWidth={2}
          fill={`url(#gradient-${theme.fill})`}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function AgeChart({
  data,
  expanded,
  theme,
}: {
  data: ChartData["data"];
  expanded: boolean;
  theme: (typeof CHART_THEMES)[keyof typeof CHART_THEMES];
}) {
  return (
    <ResponsiveContainer width="100%" height={expanded ? 180 : 80}>
      <BarChart
        data={data}
        layout={expanded ? "vertical" : "horizontal"}
        margin={
          expanded
            ? { top: 8, right: 8, left: 0, bottom: 0 }
            : { top: 8, right: 8, left: -20, bottom: 0 }
        }
      >
        {expanded ? (
          <>
            <XAxis
              type="number"
              tick={{ fontSize: 9, fill: "#9ca3af" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fontSize: 9, fill: "#6b7280" }}
              axisLine={false}
              tickLine={false}
              width={36}
            />
          </>
        ) : (
          <XAxis
            dataKey="name"
            tick={{ fontSize: 8, fill: "#9ca3af" }}
            axisLine={false}
            tickLine={false}
            interval={0}
          />
        )}
        <Tooltip content={<CustomTooltip theme={theme} />} />
        <Bar dataKey="value" radius={expanded ? [0, 4, 4, 0] : [4, 4, 0, 0]}>
          {data.map((_, index) => (
            <Cell key={index} fill={AGE_GRADIENT[index % AGE_GRADIENT.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function GenderChart({ data, expanded }: { data: ChartData["data"]; expanded: boolean }) {
  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className={cn("flex items-center", expanded ? "gap-4" : "gap-2")}>
      <ResponsiveContainer width={expanded ? 140 : 80} height={expanded ? 140 : 80}>
        <PieChart>
          <Tooltip content={<CustomTooltip theme={CHART_THEMES.gender} />} />
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={expanded ? 35 : 20}
            outerRadius={expanded ? 55 : 32}
            paddingAngle={3}
            dataKey="value"
            strokeWidth={0}
          >
            {data.map((_, index) => (
              <Cell
                key={index}
                fill={GENDER_COLORS[index % GENDER_COLORS.length]}
                className="drop-shadow-sm"
              />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className={cn("flex flex-col gap-1.5", !expanded && "hidden sm:flex")}>
        {data.map((item, index) => (
          <div key={item.name} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full shadow-sm"
              style={{ backgroundColor: GENDER_COLORS[index % GENDER_COLORS.length] }}
            />
            <span className="text-xs text-gray-600">{item.name}</span>
            <span className="text-xs font-semibold text-gray-800">
              {total > 0 ? item.value.toFixed(1) : "0.0"}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================
// Section Component (Multiple Charts)
// ============================================

export function ChatChartSection({ charts }: ChatChartSectionProps) {
  if (!charts || charts.length === 0) return null;

  return (
    <div className="space-y-2">
      {charts.map((chart, index) => (
        <ChatChart
          key={`${chart.type}-${index}`}
          chart={chart}
          expanded={index === 0} // First chart expanded by default
        />
      ))}
    </div>
  );
}

// ============================================
// Demo Data Generator (for testing)
// ============================================

export const DEMO_CHARTS: ChartData[] = [
  {
    type: "time",
    title: "시간대별 매출",
    data: [
      { name: "새벽", value: 5.2 },
      { name: "오전", value: 18.4 },
      { name: "점심", value: 28.1 },
      { name: "오후", value: 15.3 },
      { name: "저녁", value: 22.8 },
      { name: "심야", value: 10.2 },
    ],
    highlight: "점심 피크",
  },
  {
    type: "day",
    title: "요일별 매출",
    data: [
      { name: "월", value: 12.1 },
      { name: "화", value: 11.8 },
      { name: "수", value: 13.2 },
      { name: "목", value: 14.5 },
      { name: "금", value: 18.9 },
      { name: "토", value: 17.2 },
      { name: "일", value: 12.3 },
    ],
  },
  {
    type: "age",
    title: "연령대별 고객",
    data: [
      { name: "10대", value: 8.5 },
      { name: "20대", value: 32.1 },
      { name: "30대", value: 28.4 },
      { name: "40대", value: 18.2 },
      { name: "50대", value: 9.1 },
      { name: "60+", value: 3.7 },
    ],
    highlight: "20-30대 주력",
  },
  {
    type: "gender",
    title: "성별 비율",
    data: [
      { name: "남성", value: 42 },
      { name: "여성", value: 58 },
    ],
  },
];
