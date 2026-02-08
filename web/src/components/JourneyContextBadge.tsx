"use client";

import { useJourneyStore, INDUSTRY_NAMES, INDUSTRY_ICONS } from "@/lib/journey-store";
import { Store, MapPin, Building2, Wallet } from "lucide-react";
import { cn } from "@/lib/utils";

function formatBudget(manWon: number): string {
  if (manWon >= 10000) {
    const eok = manWon / 10000;
    return Number.isInteger(eok) ? `${eok}억` : `${eok.toFixed(1)}억`;
  }
  return `${manWon.toLocaleString()}만`;
}

export function JourneyContextBadge({ className }: { className?: string }) {
  const {
    industryCode,
    selectedDistrict,
    franchiseChoice,
    budgetMin,
    budgetMax,
  } = useJourneyStore();

  const industryName = INDUSTRY_NAMES[industryCode] || "카페";
  const industryIcon = INDUSTRY_ICONS[industryCode] || "☕";

  const hasPrevData =
    industryCode || selectedDistrict || franchiseChoice || budgetMax > 0;
  if (!hasPrevData) return null;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 rounded-xl bg-slate-50 border border-slate-200/60 px-4 py-2.5",
        className
      )}
    >
      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-1">
        이전 단계
      </span>

      {/* Industry */}
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-50 border border-blue-200/60 text-blue-700 text-xs font-medium">
        <Store className="w-3 h-3" />
        {industryIcon} {industryName}
      </span>

      {/* District */}
      {selectedDistrict && (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200/60 text-emerald-700 text-xs font-medium">
          <MapPin className="w-3 h-3" />
          {selectedDistrict.district_name}
        </span>
      )}

      {/* Franchise choice */}
      {franchiseChoice && (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-violet-50 border border-violet-200/60 text-violet-700 text-xs font-medium">
          <Building2 className="w-3 h-3" />
          {franchiseChoice === "franchise" ? "프랜차이즈" : "독립 창업"}
        </span>
      )}

      {/* Budget */}
      {budgetMax > 0 && (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 border border-amber-200/60 text-amber-700 text-xs font-medium">
          <Wallet className="w-3 h-3" />
          {formatBudget(budgetMin)}~{formatBudget(budgetMax)}
        </span>
      )}
    </div>
  );
}
