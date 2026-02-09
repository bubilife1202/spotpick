"use client";

import { cn } from "@/lib/utils";
import { ANALYZE_STEPS, type AnalyzeStep } from "@/lib/analyze-store";
import { ClipboardList, FileBarChart, Rocket, Check } from "lucide-react";

const STEP_ICONS = [ClipboardList, FileBarChart, Rocket];

export function AnalyzeStepper({
  currentStep,
  className,
}: {
  currentStep: AnalyzeStep;
  className?: string;
}) {
  return (
    <div className={cn("w-full", className)}>
      <div className="mx-auto flex max-w-md items-center justify-between px-2">
        {ANALYZE_STEPS.map((s, i) => {
          const Icon = STEP_ICONS[i];
          const isCompleted = s.num < currentStep;
          const isCurrent = s.num === currentStep;
          const isFuture = s.num > currentStep;

          return (
            <div key={s.num} className="flex flex-1 items-center last:flex-none">
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full transition-all duration-300",
                    isCurrent &&
                      "scale-110 bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/30",
                    isCompleted && "bg-blue-100 text-blue-600",
                    isFuture && "bg-slate-100 text-slate-400",
                  )}
                >
                  {isCompleted ? (
                    <Check size={16} strokeWidth={3} />
                  ) : (
                    <Icon size={16} />
                  )}
                </div>
                <div className="text-center">
                  <p
                    className={cn(
                      "text-xs font-semibold",
                      isCurrent && "text-blue-600",
                      isCompleted && "text-blue-500",
                      isFuture && "text-slate-400",
                    )}
                  >
                    {s.label}
                  </p>
                  <p className="hidden text-[10px] text-slate-400 sm:block">
                    {s.short}
                  </p>
                </div>
              </div>

              {i < ANALYZE_STEPS.length - 1 && (
                <div
                  className={cn(
                    "mx-3 h-0.5 flex-1 rounded-full transition-colors duration-300 sm:mx-4",
                    isCompleted ? "bg-blue-300" : "bg-slate-200",
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
