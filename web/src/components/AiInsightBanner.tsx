"use client";

import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface AiInsightBannerProps {
  message: string;
  className?: string;
  variant?: "blue" | "amber" | "emerald";
}

const VARIANT_STYLES = {
  blue: "from-blue-50 to-indigo-50 border-blue-200/60 text-blue-800",
  amber: "from-amber-50 to-orange-50 border-amber-200/60 text-amber-800",
  emerald: "from-emerald-50 to-teal-50 border-emerald-200/60 text-emerald-800",
};

const ICON_STYLES = {
  blue: "text-blue-500",
  amber: "text-amber-500",
  emerald: "text-emerald-500",
};

export function AiInsightBanner({
  message,
  className,
  variant = "blue",
}: AiInsightBannerProps) {
  if (!message) return null;

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-xl border bg-gradient-to-r px-4 py-3",
        VARIANT_STYLES[variant],
        className
      )}
    >
      <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
        <Sparkles className={cn("w-4 h-4", ICON_STYLES[variant])} />
        <span className="text-[10px] font-bold uppercase tracking-wider opacity-60">
          AI
        </span>
      </div>
      <p className="text-sm leading-relaxed font-medium">{message}</p>
    </div>
  );
}
