/**
 * TrendChart Component
 *
 * Displays Naver DataLab search trend data as an interactive line chart.
 * Supports multiple keyword comparison with distinct colors.
 */
'use client';

import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { TrendData } from '@/types/chat';

interface TrendChartProps {
  data: TrendData;
}

// Color palette for up to 5 keywords
const TREND_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
];

export default function TrendChart({ data }: TrendChartProps) {
  const { trends = [], period, summary } = data;

  // Transform data for Recharts format
  // Each period becomes a row, with columns for each keyword
  const chartData = React.useMemo(() => {
    if (!trends || trends.length === 0) return [];

    // Get all unique periods across all keywords
    const allPeriods = new Set<string>();
    trends.forEach(trend => {
      trend.data.forEach(point => allPeriods.add(point.period));
    });

    // Sort periods chronologically
    const sortedPeriods = Array.from(allPeriods).sort();

    // Build chart data: one row per period
    return sortedPeriods.map(period => {
      const row: Record<string, string | number> = { period };

      trends.forEach(trend => {
        const dataPoint = trend.data.find(d => d.period === period);
        row[trend.keyword] = dataPoint?.ratio || 0;
      });

      return row;
    });
  }, [trends]);

  // Format period for display (YYYY-MM-DD → MM월)
  const formatPeriod = (period: string) => {
    try {
      const date = new Date(period);
      return `${date.getMonth() + 1}월`;
    } catch {
      return period;
    }
  };

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) => {
    if (!active || !payload || payload.length === 0) return null;

    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
        <p className="text-sm font-medium text-gray-900 mb-2">{label}</p>
        {payload.map((entry, index: number) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-gray-700">{entry.name}:</span>
            <span className="font-medium text-gray-900">{entry.value.toFixed(1)}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 md:p-6">
      {/* Header */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">
          검색 트렌드 분석
        </h3>
        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
          <span>기간: {period.start} ~ {period.end}</span>
          {summary && summary.top_keyword && (
            <>
              <span className="text-gray-400">|</span>
              <span className="text-blue-600 font-medium">
                가장 인기: {summary.top_keyword}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Chart */}
      <div className="w-full" style={{ height: '300px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
          >
            <defs>
              {trends.map((trend, index) => (
                <linearGradient
                  key={trend.keyword}
                  id={`color-${index}`}
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="1"
                >
                  <stop offset="5%" stopColor={TREND_COLORS[index % TREND_COLORS.length]} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={TREND_COLORS[index % TREND_COLORS.length]} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />

            <XAxis
              dataKey="period"
              tickFormatter={formatPeriod}
              tick={{ fontSize: 12, fill: '#6b7280' }}
              stroke="#d1d5db"
            />

            <YAxis
              tick={{ fontSize: 12, fill: '#6b7280' }}
              stroke="#d1d5db"
              label={{
                value: '검색량 지수',
                angle: -90,
                position: 'insideLeft',
                style: { fontSize: 12, fill: '#6b7280' }
              }}
            />

            <Tooltip content={<CustomTooltip />} />

            <Legend
              wrapperStyle={{ fontSize: '12px' }}
              iconType="line"
            />

            {trends.map((trend, index) => (
              <Area
                key={trend.keyword}
                type="monotone"
                dataKey={trend.keyword}
                stroke={TREND_COLORS[index % TREND_COLORS.length]}
                strokeWidth={2}
                fill={`url(#color-${index})`}
                animationDuration={1000}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Legend with averages */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {trends.map((trend, index) => (
            <div key={trend.keyword} className="flex items-center gap-3">
              <div
                className="w-3 h-3 rounded-full flex-shrink-0"
                style={{ backgroundColor: TREND_COLORS[index % TREND_COLORS.length] }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {trend.keyword}
                </p>
                <p className="text-xs text-gray-500">
                  평균 검색량: {trend.average_ratio.toFixed(1)}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
