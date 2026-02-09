"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useAnalyzeStore } from "@/lib/analyze-store";
import { useJourneyStore, INDUSTRY_NAMES, INDUSTRY_ICONS } from "@/lib/journey-store";
import { AnalyzeStepper } from "@/components/AnalyzeStepper";
import {
  MapPin,
  ArrowRight,
  Sparkles,
  Wallet,
} from "lucide-react";

const INDUSTRY_OPTIONS = Object.entries(INDUSTRY_NAMES).map(([code, name]) => ({
  code,
  name,
  icon: INDUSTRY_ICONS[code] || "🍽️",
}));

const BUDGET_PRESETS = [
  { label: "3천만원", value: 3000 },
  { label: "5천만원", value: 5000 },
  { label: "1억원", value: 10000 },
  { label: "2억원", value: 20000 },
];

export default function AnalyzePage() {
  const router = useRouter();
  const analyzeStore = useAnalyzeStore();
  const journeyStore = useJourneyStore();

  const [selectedIndustry, setSelectedIndustry] = useState(analyzeStore.industryCode);
  const [budget, setBudget] = useState(analyzeStore.budget);

  const handleStart = () => {
    const finalBudget = budget || 5000;
    // Save to analyze store
    analyzeStore.setIndustry(selectedIndustry);
    analyzeStore.setBudget(finalBudget);
    analyzeStore.setStep(2);

    // Sync with journey store for backward compatibility
    journeyStore.setIndustry(selectedIndustry);
    journeyStore.setBudget(finalBudget);

    const params = new URLSearchParams({
      industry_code: selectedIndustry,
      budget: String(finalBudget),
    });
    router.push(`/analyze/report?${params.toString()}`);
  };

  const selectedPreset = BUDGET_PRESETS.find(
    (p) => p.value === budget,
  );

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600">
              <MapPin className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-bold text-slate-900">SpotPick</span>
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-4 pb-20 pt-10 sm:px-6">
        {/* Stepper */}
        <AnalyzeStepper currentStep={1} className="mb-10" />

        {/* Title */}
        <div className="mb-8 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            <Sparkles className="h-3.5 w-3.5" />
            30초 만에 시작
          </span>
          <h1 className="mt-3 text-3xl font-extrabold text-slate-900 sm:text-4xl">
            창업 분석 시작하기
          </h1>
          <p className="mx-auto mt-2 max-w-lg text-base text-slate-500">
            업종과 예산만 입력하면 AI가 최적 상권을 찾아드립니다
          </p>
        </div>

        {/* Industry Selection */}
        <div className="mb-8">
          <label className="mb-3 block text-sm font-bold text-slate-700">
            어떤 업종으로 창업하시나요?
          </label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            {INDUSTRY_OPTIONS.map((ind) => (
              <button
                key={ind.code}
                onClick={() => setSelectedIndustry(ind.code)}
                className={cn(
                  "flex flex-col items-center gap-1 rounded-xl border-2 px-3 py-3 text-sm font-medium transition",
                  selectedIndustry === ind.code
                    ? "border-blue-500 bg-blue-50 text-blue-700 shadow-sm"
                    : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50",
                )}
              >
                <span className="text-2xl">{ind.icon}</span>
                <span className="text-xs font-semibold">{ind.name}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Budget Selection */}
        <div className="mb-8">
          <label className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-700">
            <Wallet className="h-4 w-4 text-slate-400" />
            총 투자 예산은 얼마인가요?
          </label>

          <div className="space-y-3">
              <div className="grid grid-cols-4 gap-2">
                {BUDGET_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    onClick={() => setBudget(preset.value)}
                    className={cn(
                      "rounded-xl border-2 px-4 py-3 text-sm font-semibold transition",
                      selectedPreset?.label === preset.label
                        ? "border-blue-500 bg-blue-50 text-blue-700"
                        : "border-slate-200 bg-white text-slate-600 hover:border-slate-300",
                    )}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
              <div className="relative max-w-xs">
                <input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(Number(e.target.value))}
                  className="w-full rounded-lg border border-slate-200 px-3 py-2.5 pr-12 text-sm focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-100"
                  min={1000}
                  step={1000}
                  placeholder="예: 5000"
                />
                <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-slate-400">만원</span>
              </div>
            </div>
        </div>

        {/* Start Button */}
        <button
          onClick={handleStart}
          className="flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 text-lg font-bold text-white shadow-lg shadow-blue-500/25 transition hover:shadow-xl hover:shadow-blue-500/30"
        >
          <Sparkles className="h-5 w-5" />
          AI 분석 시작
          <ArrowRight className="h-5 w-5" />
        </button>

        <p className="mt-4 text-center text-xs text-slate-400">
          서울 1,077개 상권 데이터 기반 AI 분석 (약 10초 소요)
        </p>
      </main>
    </div>
  );
}
