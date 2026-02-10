"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useAnalyzeStore } from "@/lib/analyze-store";
import { AnalyzeStepper } from "@/components/AnalyzeStepper";
import { MapPin, ArrowRight, Sparkles } from "lucide-react";

/* ────────────────────────────────────────────────────────────────────────────
   DATA
   ──────────────────────────────────────────────────────────────────────────── */

const INDUSTRY_OPTIONS = [
  { code: "CS100001", name: "한식", icon: "🍚" },
  { code: "CS100002", name: "중식", icon: "🥟" },
  { code: "CS100003", name: "일식", icon: "🍣" },
  { code: "CS100004", name: "양식", icon: "🍝" },
  { code: "CS100005", name: "베이커리", icon: "🍞" },
  { code: "CS100006", name: "패스트푸드", icon: "🍔" },
  { code: "CS100007", name: "치킨", icon: "🍗" },
  { code: "CS100008", name: "분식", icon: "🍜" },
  { code: "CS100009", name: "호프/주점", icon: "🍺" },
  { code: "CS100010", name: "카페", icon: "☕" },
];

const BUDGET_OPTIONS = [
  { label: "3천만원", value: 3000, desc: "소형 매장" },
  { label: "5천만원", value: 5000, desc: "표준 매장" },
  { label: "8천만원", value: 8000, desc: "현실 예산" },
  { label: "1억원", value: 10000, desc: "중형 매장" },
  { label: "2억원", value: 20000, desc: "대형 매장" },
];

const EXPERIENCE_OPTIONS = [
  { key: "beginner", emoji: "🌱", label: "처음이에요", desc: "외식업은 처음 도전합니다" },
  { key: "experienced", emoji: "💼", label: "경험 있어요", desc: "관련 업종에서 일한 적 있어요" },
  { key: "expert", emoji: "🏆", label: "전문가예요", desc: "직접 운영해본 경험이 있어요" },
];

const EMPLOYEE_OPTIONS = [
  { key: "solo", emoji: "👤", label: "1인 운영", desc: "혼자서 다 할 거예요" },
  { key: "1-2", emoji: "👥", label: "1-2명 고용", desc: "소규모 인원과 함께" },
  { key: "3+", emoji: "👥👥", label: "3명 이상", desc: "팀으로 운영할 계획이에요" },
];

const AREA_PRESETS = ["강남", "홍대/합정", "종로/을지로", "성수", "여의도", "잠실"];

const AI_QUESTIONS = [
  "어떤 업종으로 창업을 생각하고 계신가요?",
  "투자 가능한 총 예산은 얼마 정도인가요?",
  "외식업 경험이 있으신가요?",
  "혼자 운영하실 건가요?",
  "선호하는 지역이 있나요?",
];

/* ────────────────────────────────────────────────────────────────────────────
   HELPER COMPONENTS
   ──────────────────────────────────────────────────────────────────────────── */

function AiAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 shadow-md shadow-blue-500/20">
      <Sparkles className="h-4 w-4 text-white" />
    </div>
  );
}

function AiMessage({
  children,
  delay = 0,
}: {
  children: React.ReactNode;
  delay?: number;
}) {
  const [visible, setVisible] = useState(delay === 0);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (delay === 0) return;
    const t = setTimeout(() => {
      setVisible(true);
      setTimeout(() => {
        ref.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      }, 50);
    }, delay);
    return () => clearTimeout(t);
  }, [delay]);

  return (
    <div
      ref={ref}
      className={cn(
        "flex items-start gap-3 transition-all duration-500",
        visible
          ? "translate-y-0 opacity-100"
          : "pointer-events-none translate-y-4 opacity-0",
      )}
    >
      <AiAvatar />
      <div className="max-w-[85%] rounded-2xl rounded-tl-md border border-slate-200 bg-white px-5 py-4 shadow-sm">
        {children}
      </div>
    </div>
  );
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end animate-scale-in">
      <div className="rounded-2xl rounded-tr-md bg-blue-600 px-5 py-3 text-sm font-medium text-white shadow-md shadow-blue-600/20">
        {text}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3">
      <AiAvatar />
      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-md border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: "0ms" }} />
        <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: "150ms" }} />
        <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────────────────────
   MAIN PAGE
   ──────────────────────────────────────────────────────────────────────────── */

export default function AnalyzePage() {
  const router = useRouter();
  const store = useAnalyzeStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  const [budgetDraft, setBudgetDraft] = useState<number>(() => {
    const b = Number(store.budget || 5000);
    return Number.isFinite(b) && b > 0 ? b : 5000;
  });

  // Compute initial restored step from store
  const computeRestoredStep = useCallback(() => {
    if (store.preferredDistricts.length > 0 || (store.employeeCount && store.experienceLevel && store.budget)) {
      // If we have preferredDistricts OR all prior steps filled, check how far we got
      if (store.preferredDistricts.length > 0) return 6; // completed
      if (store.employeeCount) return 5;
    }
    if (store.employeeCount) return 5;
    if (store.experienceLevel) return 4;
    // budget defaults to 5000 and industry to CS100010, so only count if non-default
    return 0;
  }, [store.preferredDistricts, store.employeeCount, store.experienceLevel, store.budget]);

  const [chatStep, setChatStep] = useState(() => {
    const restored = computeRestoredStep();
    return restored > 0 ? restored : 0;
  });

  // Answers for display as user bubbles
  const [answers, setAnswers] = useState<Record<number, string>>(() => {
    const a: Record<number, string> = {};
    const restored = computeRestoredStep();
    if (restored >= 1) {
      const ind = INDUSTRY_OPTIONS.find((i) => i.code === store.industryCode);
      if (ind) a[1] = `${ind.icon} ${ind.name}`;
    }
    if (restored >= 2) {
      const b = BUDGET_OPTIONS.find((opt) => opt.value === store.budget);
      if (b) a[2] = b.label;
    }
    if (restored >= 3) {
      const e = EXPERIENCE_OPTIONS.find((opt) => opt.key === store.experienceLevel);
      if (e) a[3] = `${e.emoji} ${e.label}`;
    }
    if (restored >= 4) {
      const emp = EMPLOYEE_OPTIONS.find((opt) => opt.key === store.employeeCount);
      if (emp) a[4] = `${emp.emoji} ${emp.label}`;
    }
    if (restored >= 5) {
      a[5] = store.preferredDistricts.length > 0
        ? store.preferredDistricts.join(", ")
        : "AI가 추천";
    }
    return a;
  });

  const [showTyping, setShowTyping] = useState(false);
  const [readyStep, setReadyStep] = useState(chatStep);

  useEffect(() => {
    if (chatStep === 0) {
      setShowTyping(true);
      const t = setTimeout(() => {
        setShowTyping(false);
        setChatStep(1);
        setReadyStep(1);
      }, 800);
      return () => clearTimeout(t);
    }
  }, [chatStep]);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, 100);
  }, []);

  const advance = useCallback((step: number, answerText: string) => {
    setAnswers((prev) => ({ ...prev, [step]: answerText }));
    setShowTyping(true);
    scrollToBottom();
    const next = step + 1;
    setTimeout(() => {
      setShowTyping(false);
      if (next <= 5) {
        setChatStep(next);
        setReadyStep(next);
      } else {
        setChatStep(6);
        setReadyStep(6);
      }
      scrollToBottom();
    }, 600);
  }, [scrollToBottom]);

  /* ── Handlers ─────────────────────────────────────────────────────────── */

   const handleIndustry = (code: string) => {
     // Only allow cafe (CS100010)
     if (code !== "CS100010") return;
     store.setIndustry(code);
     const ind = INDUSTRY_OPTIONS.find((i) => i.code === code);
     advance(1, ind ? `${ind.icon} ${ind.name}` : code);
   };

  const handleBudget = (value: number) => {
    store.setBudget(value);
    const b = BUDGET_OPTIONS.find((opt) => opt.value === value);
    advance(2, b ? b.label : `${value}만원`);
  };

  const clampBudget = (v: number) => {
    const min = 1000;
    const max = 30000;
    if (!Number.isFinite(v)) return 5000;
    return Math.max(min, Math.min(max, Math.round(v / 100) * 100));
  };

  const handleExperience = (key: string) => {
    store.setExperienceLevel(key);
    const e = EXPERIENCE_OPTIONS.find((opt) => opt.key === key);
    advance(3, e ? `${e.emoji} ${e.label}` : key);
  };

  const handleEmployee = (key: string) => {
    store.setEmployeeCount(key);
    const emp = EMPLOYEE_OPTIONS.find((opt) => opt.key === key);
    advance(4, emp ? `${emp.emoji} ${emp.label}` : key);
  };

  const handleArea = (area: string | null) => {
    if (area) {
      store.setPreferredDistricts([area]);
      advance(5, area);
    } else {
      store.setPreferredDistricts([]);
      advance(5, "상관없어요 (AI가 추천)");
    }
  };

  const handleStartAnalysis = () => {
    store.setStep(2);
    const p = new URLSearchParams({
      industry_code: store.industryCode,
      budget: String(store.budget),
    });
    if (store.experienceLevel) p.set("experience_level", store.experienceLevel);
    if (store.employeeCount) p.set("employee_count", store.employeeCount);
    if (store.preferredDistricts.length > 0) {
      p.set("preferred_districts", store.preferredDistricts.join(","));
    }
    router.push(`/analyze/report?${p.toString()}`);
  };

  /* ── Render previously-answered Q&A pair ──────────────────────────────── */

  const renderAnswered = (step: number) => {
    if (!answers[step]) return null;
    return (
      <div key={`ans-${step}`} className="space-y-3">
        <AiMessage>
          <p className="text-sm font-medium text-slate-700">
            {AI_QUESTIONS[step - 1]}
          </p>
        </AiMessage>
        <UserBubble text={answers[step]} />
      </div>
    );
  };

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-slate-50 via-white to-slate-50/50">
      {/* ── Header ──────────────────────────────────────────────────────── */}
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

      {/* ── Stepper ─────────────────────────────────────────────────────── */}
      <div className="border-b border-slate-100 bg-white/60 backdrop-blur-sm">
        <div className="mx-auto max-w-2xl px-4 py-4 sm:px-6">
          <AnalyzeStepper currentStep={1} />
        </div>
      </div>

      {/* ── Chat Area ───────────────────────────────────────────────────── */}
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 pb-32 pt-8 sm:px-6">
        <div className="space-y-6">
          {/* Intro message */}
          <AiMessage delay={0}>
            <p className="text-sm font-semibold text-slate-800">
              안녕하세요! SpotPick AI 코치예요 👋
            </p>
            <p className="mt-1 text-sm text-slate-500">
              몇 가지 질문으로 당신에게 딱 맞는 상권을 찾아드릴게요.
              <span className="ml-1 text-xs font-medium text-slate-400">
                (현재 카페 업종만 완전 지원)
              </span>
            </p>
          </AiMessage>

          {/* Answered questions (chat history) */}
          {[1, 2, 3, 4, 5].map(
            (step) => step < chatStep && renderAnswered(step),
          )}

          {/* Typing indicator */}
          {showTyping && <TypingIndicator />}

          {/* ── Q1: Industry ──────────────────────────────────────────── */}
          {readyStep >= 1 && chatStep === 1 && !showTyping && (
            <div className="space-y-4 animate-slide-up">
              <AiMessage>
                <p className="text-sm font-medium text-slate-700">
                  {AI_QUESTIONS[0]}
                </p>
              </AiMessage>
               <div className="ml-11 grid grid-cols-2 gap-2 sm:grid-cols-5">
                 {INDUSTRY_OPTIONS.map((ind) => (
                   <button
                     key={ind.code}
                     type="button"
                     onClick={() => handleIndustry(ind.code)}
                     className={cn(
                       "relative flex flex-col items-center gap-1.5 rounded-xl border-2 border-slate-200 bg-white px-3 py-3 text-sm font-medium text-slate-600 transition-all duration-200 active:scale-95",
                       ind.code === "CS100010"
                         ? "hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700 hover:shadow-md"
                         : "opacity-40 cursor-not-allowed pointer-events-none"
                     )}
                   >
                     <span className="text-2xl">{ind.icon}</span>
                     <span className="text-xs font-semibold">{ind.name}</span>
                     {ind.code !== "CS100010" && (
                       <span className="absolute -right-1 -top-1 rounded-full bg-slate-400 px-1.5 py-0.5 text-[9px] font-bold text-white">
                         준비 중
                       </span>
                     )}
                   </button>
                 ))}
               </div>
            </div>
          )}

          {/* ── Q2: Budget ────────────────────────────────────────────── */}
          {readyStep >= 2 && chatStep === 2 && !showTyping && (
            <div className="space-y-4 animate-slide-up">
              <AiMessage>
                <p className="text-sm font-medium text-slate-700">
                  {AI_QUESTIONS[1]}
                </p>
              </AiMessage>
              <div className="ml-11 grid grid-cols-2 gap-3 sm:grid-cols-5">
                {BUDGET_OPTIONS.map((b) => (
                  <button
                    key={b.value}
                    type="button"
                    onClick={() => handleBudget(b.value)}
                    className="group flex flex-col items-center gap-1 rounded-xl border-2 border-slate-200 bg-white px-4 py-4 transition-all duration-200 hover:border-blue-400 hover:bg-blue-50 hover:shadow-md active:scale-95"
                  >
                    <span className="text-base font-bold text-slate-800 group-hover:text-blue-700">
                      {b.label}
                    </span>
                    <span className="text-[11px] font-medium text-slate-400 group-hover:text-blue-500">
                      {b.desc}
                    </span>
                  </button>
                ))}
              </div>

              <div className="ml-11 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      직접 입력
                    </p>
                    <p className="mt-1 text-sm font-extrabold text-slate-900">
                      {budgetDraft.toLocaleString()}만원
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      카페 서울 평균 창업비용 8,976만원 (KREI 2023)
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleBudget(clampBudget(budgetDraft))}
                    className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md active:scale-[0.98]"
                  >
                    이 값으로 선택
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>

                <div className="mt-4">
                  <input
                    type="range"
                    min={1000}
                    max={30000}
                    step={100}
                    value={budgetDraft}
                    onChange={(e) => setBudgetDraft(clampBudget(Number(e.target.value)))}
                    className="w-full"
                    aria-label="예산 슬라이더 (만원)"
                  />
                  <div className="mt-3 flex items-center gap-2">
                    <input
                      type="number"
                      value={budgetDraft}
                      onChange={(e) => setBudgetDraft(clampBudget(Number(e.target.value)))}
                      className="w-32 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-900 shadow-sm"
                      min={1000}
                      max={30000}
                      step={100}
                      inputMode="numeric"
                      aria-label="예산 직접 입력 (만원)"
                    />
                    <span className="text-sm font-semibold text-slate-500">만원</span>
                    <span className="text-xs text-slate-400">
                      (1,000~30,000)
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── Q3: Experience ────────────────────────────────────────── */}
          {readyStep >= 3 && chatStep === 3 && !showTyping && (
            <div className="space-y-4 animate-slide-up">
              <AiMessage>
                <p className="text-sm font-medium text-slate-700">
                  {AI_QUESTIONS[2]}
                </p>
              </AiMessage>
              <div className="ml-11 grid gap-2.5 sm:grid-cols-3">
                {EXPERIENCE_OPTIONS.map((opt) => (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => handleExperience(opt.key)}
                    className="flex flex-col items-start gap-1 rounded-xl border-2 border-slate-200 bg-white px-4 py-4 text-left transition-all duration-200 hover:border-blue-400 hover:bg-blue-50 hover:shadow-md active:scale-[0.98]"
                  >
                    <span className="text-xl">{opt.emoji}</span>
                    <span className="text-sm font-bold text-slate-800">
                      {opt.label}
                    </span>
                    <span className="text-xs text-slate-400">{opt.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── Q4: Employees ─────────────────────────────────────────── */}
          {readyStep >= 4 && chatStep === 4 && !showTyping && (
            <div className="space-y-4 animate-slide-up">
              <AiMessage>
                <p className="text-sm font-medium text-slate-700">
                  {AI_QUESTIONS[3]}
                </p>
              </AiMessage>
              <div className="ml-11 grid gap-2.5 sm:grid-cols-3">
                {EMPLOYEE_OPTIONS.map((opt) => (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => handleEmployee(opt.key)}
                    className="flex flex-col items-start gap-1 rounded-xl border-2 border-slate-200 bg-white px-4 py-4 text-left transition-all duration-200 hover:border-blue-400 hover:bg-blue-50 hover:shadow-md active:scale-[0.98]"
                  >
                    <span className="text-xl">{opt.emoji}</span>
                    <span className="text-sm font-bold text-slate-800">
                      {opt.label}
                    </span>
                    <span className="text-xs text-slate-400">{opt.desc}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── Q5: Area ──────────────────────────────────────────────── */}
          {readyStep >= 5 && chatStep === 5 && !showTyping && (
            <div className="space-y-4 animate-slide-up">
              <AiMessage>
                <p className="text-sm font-medium text-slate-700">
                  {AI_QUESTIONS[4]}
                </p>
              </AiMessage>
              <div className="ml-11 space-y-3">
                <div className="flex flex-wrap gap-2">
                  {AREA_PRESETS.map((area) => (
                    <button
                      key={area}
                      type="button"
                      onClick={() => handleArea(area)}
                      className="rounded-full border-2 border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 transition-all duration-200 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-700 hover:shadow-md active:scale-95"
                    >
                      {area}
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => handleArea(null)}
                  className="w-full rounded-xl border-2 border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-3 text-sm font-bold text-blue-700 transition-all duration-200 hover:border-blue-400 hover:shadow-md active:scale-[0.98]"
                >
                  ✨ 상관없어요 (AI가 추천)
                </button>
              </div>
            </div>
          )}

          {/* ── Completion: Summary + CTA ──────────────────────────────── */}
          {chatStep === 6 && !showTyping && (
            <div className="space-y-4 animate-slide-up">
              <AiMessage>
                <p className="text-sm font-semibold text-slate-800">
                  모든 준비가 끝났어요! 🎉
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  AI 코치가 분석을 준비하고 있어요...
                </p>
              </AiMessage>

              {/* Summary card */}
              <div className="ml-11 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg shadow-slate-200/50">
                <div className="border-b border-slate-100 bg-gradient-to-r from-blue-50 to-indigo-50 px-5 py-3">
                  <p className="text-xs font-bold uppercase tracking-wider text-blue-600">
                    분석 요약
                  </p>
                </div>
                <div className="divide-y divide-slate-100 px-5">
                  {[
                    { label: "업종", value: answers[1] },
                    { label: "예산", value: answers[2] },
                    { label: "경험", value: answers[3] },
                    { label: "인원", value: answers[4] },
                    { label: "지역", value: answers[5] },
                  ].map((row) => (
                    <div
                      key={row.label}
                      className="flex items-center justify-between py-3"
                    >
                      <span className="text-xs font-medium text-slate-400">
                        {row.label}
                      </span>
                      <span className="text-sm font-semibold text-slate-700">
                        {row.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* CTA */}
              <div className="ml-11">
                <button
                  type="button"
                  onClick={handleStartAnalysis}
                  className="flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 text-lg font-bold text-white shadow-lg shadow-blue-500/25 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/30 active:scale-[0.98]"
                >
                  <Sparkles className="h-5 w-5" />
                  AI 분석 시작하기
                  <ArrowRight className="h-5 w-5" />
                </button>
                <p className="mt-3 text-center text-xs text-slate-400">
                  서울 1,077개 상권 데이터 기반 AI 분석 (약 10초 소요)
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Scroll anchor */}
        <div ref={bottomRef} className="h-1" />
      </main>
    </div>
  );
}
