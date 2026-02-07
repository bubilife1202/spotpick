"use client";

import { useState, useCallback } from "react";
import { ArrowRight, ArrowLeft, Sparkles, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import { IndustrySelector } from "@/components/IndustrySelector";

interface OnboardingProps {
  onComplete: (data: OnboardingData) => void;
  onSkip: () => void;
}

export interface OnboardingData {
  industryCode: string;
  rentMin: number;   // 만원 단위 (legacy, kept for compat)
  rentMax: number;   // 만원 단위 (legacy, kept for compat)
  budgetMin: number; // 만원 단위 (총 창업 예산)
  budgetMax: number; // 만원 단위 (총 창업 예산)
  districts: string[];
}

const DISTRICTS = [
  "서울 전체",
  "강남", "서초", "마포", "용산", "성동", "송파",
  "영등포", "종로", "중구", "강서", "양천", "구로",
  "관악", "동작", "서대문", "은평", "노원", "도봉",
  "강북", "성북", "동대문", "광진", "중랑", "강동", "금천",
];

const MAX_DISTRICTS = 3;
const TOTAL_STEPS = 3;

const BUDGET_MIN = 3000;   // 만원 (3천만원)
const BUDGET_MAX = 20000;  // 만원 (2억원)
const BUDGET_STEP = 1000;  // 만원 (1천만원)

export function Onboarding({ onComplete, onSkip }: OnboardingProps) {
  const [step, setStep] = useState(0);
  const [shakeStep, setShakeStep] = useState(false);
  const [data, setData] = useState<OnboardingData>({
    industryCode: "",
    rentMin: 0,
    rentMax: 0,
    budgetMin: 5000,
    budgetMax: 10000,
    districts: [],
  });

  const handleNext = () => {
    if (step < TOTAL_STEPS - 1) {
      setStep(step + 1);
    } else {
      onComplete(data);
    }
  };

  const handleBack = () => {
    if (step > 0) {
      setStep(step - 1);
    }
  };

  const canProceed = () => {
    switch (step) {
      case 0: return data.industryCode !== "";
      case 1: return true; // slider always has a value
      case 2: return true; // district is optional
      default: return false;
    }
  };

  const shakeMessage = () => {
    switch (step) {
      case 0: return "업종을 선택해주세요";
      default: return "";
    }
  };

  const toggleDistrict = useCallback((district: string) => {
    setData(prev => {
      if (district === "서울 전체") {
        // Toggle "서울 전체": if already selected, deselect; otherwise select only it
        if (prev.districts.includes("서울 전체")) {
          return { ...prev, districts: [] };
        }
        return { ...prev, districts: ["서울 전체"] };
      }

      // If "서울 전체" is currently selected, remove it and add the specific district
      const current = prev.districts.filter(d => d !== "서울 전체");

      if (current.includes(district)) {
        return { ...prev, districts: current.filter(d => d !== district) };
      }

      if (current.length >= MAX_DISTRICTS) {
        return prev;
      }

      return { ...prev, districts: [...current, district] };
    });
  }, []);

  const formatBudget = (value: number) => {
    if (value >= 10000) {
      const eok = value / 10000;
      if (eok === Math.floor(eok)) return `${Math.floor(eok)}억원`;
      return `${eok.toFixed(1)}억원`;
    }
    return `${value.toLocaleString()}만원`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-gradient-to-br from-blue-50 to-indigo-100">
      <style jsx>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          20%, 60% { transform: translateX(-4px); }
          40%, 80% { transform: translateX(4px); }
        }
        .animate-shake { animation: shake 0.4s ease-in-out; }
        input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
          border: 3px solid white;
          box-shadow: 0 2px 6px rgba(59,130,246,0.4);
          position: relative;
          z-index: 2;
        }
        input[type="range"]::-moz-range-thumb {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
          border: 3px solid white;
          box-shadow: 0 2px 6px rgba(59,130,246,0.4);
          position: relative;
          z-index: 2;
        }
        input[type="range"] {
          -webkit-appearance: none;
          appearance: none;
          width: 100%;
          height: 6px;
          border-radius: 3px;
          background: transparent;
          outline: none;
          pointer-events: none;
        }
        input[type="range"]::-webkit-slider-thumb {
          pointer-events: auto;
        }
        input[type="range"]::-moz-range-thumb {
          pointer-events: auto;
        }
      `}</style>
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] overflow-y-auto">
        <div className="px-4 py-3 sm:px-6 sm:py-4 bg-gradient-to-r from-blue-600 to-indigo-600">
          <div className="flex items-center justify-between text-white">
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="sm:w-5 sm:h-5" />
              <span className="font-semibold text-sm sm:text-base">시작하기</span>
            </div>
            <div className="flex gap-1">
              {Array.from({ length: TOTAL_STEPS }, (_, i) => i).map((s) => (
                <div
                  key={s}
                  className={cn(
                    "w-8 h-1.5 rounded-full transition-colors sm:w-10",
                    s <= step ? "bg-white" : "bg-white/30"
                  )}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 sm:p-6">
          {/* Step 0: 업종 선택 */}
          {step === 0 && (
            <div className="space-y-4">
              <div className="text-center mb-4 sm:mb-6">
                <h2 className="text-lg sm:text-xl font-bold text-gray-900">어떤 업종을 준비하세요?</h2>
                <p className="text-xs sm:text-sm text-gray-500 mt-1">업종에 따라 분석 기준이 달라져요</p>
              </div>
              <IndustrySelector
                value={data.industryCode}
                onChange={(code) => setData({ ...data, industryCode: code })}
              />
            </div>
          )}

          {/* Step 1: 총 창업 예산 range slider */}
          {step === 1 && (
            <div className="space-y-6">
              <div className="text-center mb-4 sm:mb-6">
                <h2 className="text-lg sm:text-xl font-bold text-gray-900">총 창업 예산은 어느 정도세요?</h2>
                <p className="text-xs sm:text-sm text-gray-500 mt-1">보증금 + 인테리어 + 장비 + 운영자금 포함</p>
              </div>

              {/* Display selected range */}
              <div className="text-center">
                <span className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-50 rounded-xl border border-blue-200">
                  <span className="text-lg sm:text-xl font-bold text-blue-700">
                    {formatBudget(data.budgetMin)} ~ {formatBudget(data.budgetMax)}
                  </span>
                </span>
              </div>

              {/* Dual range slider */}
              <div className="px-2 sm:px-4">
                <div className="relative h-6">
                  {/* Track background */}
                  <div className="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-1.5 bg-gray-200 rounded-full" />
                  {/* Active track */}
                  <div
                    className="absolute top-1/2 -translate-y-1/2 h-1.5 bg-blue-500 rounded-full"
                    style={{
                      left: `${((data.budgetMin - BUDGET_MIN) / (BUDGET_MAX - BUDGET_MIN)) * 100}%`,
                      right: `${100 - ((data.budgetMax - BUDGET_MIN) / (BUDGET_MAX - BUDGET_MIN)) * 100}%`,
                    }}
                  />
                  {/* Min slider */}
                  <input
                    type="range"
                    min={BUDGET_MIN}
                    max={BUDGET_MAX}
                    step={BUDGET_STEP}
                    value={data.budgetMin}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      if (val < data.budgetMax) {
                        setData({ ...data, budgetMin: val });
                      }
                    }}
                    className="absolute top-0 left-0 w-full"
                  />
                  {/* Max slider */}
                  <input
                    type="range"
                    min={BUDGET_MIN}
                    max={BUDGET_MAX}
                    step={BUDGET_STEP}
                    value={data.budgetMax}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      if (val > data.budgetMin) {
                        setData({ ...data, budgetMax: val });
                      }
                    }}
                    className="absolute top-0 left-0 w-full"
                  />
                </div>
                {/* Scale labels */}
                <div className="flex justify-between mt-2 text-[10px] sm:text-xs text-gray-400">
                  <span>{formatBudget(BUDGET_MIN)}</span>
                  <span>{formatBudget(7000)}</span>
                  <span>{formatBudget(11000)}</span>
                  <span>{formatBudget(15000)}</span>
                  <span>{formatBudget(BUDGET_MAX)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: 희망 지역 */}
          {step === 2 && (
            <div className="space-y-4">
              <div className="text-center mb-4 sm:mb-6">
                <h2 className="text-lg sm:text-xl font-bold text-gray-900">어디에서 창업하고 싶으세요?</h2>
                <p className="text-xs sm:text-sm text-gray-500 mt-1">최대 3개까지 선택 가능 (선택 안 해도 OK)</p>
              </div>
              <div className="grid grid-cols-4 sm:grid-cols-5 gap-2">
                {DISTRICTS.map((district) => {
                  const isSelected = data.districts.includes(district);
                  const isSeoulAll = district === "서울 전체";
                  const isDisabled = !isSelected && !isSeoulAll &&
                    data.districts.length >= MAX_DISTRICTS &&
                    !data.districts.includes("서울 전체");

                  return (
                    <button
                      key={district}
                      onClick={() => toggleDistrict(district)}
                      disabled={isDisabled}
                      className={cn(
                        "py-2 px-2 sm:px-3 rounded-lg text-xs sm:text-sm font-medium transition-all active:scale-95",
                        isSeoulAll && "col-span-2 sm:col-span-1",
                        isSelected
                          ? "bg-blue-600 text-white shadow-sm"
                          : isDisabled
                            ? "bg-gray-50 text-gray-300 cursor-not-allowed"
                            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                      )}
                    >
                      {isSeoulAll && <MapPin size={12} className="inline mr-1 -mt-0.5" />}
                      {district}
                    </button>
                  );
                })}
              </div>
              {data.districts.length > 0 && !data.districts.includes("서울 전체") && (
                <p className="text-center text-xs text-blue-600 font-medium">
                  {data.districts.join(", ")} 선택됨
                </p>
              )}
            </div>
          )}
        </div>

        {shakeStep && (
          <div className="px-6 pb-2 text-center">
            <p className="text-sm text-rose-500 font-medium animate-pulse">
              {shakeMessage()}
            </p>
          </div>
        )}
        <div className="px-4 py-3 sm:px-6 sm:py-4 bg-gray-50 flex items-center justify-between">
          <button
            onClick={step === 0 ? onSkip : handleBack}
            className="text-xs sm:text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 active:scale-95 transition-transform"
          >
            {step === 0 ? (
              "건너뛰기"
            ) : (
              <>
                <ArrowLeft size={14} className="sm:w-4 sm:h-4" />
                이전
              </>
            )}
          </button>
          <button
            onClick={() => {
              if (!canProceed()) {
                setShakeStep(true);
                setTimeout(() => setShakeStep(false), 600);
                return;
              }
              handleNext();
            }}
            className={cn(
              "px-5 py-2 sm:px-6 bg-blue-600 text-white rounded-lg text-sm sm:text-base font-medium hover:bg-blue-700 active:scale-95 flex items-center gap-2 transition-all",
              shakeStep && "animate-shake"
            )}
          >
            {step === TOTAL_STEPS - 1 ? "분석 시작!" : "다음"}
            <ArrowRight size={14} className="sm:w-4 sm:h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
