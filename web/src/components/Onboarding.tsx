"use client";

import { useState } from "react";
import { Coffee, Croissant, Camera, BookOpen, ArrowRight, ArrowLeft, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { IndustrySelector } from "@/components/IndustrySelector";

interface OnboardingProps {
  onComplete: (data: OnboardingData) => void;
  onSkip: () => void;
}

export interface OnboardingData {
  industryCode: string;
  cafeType: string;
  budget: string;
  target: string;
  district: string | null;
}

const CAFE_TYPES = [
  { id: "takeout", icon: Coffee, label: "테이크아웃", desc: "빠른 회전율" },
  { id: "brunch", icon: Croissant, label: "브런치 카페", desc: "높은 객단가" },
  { id: "aesthetic", icon: Camera, label: "감성 카페", desc: "SNS 바이럴" },
  { id: "study", icon: BookOpen, label: "스터디 카페", desc: "장시간 체류" },
];

const BUDGETS = [
  { id: "low", label: "3천만원 이하", desc: "소규모 창업", emoji: "💰" },
  { id: "mid", label: "3천~1억", desc: "일반 창업", emoji: "💰💰" },
  { id: "high", label: "1억 이상", desc: "프리미엄", emoji: "💰💰💰" },
];

const TARGETS = [
  { id: "office", label: "직장인", desc: "점심·퇴근 피크", emoji: "💼" },
  { id: "20s_female", label: "20대 여성", desc: "SNS·감성 소비", emoji: "👩" },
  { id: "30s", label: "30~40대", desc: "안정적 소비층", emoji: "👔" },
  { id: "student", label: "대학생", desc: "가성비·장시간", emoji: "🎓" },
  { id: "local", label: "동네 주민", desc: "단골 위주", emoji: "🏘️" },
  { id: "tourist", label: "관광객", desc: "유동인구 높음", emoji: "🧳" },
];

const DISTRICTS = [
  "강남", "서초", "마포", "용산", "성동", "송파",
  "영등포", "종로", "중구", "강서", "양천", "구로",
];

const TOTAL_STEPS = 5;

// Steps where cafe-specific sub-type selection is shown
const CAFE_INDUSTRY_CODE = "CS100010";

export function Onboarding({ onComplete, onSkip }: OnboardingProps) {
  const [step, setStep] = useState(0);
  const [shakeStep, setShakeStep] = useState(false);
  const [data, setData] = useState<OnboardingData>({
    industryCode: "",
    cafeType: "",
    budget: "",
    target: "",
    district: null,
  });

  const isCafe = data.industryCode === CAFE_INDUSTRY_CODE;

  const handleNext = () => {
    if (step < TOTAL_STEPS - 1) {
      let nextStep = step + 1;
      // Skip cafe sub-type step (step 1) for non-cafe industries
      if (step === 0 && !isCafe) {
        nextStep = 2;
      }
      setStep(nextStep);
    } else {
      onComplete(data);
    }
  };

  const handleBack = () => {
    if (step > 0) {
      let prevStep = step - 1;
      // Skip cafe sub-type step (step 1) for non-cafe industries
      if (step === 2 && !isCafe) {
        prevStep = 0;
      }
      setStep(prevStep);
    }
  };

  const canProceed = () => {
    switch (step) {
      case 0: return data.industryCode !== "";
      case 1: return data.cafeType !== "";
      case 2: return data.budget !== "";
      case 3: return data.target !== "";
      case 4: return true;
      default: return false;
    }
  };

  const shakeMessage = () => {
    switch (step) {
      case 0: return "업종을 선택해주세요";
      case 1: return "카페 유형을 선택해주세요";
      case 2: return "예산을 선택해주세요";
      case 3: return "타겟 고객을 선택해주세요";
      default: return "";
    }
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
                    "w-6 h-1 rounded-full transition-colors sm:w-8",
                    s <= step ? "bg-white" : "bg-white/30"
                  )}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 sm:p-6">
          {step === 0 && (
            <div className="space-y-4">
              <div className="text-center mb-4 sm:mb-6">
                <h2 className="text-lg sm:text-xl font-bold text-gray-900">어떤 업종을 준비하세요?</h2>
                <p className="text-xs sm:text-sm text-gray-500 mt-1">업종에 따라 분석 기준이 달라져요</p>
              </div>
              <IndustrySelector
                value={data.industryCode}
                onChange={(code) => setData({ ...data, industryCode: code, cafeType: "" })}
              />
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-gray-900">어떤 카페를 꿈꾸세요?</h2>
                <p className="text-sm text-gray-500 mt-1">운영 스타일에 따라 추천이 달라져요</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {CAFE_TYPES.map((type) => {
                  const Icon = type.icon;
                  return (
                    <button
                      key={type.id}
                      onClick={() => setData({ ...data, cafeType: type.id })}
                      className={cn(
                        "p-3 sm:p-4 rounded-xl border-2 text-left transition-all active:scale-95",
                        data.cafeType === type.id
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      )}
                    >
                      <Icon
                        size={20}
                        className={cn(
                          "mb-2 sm:w-6 sm:h-6",
                          data.cafeType === type.id ? "text-blue-600" : "text-gray-400"
                        )}
                      />
                      <p className="font-medium text-sm sm:text-base text-gray-900">{type.label}</p>
                      <p className="text-[11px] sm:text-xs text-gray-500">{type.desc}</p>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-gray-900">예산은 어느 정도세요?</h2>
                <p className="text-sm text-gray-500 mt-1">보증금 + 인테리어 + 운영자금 기준</p>
              </div>
              <div className="grid grid-cols-1 gap-3">
                {BUDGETS.map((budget) => (
                  <button
                    key={budget.id}
                    onClick={() => setData({ ...data, budget: budget.id })}
                    className={cn(
                      "p-3 sm:p-4 rounded-xl border-2 text-left transition-all flex items-center gap-3 active:scale-98",
                      data.budget === budget.id
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300"
                    )}
                  >
                    <span className="text-xl sm:text-2xl">{budget.emoji}</span>
                    <div>
                      <p className="font-medium text-sm sm:text-base text-gray-900">{budget.label}</p>
                      <p className="text-[11px] sm:text-xs text-gray-500">{budget.desc}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-gray-900">주요 타겟 고객은?</h2>
                <p className="text-sm text-gray-500 mt-1">고객층에 따라 최적 입지가 달라져요</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {TARGETS.map((target) => (
                  <button
                    key={target.id}
                    onClick={() => setData({ ...data, target: target.id })}
                    className={cn(
                      "p-4 rounded-xl border-2 text-left transition-all",
                      data.target === target.id
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300"
                    )}
                  >
                    <span className="text-2xl">{target.emoji}</span>
                    <p className="font-medium text-gray-900 mt-2">{target.label}</p>
                    <p className="text-xs text-gray-500">{target.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-gray-900">선호하는 지역이 있으세요?</h2>
                <p className="text-sm text-gray-500 mt-1">선택 안 해도 분석 가능해요</p>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                {DISTRICTS.map((district) => (
                  <button
                    key={district}
                    onClick={() => setData({ ...data, district: data.district === district ? null : district })}
                    className={cn(
                      "py-2 px-2 sm:px-3 rounded-lg text-xs sm:text-sm font-medium transition-all active:scale-95",
                      data.district === district
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    )}
                  >
                    {district}
                  </button>
                ))}
              </div>
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
