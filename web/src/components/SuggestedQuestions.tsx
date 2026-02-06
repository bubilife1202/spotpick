"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Sparkles, ChevronRight, MessageCircle, Zap, TrendingUp, MapPin, Lightbulb } from "lucide-react";
import { cn } from "@/lib/utils";

interface SuggestedQuestionsProps {
  questions: string[];
  onSelect: (question: string) => void;
  variant?: "default" | "minimal" | "inline";
  className?: string;
}

export function SuggestedQuestions({
  questions,
  onSelect,
  variant = "default",
  className,
}: SuggestedQuestionsProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);
  const [isVisible, setIsVisible] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Trigger entrance animation
    const timer = setTimeout(() => setIsVisible(true), 50);
    return () => clearTimeout(timer);
  }, []);

  const handleClick = useCallback(
    (question: string, index: number) => {
      setSelectedIndex(index);
      // Animate out then trigger callback
      setTimeout(() => {
        onSelect(question);
        setSelectedIndex(null);
      }, 250);
    },
    [onSelect]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      const maxIndex = Math.min(questions.length - 1, variant === "minimal" ? 2 : variant === "inline" ? 1 : questions.length - 1);

      switch (e.key) {
        case "ArrowDown":
        case "ArrowRight":
          e.preventDefault();
          setFocusedIndex((prev) => Math.min(prev + 1, maxIndex));
          break;
        case "ArrowUp":
        case "ArrowLeft":
          e.preventDefault();
          setFocusedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case "Enter":
        case " ":
          e.preventDefault();
          handleClick(questions[index], index);
          break;
        case "Escape":
          e.preventDefault();
          setFocusedIndex(-1);
          (e.target as HTMLElement).blur();
          break;
      }
    },
    [questions, variant, handleClick]
  );

  useEffect(() => {
    if (focusedIndex >= 0 && containerRef.current) {
      const buttons = containerRef.current.querySelectorAll("button");
      buttons[focusedIndex]?.focus();
    }
  }, [focusedIndex]);

  if (!questions || questions.length === 0) return null;

  // ─────────────────────────────────────────────────────────────────────────────
  // MINIMAL VARIANT: Compact pill buttons
  // ─────────────────────────────────────────────────────────────────────────────
  if (variant === "minimal") {
    return (
      <div
        ref={containerRef}
        role="group"
        aria-label="추천 질문"
        className={cn("flex flex-wrap gap-2", className)}
      >
        {questions.slice(0, 3).map((q, i) => (
          <button
            key={i}
            onClick={() => handleClick(q, i)}
            onKeyDown={(e) => handleKeyDown(e, i)}
            onFocus={() => setFocusedIndex(i)}
            tabIndex={0}
            aria-label={`추천 질문: ${q}`}
            className={cn(
              "text-xs px-3.5 py-2 rounded-full font-medium",
              "border transition-all duration-200 ease-out",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2",
              // Staggered entrance
              "opacity-0 translate-y-2",
              isVisible && "opacity-100 translate-y-0",
              // Selection state
              selectedIndex === i
                ? "bg-primary-600 text-white border-primary-600 scale-95 shadow-lg shadow-primary-500/30"
                : "bg-white/80 backdrop-blur-sm text-gray-600 border-gray-200/80 hover:border-primary-400 hover:text-primary-600 hover:bg-primary-50/50 hover:shadow-sm active:scale-95"
            )}
            style={{
              transitionDelay: isVisible ? `${i * 60}ms` : "0ms",
            }}
          >
            {q}
          </button>
        ))}
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // INLINE VARIANT: Text links with subtle icon
  // ─────────────────────────────────────────────────────────────────────────────
  if (variant === "inline") {
    return (
      <div
        ref={containerRef}
        role="group"
        aria-label="추천 질문"
        className={cn(
          "flex items-center gap-3 text-sm",
          "opacity-0 translate-y-1",
          isVisible && "opacity-100 translate-y-0 transition-all duration-300",
          className
        )}
      >
        <span className="flex items-center gap-1.5 text-amber-500">
          <Lightbulb size={14} className="fill-amber-200" />
        </span>
        {questions.slice(0, 2).map((q, i) => (
          <button
            key={i}
            onClick={() => handleClick(q, i)}
            onKeyDown={(e) => handleKeyDown(e, i)}
            onFocus={() => setFocusedIndex(i)}
            tabIndex={0}
            aria-label={`추천 질문: ${q}`}
            className={cn(
              "text-primary-600 hover:text-primary-700",
              "underline decoration-primary-300/50 underline-offset-2",
              "hover:decoration-primary-500 transition-colors duration-150",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:rounded-sm",
              selectedIndex === i && "text-primary-800 scale-95"
            )}
            style={{
              transitionDelay: `${i * 100 + 100}ms`,
            }}
          >
            {q}
          </button>
        ))}
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // DEFAULT VARIANT: Full card with glassmorphism
  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div
      ref={containerRef}
      role="group"
      aria-label="추천 질문"
      className={cn(
        "relative rounded-2xl p-4 overflow-hidden",
        // Glassmorphism background
        "bg-gradient-to-br from-gray-50/90 via-white/70 to-primary-50/50",
        "backdrop-blur-md border border-white/60",
        "shadow-[0_4px_24px_-4px_rgba(0,0,0,0.08),inset_0_1px_0_rgba(255,255,255,0.8)]",
        // Entrance animation
        "opacity-0 translate-y-3",
        isVisible && "opacity-100 translate-y-0 transition-all duration-400 ease-out",
        className
      )}
    >
      {/* Decorative gradient orb */}
      <div className="absolute -top-12 -right-12 w-32 h-32 bg-gradient-to-br from-primary-400/20 to-indigo-400/20 rounded-full blur-2xl pointer-events-none" />
      
      {/* Header */}
      <div className="flex items-center gap-2.5 mb-3 relative">
        <div className="flex items-center justify-center w-7 h-7 rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 shadow-lg shadow-amber-500/25">
          <Sparkles size={14} className="text-white" />
        </div>
        <span className="text-sm font-semibold text-gray-700 tracking-tight">
          이런 질문은 어때요?
        </span>
      </div>

      {/* Question list */}
      <div className="space-y-2 relative">
        {questions.map((question, index) => (
          <button
            key={index}
            onClick={() => handleClick(question, index)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            onFocus={() => setFocusedIndex(index)}
            tabIndex={0}
            aria-label={`추천 질문: ${question}`}
            className={cn(
              "group w-full flex items-center justify-between gap-3",
              "p-3 rounded-xl text-left",
              "transition-all duration-200 ease-out",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-1",
              // Staggered entrance
              "opacity-0 translate-x-[-8px]",
              isVisible && "opacity-100 translate-x-0",
              // Selection/hover states
              selectedIndex === index
                ? "bg-primary-600 text-white shadow-lg shadow-primary-500/30 scale-[0.98]"
                : "bg-white/70 hover:bg-white text-gray-700 border border-gray-100/80 hover:border-primary-200 hover:shadow-md active:scale-[0.98]"
            )}
            style={{
              transitionDelay: isVisible ? `${index * 80 + 100}ms` : "0ms",
            }}
          >
            <div className="flex items-center gap-3 min-w-0">
              <div
                className={cn(
                  "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-200",
                  selectedIndex === index
                    ? "bg-white/20"
                    : "bg-primary-50 group-hover:bg-primary-100"
                )}
              >
                <MessageCircle
                  size={15}
                  className={cn(
                    "transition-colors duration-200",
                    selectedIndex === index
                      ? "text-white"
                      : "text-primary-500 group-hover:text-primary-600"
                  )}
                />
              </div>
              <span className="text-sm font-medium truncate">{question}</span>
            </div>
            <ChevronRight
              size={16}
              className={cn(
                "flex-shrink-0 transition-all duration-200",
                selectedIndex === index
                  ? "text-white/80 translate-x-0.5"
                  : "text-gray-300 group-hover:text-primary-500 group-hover:translate-x-0.5"
              )}
            />
          </button>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// INITIAL QUESTIONS: Hero component for onboarding / empty state
// ─────────────────────────────────────────────────────────────────────────────
const INITIAL_QUESTION_ICONS = [TrendingUp, MapPin, Zap, MapPin, TrendingUp] as const;

export function InitialQuestions({ onSelect }: { onSelect: (q: string) => void }) {
  const [isVisible, setIsVisible] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  const initialQuestions = [
    "서울 강남에서 월세 300~400만원으로 카페 창업 추천해줘",
    "서울 홍대에서 20대 여성 타겟 카페 상권 추천해줘",
    "서울에서 직장인 점심(11-14) 피크 상권 추천해줘",
    "서울 홍대 vs 성수 상권 비교해줘",
    "서울 성수에서 골목상권 + 월세 200~300만원 추천해줘",
  ];

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const handleClick = useCallback(
    (question: string, index: number) => {
      setSelectedIndex(index);
      setTimeout(() => {
        onSelect(question);
      }, 300);
    },
    [onSelect]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setFocusedIndex((prev) => Math.min(prev + 1, initialQuestions.length - 1));
          break;
        case "ArrowUp":
          e.preventDefault();
          setFocusedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case "Enter":
        case " ":
          e.preventDefault();
          handleClick(initialQuestions[index], index);
          break;
      }
    },
    [handleClick, initialQuestions]
  );

  useEffect(() => {
    if (focusedIndex >= 0 && containerRef.current) {
      const buttons = containerRef.current.querySelectorAll("button");
      buttons[focusedIndex]?.focus();
    }
  }, [focusedIndex]);

  return (
    <div ref={containerRef} className="w-full max-w-lg" role="group" aria-label="시작 질문">
      <div className="space-y-2.5">
        {initialQuestions.map((q, i) => {
          const Icon = INITIAL_QUESTION_ICONS[i % INITIAL_QUESTION_ICONS.length];
          return (
            <button
              key={i}
              onClick={() => handleClick(q, i)}
              onKeyDown={(e) => handleKeyDown(e, i)}
              onFocus={() => setFocusedIndex(i)}
              tabIndex={0}
              aria-label={`질문: ${q}`}
              className={cn(
                "group w-full p-3.5 rounded-xl text-left",
                "transition-all duration-300 ease-out",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2",
                "opacity-0 translate-y-3",
                isVisible && "opacity-100 translate-y-0",
                selectedIndex === i
                  ? "bg-primary-600 text-white shadow-xl shadow-primary-500/40 scale-[0.98]"
                  : "bg-white border border-gray-100 hover:border-primary-300 hover:shadow-lg hover:shadow-primary-500/10 active:scale-[0.98]"
              )}
              style={{
                transitionDelay: isVisible ? `${i * 60 + 100}ms` : "0ms",
              }}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={cn(
                      "flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-200",
                      selectedIndex === i
                        ? "bg-white/20"
                        : "bg-gradient-to-br from-primary-50 to-blue-50 group-hover:from-primary-100 group-hover:to-blue-100"
                    )}
                  >
                    <Icon
                      size={16}
                      className={cn(
                        "transition-colors duration-200",
                        selectedIndex === i
                          ? "text-white"
                          : "text-primary-500 group-hover:text-primary-600"
                      )}
                    />
                  </div>
                  <span
                    className={cn(
                      "text-sm font-medium leading-snug",
                      selectedIndex === i ? "text-white" : "text-gray-700 group-hover:text-gray-900"
                    )}
                  >
                    {q}
                  </span>
                </div>
                <ChevronRight
                  size={16}
                  className={cn(
                    "flex-shrink-0 transition-all duration-200",
                    selectedIndex === i
                      ? "text-white/80 translate-x-1"
                      : "text-gray-300 group-hover:text-primary-500 group-hover:translate-x-1"
                  )}
                />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
