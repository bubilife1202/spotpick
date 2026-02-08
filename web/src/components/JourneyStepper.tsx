"use client";

import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useJourneyStore, JOURNEY_STEPS, type JourneyStep } from "@/lib/journey-store";
import {
  Search,
  GitCompare,
  MapPin,
  BarChart3,
  SlidersHorizontal,
  BadgeDollarSign,
  FileText,
  Check,
} from "lucide-react";

const STEP_ICONS = [Search, GitCompare, MapPin, BarChart3, SlidersHorizontal, BadgeDollarSign, FileText];

const STEP_ROUTES: Record<JourneyStep, string> = {
  1: "/",
  2: "/franchise",
  3: "/results",
  4: "/report",
  5: "/simulator",
  6: "/support",
  7: "/business-plan",
};

export function JourneyStepper({ className }: { className?: string }) {
  const router = useRouter();
  const { step: currentStep, selectedDistrict, industryCode } = useJourneyStore();

  const handleStepClick = (targetStep: JourneyStep) => {
    if (targetStep === currentStep) return;

    let route = STEP_ROUTES[targetStep];

    // Franchise step only needs industry_code
    if (targetStep === 2) {
      route = `/franchise?industry_code=${industryCode}`;
    } else if (selectedDistrict && targetStep >= 4) {
      // Steps 4+ (report, simulator, support, business-plan) need district & industry params
      const p = new URLSearchParams();
      p.set("district_code", selectedDistrict.district_code);
      p.set("industry_code", industryCode);
      if (targetStep === 6) {
        const { budgetMin, budgetMax } = useJourneyStore.getState();
        p.set("budget_min", String(budgetMin));
        p.set("budget_max", String(budgetMax));
      }
      route = `${STEP_ROUTES[targetStep]}?${p.toString()}`;
    }

    useJourneyStore.getState().setStep(targetStep);
    router.push(route);
  };

  return (
    <div className={cn("w-full", className)}>
      <div className="flex items-center justify-between max-w-xl mx-auto px-2">
        {JOURNEY_STEPS.map((s, i) => {
          const Icon = STEP_ICONS[i];
          const isCompleted = s.num < currentStep;
          const isCurrent = s.num === currentStep;
          const isFuture = s.num > currentStep;

          return (
            <div key={s.num} className="flex items-center flex-1 last:flex-none">
              <button
                onClick={() => handleStepClick(s.num)}
                className={cn(
                  "flex flex-col items-center gap-1 group transition-all duration-200",
                  isFuture ? "opacity-40 cursor-default" : "cursor-pointer"
                )}
                disabled={isFuture}
              >
                <div className={cn(
                  "w-8 h-8 sm:w-9 sm:h-9 rounded-full flex items-center justify-center transition-all duration-300",
                  isCurrent && "bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/30 scale-110",
                  isCompleted && "bg-blue-100 text-blue-600 group-hover:bg-blue-200",
                  isFuture && "bg-slate-100 text-slate-400"
                )}>
                  {isCompleted ? <Check size={14} strokeWidth={3} /> : <Icon size={14} />}
                </div>
                <span className={cn(
                  "text-[10px] sm:text-[11px] font-medium whitespace-nowrap",
                  isCurrent && "text-blue-600 font-semibold",
                  isCompleted && "text-blue-500",
                  isFuture && "text-slate-400"
                )}>
                  {s.label}
                </span>
              </button>

              {i < JOURNEY_STEPS.length - 1 && (
                <div className={cn(
                  "flex-1 h-0.5 mx-1 sm:mx-2 -mt-4 rounded-full transition-colors duration-300",
                  isCompleted ? "bg-blue-300" : "bg-slate-200"
                )} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function JourneyStepperCompact({ className }: { className?: string }) {
  const { step: currentStep } = useJourneyStore();

  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      {JOURNEY_STEPS.map((s) => (
        <div
          key={s.num}
          className={cn(
            "h-1 rounded-full transition-all duration-300",
            s.num === currentStep ? "w-6 bg-blue-500" :
            s.num < currentStep ? "w-3 bg-blue-300" : "w-3 bg-slate-200"
          )}
        />
      ))}
      <span className="text-[10px] text-slate-500 ml-1">
        STEP {currentStep}/{JOURNEY_STEPS.length}
      </span>
    </div>
  );
}
