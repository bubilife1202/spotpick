"use client";

import { useState } from "react";
import { Coffee, Croissant, Camera, BookOpen, ArrowRight, ArrowLeft, Sparkles, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";

interface OnboardingProps {
  onComplete: (data: OnboardingData) => void;
  onSkip: () => void;
}

export interface OnboardingData {
  cafeType: string;
  budget: string;
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
  { id: "unknown", label: "잘 모르겠어요", desc: "AI가 추천", emoji: "❓" },
];

const DISTRICTS = [
  "강남", "서초", "마포", "용산", "성동", "송파",
  "영등포", "종로", "중구", "강서", "양천", "구로",
];

export function Onboarding({ onComplete, onSkip }: OnboardingProps) {
  const [step, setStep] = useState(1);
  const [data, setData] = useState<OnboardingData>({
    cafeType: "",
    budget: "",
    district: null,
  });

  const handleNext = () => {
    if (step < 3) {
      setStep(step + 1);
    } else {
      onComplete(data);
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  const canProceed = () => {
    switch (step) {
      case 1: return data.cafeType !== "";
      case 2: return data.budget !== "";
      case 3: return true;
      default: return false;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl overflow-hidden">
        <div className="px-6 py-4 bg-gradient-to-r from-blue-600 to-indigo-600">
          <div className="flex items-center justify-between text-white">
            <div className="flex items-center gap-2">
              <Sparkles size={20} />
              <span className="font-semibold">시작하기</span>
            </div>
            <div className="flex gap-1">
              {[1, 2, 3].map((s) => (
                <div
                  key={s}
                  className={cn(
                    "w-8 h-1 rounded-full transition-colors",
                    s <= step ? "bg-white" : "bg-white/30"
                  )}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="p-6">
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
                        "p-4 rounded-xl border-2 text-left transition-all",
                        data.cafeType === type.id
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      )}
                    >
                      <Icon
                        size={24}
                        className={cn(
                          "mb-2",
                          data.cafeType === type.id ? "text-blue-600" : "text-gray-400"
                        )}
                      />
                      <p className="font-medium text-gray-900">{type.label}</p>
                      <p className="text-xs text-gray-500">{type.desc}</p>
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
              <div className="grid grid-cols-2 gap-3">
                {BUDGETS.map((budget) => (
                  <button
                    key={budget.id}
                    onClick={() => setData({ ...data, budget: budget.id })}
                    className={cn(
                      "p-4 rounded-xl border-2 text-left transition-all",
                      data.budget === budget.id
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300"
                    )}
                  >
                    <span className="text-2xl">{budget.emoji}</span>
                    <p className="font-medium text-gray-900 mt-2">{budget.label}</p>
                    <p className="text-xs text-gray-500">{budget.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="text-center mb-6">
                <h2 className="text-xl font-bold text-gray-900">선호하는 지역이 있으세요?</h2>
                <p className="text-sm text-gray-500 mt-1">없으면 AI가 추천해드려요</p>
              </div>
              <div className="grid grid-cols-4 gap-2">
                {DISTRICTS.map((district) => (
                  <button
                    key={district}
                    onClick={() => setData({ ...data, district: data.district === district ? null : district })}
                    className={cn(
                      "py-2 px-3 rounded-lg text-sm font-medium transition-all",
                      data.district === district
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    )}
                  >
                    {district}
                  </button>
                ))}
              </div>
              <button
                onClick={() => setData({ ...data, district: null })}
                className={cn(
                  "w-full py-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2",
                  data.district === null
                    ? "bg-gradient-to-r from-blue-500 to-indigo-500 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                )}
              >
                <MapPin size={16} />
                잘 모르겠어요, AI가 추천해주세요
              </button>
            </div>
          )}
        </div>

        <div className="px-6 py-4 bg-gray-50 flex items-center justify-between">
          <button
            onClick={step === 1 ? onSkip : handleBack}
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            {step === 1 ? (
              "건너뛰기"
            ) : (
              <>
                <ArrowLeft size={16} />
                이전
              </>
            )}
          </button>
          <button
            onClick={handleNext}
            disabled={!canProceed()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {step === 3 ? "분석 시작!" : "다음"}
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
