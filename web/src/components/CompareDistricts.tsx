"use client";

import { X, Trophy, TrendingUp, TrendingDown } from "lucide-react";
import { cn, formatMoney } from "@/lib/utils";

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
}

interface CompareDistrictsProps {
  isOpen: boolean;
  onClose: () => void;
  districts: District[];
}

const COMPARISON_ITEMS = [
  { key: "monthly_sales", label: "월 매출", format: formatMoney, higher: true },
  { key: "estimated_rent", label: "예상 월세", format: formatMoney, higher: false },
  { key: "survival_rate", label: "생존율", format: (v: number) => `${(v * 100).toFixed(0)}%`, higher: true },
  { key: "store_count", label: "경쟁 점포", format: (v: number) => `${v}개`, higher: false },
  { key: "peak_time", label: "피크 시간", format: (v: string) => v, higher: null },
  { key: "main_age_group", label: "주요 고객", format: (v: string) => v, higher: null },
  { key: "female_ratio", label: "여성 비율", format: (v: number) => `${(v * 100).toFixed(0)}%`, higher: null },
];

export function CompareDistricts({ isOpen, onClose, districts }: CompareDistrictsProps) {
  if (!isOpen || districts.length < 2) return null;

  const getWinner = (key: string, higher: boolean | null) => {
    if (higher === null) return null;
    
    const values = districts.map((d) => d[key as keyof District] as number);
    const winnerIdx = higher
      ? values.indexOf(Math.max(...values))
      : values.indexOf(Math.min(...values));
    return winnerIdx;
  };

  const totalWins = districts.map((_, idx) => {
    return COMPARISON_ITEMS.filter((item) => {
      const winner = getWinner(item.key, item.higher);
      return winner === idx;
    }).length;
  });

  const overallWinner = totalWins.indexOf(Math.max(...totalWins));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      
      <div className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div className="px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Trophy size={20} />
            <h3 className="font-semibold">상권 비교 분석</h3>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-white/20 rounded-full">
            <X size={20} />
          </button>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div />
            {districts.map((d, idx) => (
              <div
                key={d.name}
                className={cn(
                  "text-center p-3 rounded-xl",
                  idx === overallWinner
                    ? "bg-gradient-to-br from-amber-50 to-yellow-50 border-2 border-amber-300"
                    : "bg-gray-50"
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

          <div className="space-y-2">
            {COMPARISON_ITEMS.map((item) => {
              const winner = getWinner(item.key, item.higher);
              
              return (
                <div key={item.key} className="grid grid-cols-3 gap-4 items-center py-2 border-b border-gray-100">
                  <p className="text-sm font-medium text-gray-600">{item.label}</p>
                  {districts.map((d, idx) => {
                    const value = d[item.key as keyof District];
                    const isWinner = winner === idx;
                    
                    return (
                      <div
                        key={`${d.name}-${item.key}`}
                        className={cn(
                          "text-center py-1 px-2 rounded-lg text-sm",
                          isWinner ? "bg-green-50 text-green-700 font-semibold" : "text-gray-700"
                        )}
                      >
                        <span className="flex items-center justify-center gap-1">
                          {item.format(value as never)}
                          {isWinner && item.higher !== null && (
                            item.higher ? (
                              <TrendingUp size={14} className="text-green-500" />
                            ) : (
                              <TrendingDown size={14} className="text-green-500" />
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

          <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl">
            <p className="text-sm font-semibold text-gray-700 mb-2">📊 비교 결과</p>
            <p className="text-sm text-gray-600">
              <strong className="text-blue-600">{districts[overallWinner].name}</strong>이(가)
              {" "}{totalWins[overallWinner]}개 항목에서 우세합니다.
              {districts[overallWinner].survival_rate > 0.9 && (
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
  
  return (
    <button
      onClick={onClick}
      className="fixed bottom-24 right-6 px-4 py-2 bg-indigo-600 text-white rounded-full shadow-lg hover:bg-indigo-700 transition-all flex items-center gap-2 z-40"
    >
      <Trophy size={18} />
      비교하기 ({count})
    </button>
  );
}
