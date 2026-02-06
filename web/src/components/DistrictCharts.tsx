"use client";

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
} from "recharts";
import { DistrictAnalysis } from "@/lib/chat-api";

interface DistrictChartsProps {
  data: DistrictAnalysis;
  compact?: boolean;
}

const COLORS = {
  primary: "#2563eb",
  secondary: "#60a5fa",
  accent: "#f59e0b",
  success: "#10b981",
  danger: "#ef4444",
  gray: "#6b7280",
};

const AGE_COLORS = ["#fcd34d", "#fbbf24", "#f59e0b", "#d97706", "#b45309", "#92400e"];
const GENDER_COLORS = ["#3b82f6", "#ec4899"];

export function DistrictCharts({ data, compact = false }: DistrictChartsProps) {
  const timeData = [
    { name: "00-06", value: data.time_analysis.time_00_06, label: "새벽" },
    { name: "06-11", value: data.time_analysis.time_06_11, label: "오전" },
    { name: "11-14", value: data.time_analysis.time_11_14, label: "점심" },
    { name: "14-17", value: data.time_analysis.time_14_17, label: "오후" },
    { name: "17-21", value: data.time_analysis.time_17_21, label: "저녁" },
    { name: "21-24", value: data.time_analysis.time_21_24, label: "심야" },
  ];

  const ageData = [
    { name: "10대", value: data.customer_analysis.age_10 },
    { name: "20대", value: data.customer_analysis.age_20 },
    { name: "30대", value: data.customer_analysis.age_30 },
    { name: "40대", value: data.customer_analysis.age_40 },
    { name: "50대", value: data.customer_analysis.age_50 },
    { name: "60대+", value: data.customer_analysis.age_60 },
  ];

  const genderData = [
    { name: "남성", value: data.customer_analysis.male_ratio },
    { name: "여성", value: data.customer_analysis.female_ratio },
  ];

  const dayData = [
    { name: "월", value: data.day_analysis.mon },
    { name: "화", value: data.day_analysis.tue },
    { name: "수", value: data.day_analysis.wed },
    { name: "목", value: data.day_analysis.thu },
    { name: "금", value: data.day_analysis.fri },
    { name: "토", value: data.day_analysis.sat },
    { name: "일", value: data.day_analysis.sun },
  ];

  if (compact) {
    return (
      <div className="grid grid-cols-2 gap-3">
        <MiniChart title="시간대별" data={timeData} color={COLORS.primary} />
        <MiniChart title="연령대별" data={ageData} color={COLORS.accent} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-gray-50 rounded-xl p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          ⏰ 시간대별 매출 비중
          <span className="text-xs font-normal text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
            피크: {data.time_analysis.peak_time}
          </span>
        </h4>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={timeData}>
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
            <Tooltip
              formatter={(value: number) => [`${value.toFixed(1)}%`, "매출 비중"]}
              contentStyle={{ fontSize: 12 }}
            />
            <Bar
              dataKey="value"
              fill={COLORS.primary}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-50 rounded-xl p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            👥 연령대별
            <span className="text-xs font-normal text-amber-600 bg-amber-50 px-2 py-0.5 rounded">
              주요: {data.customer_analysis.main_age_group}
            </span>
          </h4>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={ageData} layout="vertical">
              <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={35} />
              <Tooltip
                formatter={(value: number) => [`${value.toFixed(1)}%`, "비중"]}
                contentStyle={{ fontSize: 11 }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {ageData.map((_, index) => (
                  <Cell key={index} fill={AGE_COLORS[index]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-50 rounded-xl p-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-3">🚻 성별 비율</h4>
          <ResponsiveContainer width="100%" height={140}>
            <PieChart>
              <Pie
                data={genderData}
                cx="50%"
                cy="50%"
                innerRadius={30}
                outerRadius={50}
                paddingAngle={2}
                dataKey="value"
                label={({ name, value }) => `${name} ${value.toFixed(0)}%`}
                labelLine={false}
              >
                {genderData.map((_, index) => (
                  <Cell key={index} fill={GENDER_COLORS[index]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => [`${value.toFixed(1)}%`, "비율"]}
                contentStyle={{ fontSize: 11 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-gray-50 rounded-xl p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          📅 요일별 매출 비중
          <span className="text-xs font-normal text-green-600 bg-green-50 px-2 py-0.5 rounded">
            피크: {data.day_analysis.peak_day}요일
          </span>
        </h4>
        <ResponsiveContainer width="100%" height={120}>
          <BarChart data={dayData}>
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
            <Tooltip
              formatter={(value: number) => [`${value.toFixed(1)}%`, "매출 비중"]}
              contentStyle={{ fontSize: 12 }}
            />
            <Bar
              dataKey="value"
              fill={COLORS.success}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-4">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">📊 경쟁 현황</h4>
        <div className="grid grid-cols-4 gap-3 text-center">
          <div>
            <p className="text-lg font-bold text-blue-600">{data.competition.store_count}</p>
            <p className="text-xs text-gray-500">점포 수</p>
          </div>
          <div>
            <p className="text-lg font-bold text-green-600">+{data.competition.new_stores}</p>
            <p className="text-xs text-gray-500">신규 개업</p>
          </div>
          <div>
            <p className="text-lg font-bold text-red-600">-{data.competition.closed_stores}</p>
            <p className="text-xs text-gray-500">폐업</p>
          </div>
          <div>
            <p className="text-lg font-bold text-amber-600">{data.competition.franchise_ratio.toFixed(0)}%</p>
            <p className="text-xs text-gray-500">프랜차이즈</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniChart({
  title,
  data,
  color,
}: {
  title: string;
  data: { name: string; value: number }[];
  color: string;
}) {
  return (
    <div className="bg-gray-50 rounded-lg p-2">
      <p className="text-xs font-medium text-gray-600 mb-1">{title}</p>
      <ResponsiveContainer width="100%" height={60}>
        <BarChart data={data}>
          <Bar dataKey="value" fill={color} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
