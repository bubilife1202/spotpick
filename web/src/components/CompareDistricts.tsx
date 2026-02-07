"use client";

import { X, Trophy, TrendingUp, TrendingDown, BarChart3 } from "lucide-react";
import { cn, formatMoney } from "@/lib/utils";
import { ScorecardResult } from "@/types/chat";
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, Legend, ResponsiveContainer } from "recharts";

export interface District {
  name: string;
  type: string;
  monthly_sales: number;
  estimated_rent: number;
  survival_rate: number;
  store_count: number;
  peak_time: string;
  main_age_group: string;
  female_ratio: number;
  scorecard?: ScorecardResult;
}

interface CompareDistrictsProps {
  isOpen: boolean;
  onClose: () => void;
  districts: District[];
}

const COMPARISON_ITEMS = [
  { key: "monthly_sales", label: "월 매출", format: formatMoney, higher: true, category: "매출" },
  { key: "estimated_rent", label: "예상 월세", format: formatMoney, higher: false, category: "임대료" },
  { key: "survival_rate", label: "생존율", format: (v: number) => `${(v * 100).toFixed(0)}%`, higher: true, category: "생존율" },
  { key: "store_count", label: "경쟁 점포", format: (v: number) => `${v}개`, higher: false, category: "경쟁강도" },
  { key: "peak_time", label: "피크 시간", format: (v: string) => v, higher: null, category: null },
  { key: "main_age_group", label: "주요 고객", format: (v: string) => v, higher: null, category: null },
  { key: "female_ratio", label: "여성 비율", format: (v: number) => `${(v * 100).toFixed(0)}%`, higher: null, category: null },
];

const DISTRICT_COLORS = ["#6366f1", "#8b5cf6", "#ec4899"]; // indigo, purple, pink

/**
 * 레이더 차트용 데이터 생성 (5개 카테고리 점수)
 */
function buildRadarData(districts: District[]): Array<Record<string, string | number>> | null {
  // 모든 상권이 scorecard가 있는지 확인
  const allHaveScorecard = districts.every((d) => d.scorecard?.categories);
  if (!allHaveScorecard) return null;

  const categoryNames = ["매출력", "성장성", "경쟁환경", "입지여건", "안정성"];

  return categoryNames.map((catName) => {
    const dataPoint: Record<string, string | number> = { category: catName };
    districts.forEach((d) => {
      const cat = d.scorecard!.categories.find((c) => c.name === catName);
      dataPoint[d.name] = cat?.score || 0;
    });
    return dataPoint;
  });
}

export function CompareDistricts({ isOpen, onClose, districts }: CompareDistrictsProps) {
  if (!isOpen || districts.length < 2) return null;

  // 최대 3개 상권까지만 비교
  const compareDistricts = districts.slice(0, 3);
  const radarData = buildRadarData(compareDistricts);

  const getWinner = (key: string, higher: boolean | null) => {
    if (higher === null) return null;

    const values = compareDistricts.map((d) => d[key as keyof District] as number);
    const winnerIdx = higher
      ? values.indexOf(Math.max(...values))
      : values.indexOf(Math.min(...values));
    return winnerIdx;
  };

  const totalWins = compareDistricts.map((_, idx) => {
    return COMPARISON_ITEMS.filter((item) => {
      const winner = getWinner(item.key, item.higher);
      return winner === idx;
    }).length;
  });

  const overallWinner = totalWins.indexOf(Math.max(...totalWins));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />

      <div className="relative w-full max-w-5xl bg-white rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-2">
            <BarChart3 size={20} />
            <h3 className="font-semibold">상권 비교 분석 ({compareDistricts.length}개)</h3>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-white/20 rounded-full">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-8">
          {/* 상권 헤더 */}
          <div className={cn("grid gap-4 mb-6", compareDistricts.length === 2 ? "grid-cols-3" : "grid-cols-4")}>
            <div className="flex items-center">
              <p className="text-xs font-semibold text-gray-500 uppercase">비교 항목</p>
            </div>
            {compareDistricts.map((d, idx) => (
              <div
                key={d.name}
                className={cn(
                  "text-center p-3 rounded-xl border-2",
                  idx === overallWinner
                    ? "bg-gradient-to-br from-amber-50 to-yellow-50 border-amber-300"
                    : "bg-gray-50 border-transparent"
                )}
              >
                {idx === overallWinner && (
                  <div className="flex items-center justify-center gap-1 text-amber-600 text-xs font-medium mb-1">
                    <Trophy size={12} />
                    추천
                  </div>
                )}
                <p className="font-bold text-gray-900">{d.name}</p>
                <p className="text-xs text-gray-500">{d.type}</p>
              </div>
            ))}
          </div>

          {/* 레이더 차트 - 5개 카테고리 시각 비교 */}
          {radarData && (
            <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6">
              <h4 className="text-sm font-bold text-gray-700 mb-4 flex items-center gap-2">
                <BarChart3 size={16} />
                종합 점수 비교 (5개 카테고리)
              </h4>
              <ResponsiveContainer width="100%" height={320}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#d1d5db" />
                  <PolarAngleAxis dataKey="category" tick={{ fontSize: 12, fill: "#4b5563" }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                  {compareDistricts.map((d, idx) => (
                    <Radar
                      key={d.name}
                      name={d.name}
                      dataKey={d.name}
                      stroke={DISTRICT_COLORS[idx % DISTRICT_COLORS.length]}
                      fill={DISTRICT_COLORS[idx % DISTRICT_COLORS.length]}
                      fillOpacity={0.25}
                      strokeWidth={2}
                    />
                  ))}
                  <Legend wrapperStyle={{ fontSize: "12px" }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* 항목별 상세 비교 테이블 */}
          <div>
            <h4 className="text-sm font-bold text-gray-700 mb-3 flex items-center gap-2">
              <Trophy size={16} />
              항목별 상세 비교
            </h4>
            <div className="space-y-2">
              {COMPARISON_ITEMS.map((item) => {
                const winner = getWinner(item.key, item.higher);

                return (
                  <div
                    key={item.key}
                    className={cn(
                      "grid gap-4 items-center py-3 px-4 border-b border-gray-100 hover:bg-gray-50 rounded-lg transition-colors",
                      compareDistricts.length === 2 ? "grid-cols-3" : "grid-cols-4"
                    )}
                  >
                    <p className="text-sm font-medium text-gray-700">{item.label}</p>
                    {compareDistricts.map((d, idx) => {
                      const value = d[item.key as keyof District];
                      const isWinner = winner === idx;

                      return (
                        <div
                          key={`${d.name}-${item.key}`}
                          className={cn(
                            "text-center py-2 px-3 rounded-lg text-sm font-medium transition-all",
                            isWinner
                              ? "bg-green-50 text-green-700 border border-green-200"
                              : "text-gray-700"
                          )}
                        >
                          <span className="flex items-center justify-center gap-1">
                            {item.format(value as never)}
                            {isWinner && item.higher !== null && (
                              item.higher ? (
                                <TrendingUp size={14} className="text-green-600" />
                              ) : (
                                <TrendingDown size={14} className="text-green-600" />
                              )
                            )}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>

          {/* 카테고리별 점수 상세 */}
          {radarData && (
            <div>
              <h4 className="text-sm font-bold text-gray-700 mb-3">카테고리별 점수</h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                {["매출력", "성장성", "경쟁환경", "입지여건", "안정성"].map((catName) => (
                  <div key={catName} className="bg-white border border-gray-200 rounded-lg p-3">
                    <p className="text-xs font-semibold text-gray-600 mb-2 text-center">{catName}</p>
                    {compareDistricts.map((d, idx) => {
                      const cat = d.scorecard?.categories.find((c) => c.name === catName);
                      const score = cat?.score || 0;
                      return (
                        <div key={d.name} className="flex items-center justify-between text-xs mb-1">
                          <span
                            className="w-2 h-2 rounded-full mr-1"
                            style={{ backgroundColor: DISTRICT_COLORS[idx % DISTRICT_COLORS.length] }}
                          />
                          <span className="flex-1 text-gray-700 truncate text-[10px]">{d.name}</span>
                          <span className="font-semibold text-gray-900">{score.toFixed(1)}</span>
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 비교 결과 요약 */}
          <div className="p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl">
            <p className="text-sm font-semibold text-gray-700 mb-2">📊 비교 결과</p>
            <p className="text-sm text-gray-600">
              <strong className="text-blue-600">{compareDistricts[overallWinner].name}</strong>이(가)
              {" "}{totalWins[overallWinner]}개 항목에서 우세합니다.
              {compareDistricts[overallWinner].survival_rate > 0.9 && (
                <> 특히 <strong>높은 생존율</strong>이 장점입니다.</>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export function CompareButton({ onClick, count }: { onClick: () => void; count: number }) {
  if (count < 2) return null;

  const displayCount = Math.min(count, 3);
  const isMaxed = count > 3;

  return (
    <button
      onClick={onClick}
      className={cn(
        "fixed bottom-24 right-6 px-4 py-2 rounded-full shadow-lg transition-all flex items-center gap-2 z-40",
        isMaxed
          ? "bg-amber-600 hover:bg-amber-700 text-white animate-pulse"
          : "bg-indigo-600 hover:bg-indigo-700 text-white"
      )}
    >
      <BarChart3 size={18} />
      비교하기 ({displayCount}{isMaxed && "+"})
    </button>
  );
}
