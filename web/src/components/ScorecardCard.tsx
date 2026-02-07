"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScorecardResult } from "@/types/chat";

const CATEGORY_COLORS: Record<string, { bar: string; bg: string; text: string }> = {
  "매출력": { bar: "bg-blue-500", bg: "bg-blue-50", text: "text-blue-700" },
  "성장성": { bar: "bg-green-500", bg: "bg-green-50", text: "text-green-700" },
  "경쟁환경": { bar: "bg-amber-500", bg: "bg-amber-50", text: "text-amber-700" },
  "입지여건": { bar: "bg-purple-500", bg: "bg-purple-50", text: "text-purple-700" },
  "안정성": { bar: "bg-teal-500", bg: "bg-teal-50", text: "text-teal-700" },
};

function scoreColor(score: number): string {
  if (score >= 75) return "text-emerald-600";
  if (score >= 50) return "text-amber-600";
  return "text-rose-600";
}

function scoreBadgeBg(percentile: number): string {
  if (percentile <= 20) return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (percentile <= 40) return "bg-blue-100 text-blue-700 border-blue-200";
  if (percentile <= 60) return "bg-amber-100 text-amber-700 border-amber-200";
  return "bg-slate-100 text-slate-600 border-slate-200";
}

export function ScorecardCard({ scorecard }: { scorecard: ScorecardResult }) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  const toggleCategory = (name: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const topPercent = Math.max(1, Math.round(100 - scorecard.percentile));

  return (
    <div className="bg-white rounded-xl border border-slate-200/60 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-4 pb-3 sm:px-5 sm:pt-5 sm:pb-4">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-xs sm:text-sm font-semibold text-slate-500 tracking-wide uppercase">
            투명 스코어카드
          </h3>
          <span
            className={cn(
              "text-[10px] sm:text-xs font-semibold px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-full border",
              scoreBadgeBg(topPercent)
            )}
          >
            상위 {topPercent}%
          </span>
        </div>

        <div className="flex items-end gap-2 sm:gap-3 mt-2 sm:mt-3">
          <span className={cn("text-4xl sm:text-5xl font-extrabold tracking-tight", scoreColor(scorecard.total_score))}>
            {Math.round(scorecard.total_score)}
          </span>
          <span className="text-base sm:text-lg text-slate-400 font-medium mb-1 sm:mb-1.5">/ 100</span>
        </div>

        <p className="text-xs sm:text-sm text-slate-500 mt-1 truncate">
          {scorecard.district_name}
        </p>
      </div>

      {/* Divider */}
      <div className="border-t border-slate-100" />

      {/* Category bars */}
      <div className="px-4 py-3 space-y-2.5 sm:px-5 sm:py-4 sm:space-y-3">
        {scorecard.categories.map((category) => {
          const colors = CATEGORY_COLORS[category.name] ?? {
            bar: "bg-slate-500",
            bg: "bg-slate-50",
            text: "text-slate-700",
          };
          const isExpanded = expandedCategories.has(category.name);
          const roundedScore = Math.round(category.score);

          return (
            <div key={category.name}>
              {/* Category row */}
              <button
                type="button"
                onClick={() => toggleCategory(category.name)}
                className="w-full group active:scale-[0.99] transition-transform"
              >
                <div className="flex items-center justify-between mb-1 sm:mb-1.5">
                  <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                    <span className={cn("text-xs sm:text-sm font-semibold truncate", colors.text)}>
                      {category.name}
                    </span>
                    <span className="text-[10px] sm:text-xs text-slate-400 font-medium flex-shrink-0">
                      ({Math.round(category.weight * 100)}%)
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 sm:gap-2 flex-shrink-0">
                    <span className="text-xs sm:text-sm font-bold text-slate-700">
                      {roundedScore}
                    </span>
                    <ChevronDown
                      size={12}
                      className={cn(
                        "text-slate-400 transition-transform duration-200 sm:w-[14px] sm:h-[14px]",
                        isExpanded && "rotate-180"
                      )}
                    />
                  </div>
                </div>

                {/* Bar */}
                <div className="w-full h-2 sm:h-2.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all duration-500", colors.bar)}
                    style={{ width: `${Math.min(100, Math.max(0, roundedScore))}%` }}
                  />
                </div>
              </button>

              {/* Expanded feature items */}
              {isExpanded && category.items.length > 0 && (
                <div className={cn("mt-2 ml-0.5 sm:ml-1 rounded-lg p-2 sm:p-3 space-y-1.5 sm:space-y-2", colors.bg)}>
                  {category.items.map((item) => (
                    <div key={item.feature} className="flex items-center justify-between text-[10px] sm:text-xs">
                      <span className="text-slate-600 truncate mr-2">{item.label}</span>
                      <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
                        <div className="w-16 sm:w-24 h-1.5 bg-white/60 rounded-full overflow-hidden">
                          <div
                            className={cn("h-full rounded-full", colors.bar)}
                            style={{ width: `${Math.min(100, Math.max(0, Math.round(item.percentile)))}%` }}
                          />
                        </div>
                        <span className="text-slate-700 font-semibold w-6 sm:w-8 text-right">
                          {Math.round(item.percentile)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
