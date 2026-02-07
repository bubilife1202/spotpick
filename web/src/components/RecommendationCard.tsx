"use client";

import { LocationRecommendation } from "@/lib/api";
import { MapPin, TrendingUp, AlertTriangle, Lightbulb, Store, Sparkles, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  recommendation: LocationRecommendation;
  isSelected?: boolean;
  onClick?: () => void;
  compact?: boolean;
  onAskAI?: (question: string) => void;
}

export function RecommendationCard({ 
  recommendation, 
  isSelected, 
  onClick,
  compact = false,
  onAskAI
}: Props) {
  const r = recommendation;
  const kakaoMapUrl = `https://map.kakao.com/link/search/${encodeURIComponent(
    r.address || r.area_name
  )}`;
  
  const probabilityColor = 
    r.success_probability >= 0.7 ? "text-green-600" :
    r.success_probability >= 0.5 ? "text-yellow-600" : "text-red-600";

  const probabilityBgColor = 
    r.success_probability >= 0.7 ? "bg-emerald-50 border-emerald-200" :
    r.success_probability >= 0.5 ? "bg-amber-50 border-amber-200" : "bg-rose-50 border-rose-200";

  if (compact) {
    return (
      <div
        className={cn(
          "group max-w-[400px] bg-gradient-to-br from-white to-slate-50/80",
          "rounded-xl border border-slate-200/60 p-3 sm:p-3.5",
          "hover:shadow-lg hover:shadow-slate-200/50 hover:border-slate-300/80",
          "transition-all duration-300 ease-out cursor-pointer active:scale-[0.98]",
          "backdrop-blur-sm",
          isSelected && "ring-2 ring-blue-500 ring-offset-2"
        )}
        onClick={onClick}
      >
        <div className="flex items-center justify-between gap-2 sm:gap-3">
          <div className="flex items-center gap-2 sm:gap-2.5 min-w-0 flex-1">
            <span className={cn(
              "flex-shrink-0 w-6 h-6 sm:w-7 sm:h-7 rounded-lg flex items-center justify-center",
              "text-xs font-bold text-slate-500 bg-slate-100",
              "group-hover:bg-slate-200 transition-colors"
            )}>
              {r.rank}
            </span>
            <div className="min-w-0 flex-1">
              <span className="font-semibold text-sm sm:text-base text-slate-900 truncate block">
                {r.area_name}
              </span>
              <span className={cn(
                "inline-flex items-center text-[9px] sm:text-[10px] px-1.5 py-0.5 mt-0.5",
                "bg-slate-100 rounded text-slate-500 font-medium tracking-tight"
              )}>
                {r.area_type}
              </span>
            </div>
          </div>
          
          <div className={cn(
            "flex-shrink-0 px-2 py-1 sm:px-2.5 sm:py-1.5 rounded-lg border",
            probabilityBgColor,
            "transition-transform group-hover:scale-105"
          )}>
            <span className={cn("text-base sm:text-lg font-bold tracking-tight", probabilityColor)}>
              {Math.round(r.success_probability * 100)}
              <span className="text-[10px] sm:text-xs font-medium">%</span>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 mt-2.5 sm:mt-3 pt-2.5 sm:pt-3 border-t border-slate-100 overflow-x-auto scrollbar-hide">
          <div className="flex items-center gap-1.5 text-[10px] sm:text-xs text-slate-600 flex-shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
            <span className="font-medium">월세</span>
            <span className="text-slate-900 font-semibold">
              {Math.round(r.estimated_monthly_rent / 10000)}만
            </span>
          </div>
          {r.time_analysis?.peak_time && (
            <div className="flex items-center gap-1.5 text-[10px] sm:text-xs text-slate-600 flex-shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
              <span className="font-medium">피크</span>
              <span className="text-slate-900 font-semibold">
                {r.time_analysis.peak_time}
              </span>
            </div>
          )}
          {r.customer_analysis?.main_age_group && (
            <div className="flex items-center gap-1.5 text-[10px] sm:text-xs text-slate-600 flex-shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-400"></span>
              <span className="text-slate-900 font-semibold">
                {r.customer_analysis.main_age_group}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 mt-2.5 sm:mt-3">
          <button
            onClick={(e) => { e.stopPropagation(); onClick?.(); }}
            className={cn(
              "flex items-center gap-1 text-[10px] sm:text-xs font-medium",
              "text-slate-600 hover:text-blue-600 active:scale-95",
              "transition-all group/btn"
            )}
          >
            <span>상세보기</span>
            <ChevronRight size={10} className="sm:w-3 sm:h-3 group-hover/btn:translate-x-0.5 transition-transform" />
          </button>

          <a
            href={kakaoMapUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className={cn(
              "flex items-center gap-1.5 text-[10px] sm:text-xs font-medium",
              "text-slate-600 hover:text-blue-600 active:scale-95",
              "transition-all"
            )}
            title="카카오맵에서 위치 보기"
          >
            <MapPin size={10} className="sm:w-3 sm:h-3" />
            <span>지도</span>
          </a>
          
          {onAskAI && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAskAI(`${r.area_name} 상권에 대해 자세히 알려줘`);
              }}
              className={cn(
                "flex items-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs font-medium ml-auto",
                "px-2 py-1 sm:px-2.5 sm:py-1.5 rounded-lg",
                "bg-gradient-to-r from-violet-500/10 to-fuchsia-500/10",
                "text-violet-700 hover:from-violet-500/20 hover:to-fuchsia-500/20 active:scale-95",
                "transition-all duration-200"
              )}
            >
              <Sparkles size={10} className="text-violet-500 sm:w-3 sm:h-3" />
              <span className="hidden sm:inline">AI에게 물어보기</span>
              <span className="sm:hidden">AI 질문</span>
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`bg-white rounded-lg shadow-md p-4 cursor-pointer transition-all hover:shadow-lg ${
        isSelected ? "ring-2 ring-blue-500" : ""
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-gray-400">#{r.rank}</span>
            <h3 className="text-lg font-semibold text-gray-900">{r.area_name}</h3>
            <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full text-gray-600">
              {r.area_type}
            </span>
          </div>
          <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
            <MapPin size={14} />
            {r.address}
          </p>
        </div>
        <div className="text-right">
          <div className={`text-2xl font-bold ${probabilityColor}`}>
            {Math.round(r.success_probability * 100)}%
          </div>
          <div className="text-xs text-gray-500">성공 확률</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3 text-sm">
        <div className="bg-gray-50 rounded p-2">
          <div className="text-gray-500 text-xs">예상 월세</div>
          <div className="font-semibold">{(r.estimated_monthly_rent / 10000).toFixed(0)}만원</div>
        </div>
        <div className="bg-gray-50 rounded p-2">
          <div className="text-gray-500 text-xs">유동인구</div>
          <div className="font-semibold">{(r.area_stats.floating_population / 10000).toFixed(1)}만</div>
        </div>
        <div className="bg-gray-50 rounded p-2">
          <div className="text-gray-500 text-xs">3년 생존율</div>
          <div className="font-semibold">{Math.round(r.area_stats.survival_rate_3y * 100)}%</div>
        </div>
      </div>

      {r.key_success_factors.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-1 text-xs text-green-700 mb-1">
            <TrendingUp size={12} />
            성공 요인
          </div>
          <div className="flex flex-wrap gap-1">
            {r.key_success_factors.slice(0, 3).map((factor, i) => (
              <span key={i} className="text-xs px-2 py-0.5 bg-green-50 text-green-700 rounded">
                {factor}
              </span>
            ))}
          </div>
        </div>
      )}

      {r.risk_factors.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-1 text-xs text-orange-700 mb-1">
            <AlertTriangle size={12} />
            주의 사항
          </div>
          <p className="text-xs text-orange-700">{r.risk_factors[0]}</p>
        </div>
      )}

      {r.recommendations.length > 0 && (
        <div className="border-t pt-2">
          <div className="flex items-center gap-1 text-xs text-blue-700 mb-1">
            <Lightbulb size={12} />
            추천 전략
          </div>
          <p className="text-xs text-gray-600">{r.recommendations[0]}</p>
        </div>
      )}

      {r.nearby_successful_stores.length > 0 && (
        <div className="border-t pt-2 mt-2">
          <div className="flex items-center gap-1 text-xs text-gray-500 mb-1">
            <Store size={12} />
            인근 성공 매장
          </div>
          <div className="flex flex-wrap gap-1">
            {r.nearby_successful_stores.slice(0, 3).map((store, i) => (
              <span key={i} className="text-xs text-gray-600">
                {store.name} ({(store.score * 100).toFixed(0)}점)
                {i < 2 && r.nearby_successful_stores.length > i + 1 ? "," : ""}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
