"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Coffee, Send, Bot, User, BarChart3, MapPin } from "lucide-react";
import { ChatMessage, StructuredChatResponse, RecommendationCardData } from "@/types/chat";
import { SuggestedQuestions, InitialQuestions } from "@/components/SuggestedQuestions";
import { ChatChartSection } from "@/components/ChatChart";
import type { ChartData } from "@/types/chat";
import { RecommendationCard } from "@/components/RecommendationCard";
import { sendStructuredChatMessage, GLOSSARY } from "@/lib/chat-api";
import { LocationRecommendation } from "@/lib/api";
import { cn } from "@/lib/utils";
import dynamic from "next/dynamic";
import SearchMode from "@/components/SearchMode";
import { Onboarding, OnboardingData } from "@/components/Onboarding";

const MapView = dynamic(() => import("@/components/MapView"), {
  ssr: false,
  loading: () => (
    <div className="w-full min-h-[280px] flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
      <div className="text-center text-gray-500">
        <MapPin size={40} className="mx-auto mb-2 opacity-60 animate-pulse" />
        <p className="text-sm">지도 로딩 중...</p>
      </div>
    </div>
  ),
});

function ChatHome({ onSwitchToSearch, initialQuery }: { onSwitchToSearch: () => void; initialQuery?: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const initialQuerySent = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const makeKakaoMapUrl = (query: string) =>
    `https://map.kakao.com/link/search/${encodeURIComponent(query)}`;

  // Initialize welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        id: "welcome",
        role: "assistant",
        content: [
          "안녕하세요! 커피숍 창업 AI 컨설턴트 **빌더**입니다.",
          "",
          "현재 베타 서비스는 **서울 지역 데이터만** 지원합니다.",
          "",
          "**질문 작성 팁**",
          "- 지역: 서울 + 구/동/역 (예: 강남, 홍대, 성수)",
          "- 월세 예산: 200~400만원 (예: 300만원대)",
          "- 옵션: 타겟(20대/직장인/여성), 시간대(오전/점심/저녁), 상권 유형(골목/발달)",
          "",
          "**예시**",
          "- 서울 강남에서 월세 300~400만원, 직장인 점심 타겟 상권 추천해줘",
          "- 서울 성수 골목상권에서 월세 200~300만원 추천해줘",
        ].join("\n"),
        timestamp: new Date(),
      }]);
    }
  }, [messages.length]);

  useEffect(() => {
    if (initialQuery && !initialQuerySent.current && messages.length > 0) {
      initialQuerySent.current = true;
      handleSend(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery, messages.length]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (hasStarted) {
      inputRef.current?.focus();
    }
  }, [hasStarted]);

  // Convert RecommendationCardData to LocationRecommendation for RecommendationCard
  const convertToLocationRecommendation = (rec: RecommendationCardData): LocationRecommendation => ({
    rank: rec.rank,
    lat: rec.coordinates?.lat || 37.5665,
    lng: rec.coordinates?.lng || 126.9780,
    address: rec.address || "",
    area_name: rec.district_name,
    area_type: rec.district_type,
    success_probability: rec.success_probability,
    confidence: 0.8,
    estimated_monthly_rent: rec.estimated_rent,
    estimated_monthly_sales: rec.monthly_sales,
    survival_rate_2y: rec.survival_rate,
    risk_factors: rec.risk_factors,
    recommendations: rec.recommendations,
    key_success_factors: rec.key_success_factors || [],
    nearby_successful_stores: [],
    area_stats: {
      floating_population: 0,
      competitor_count: rec.store_count || 0,
      survival_rate_1y: (rec.survival_rate || 0.8) + 0.05,
      survival_rate_3y: (rec.survival_rate || 0.8) - 0.05,
    },
    time_analysis: rec.peak_time ? {
      peak_time: rec.peak_time,
      time_00_06: 0,
      time_06_11: 0,
      time_11_14: 0,
      time_14_17: 0,
      time_17_21: 0,
      time_21_24: 0,
    } : undefined,
    customer_analysis: rec.main_age_group ? {
      main_age_group: rec.main_age_group,
      male_ratio: 0.4,
      female_ratio: 0.6,
      age_10: 0,
      age_20: 0,
      age_30: 0,
      age_40: 0,
      age_50: 0,
      age_60: 0,
    } : undefined,
  });

  const handleSend = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || isLoading) return;

    setHasStarted(true);
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: messageText,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response: StructuredChatResponse = await sendStructuredChatMessage(messageText, messages);
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.reply,
        timestamp: new Date(),
        structured: {
          recommendations: response.recommendations,
          charts: response.charts,
          suggestedQuestions: response.suggested_questions,
        },
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "죄송합니다, 일시적인 오류가 발생했습니다. 다시 시도해주세요.",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInitialQuestion = (question: string) => {
    setHasStarted(true);
    handleSend(question);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Process content with glossary terms and markdown
  const renderMessageContent = (content: string) => {
    let processedContent = content;
    
    Object.keys(GLOSSARY).forEach((term) => {
      const regex = new RegExp(`(${term})`, "g");
      processedContent = processedContent.replace(
        regex,
        `<span class="glossary-term underline decoration-dotted decoration-blue-400 cursor-help" title="${GLOSSARY[term]}">$1</span>`
      );
    });

    processedContent = processedContent
      .replace(/\*\*(.*?)\*\*/g, "<strong class='font-semibold text-gray-900'>$1</strong>")
      .replace(/\n/g, "<br />");

    return (
      <div
        className="prose prose-sm max-w-none text-gray-700 leading-relaxed"
        dangerouslySetInnerHTML={{ __html: processedContent }}
      />
    );
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-blue-50/30">
      {/* Header */}
      <header className="bg-white/95 backdrop-blur-sm shadow-sm sticky top-0 z-40 border-b border-gray-100/50">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/25">
                <Coffee className="text-white" size={20} />
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-400 rounded-full border-2 border-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-gray-900 tracking-tight">Builder Curation</h1>
              <p className="text-xs text-gray-500">AI 창업 컨설턴트</p>
            </div>
          </div>

          <button
            onClick={onSwitchToSearch}
            className="text-sm font-medium text-gray-700 hover:text-gray-900 px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors"
            title="고급 기능: 조건 검색, 지도/카드 비교"
          >
            검색/비교
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="relative max-w-3xl mx-auto px-4">
        {!hasStarted ? (
          // Initial screen with hero and suggested questions
          <div className="py-10 sm:py-14 flex flex-col items-center">
            {/* Stats badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 mb-5 bg-white rounded-full shadow-md border border-gray-100/80">
              <BarChart3 size={14} className="text-blue-500" />
              <span className="text-sm font-medium text-gray-700">
                <span className="text-blue-600 font-bold">1,077</span>개 상권 · 
                <span className="text-blue-600 font-bold"> 64</span>개 분석 지표
              </span>
            </div>

            {/* Hero title */}
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3 tracking-tight text-center">
              커피숍 창업,<br className="sm:hidden" /> 어디서 해야 성공할까?
            </h2>
            <p className="text-gray-600 max-w-md mx-auto text-center mb-2">
              서울시 6년간 데이터를 AI가 분석했습니다.<br />
              <span className="text-blue-600 font-medium">자연어로 질문</span>하면 맞춤 분석을 제공합니다.
            </p>
            <p className="text-xs text-gray-400 mb-8 text-center">
              작성 팁: <span className="font-medium text-gray-500">서울 + 지역 + 월세 예산</span> + (선택) 타겟/시간대/상권유형
            </p>

            {/* Initial questions */}
            <InitialQuestions onSelect={handleInitialQuestion} />

            {/* Input bar */}
            <div className="w-full max-w-lg mt-8">
              <div className="relative">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="또는 직접 질문해보세요..."
                  className={cn(
                    "w-full pl-5 pr-14 py-4 text-sm",
                    "bg-white border-2 border-gray-100 rounded-2xl",
                    "focus:outline-none focus:border-blue-400 focus:ring-4 focus:ring-blue-100",
                    "shadow-lg shadow-gray-100/50",
                    "placeholder:text-gray-400",
                    "transition-all duration-200"
                  )}
                />
                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim()}
                  className={cn(
                    "absolute right-2 top-1/2 -translate-y-1/2",
                    "w-10 h-10 rounded-xl",
                    "flex items-center justify-center",
                    "transition-all duration-200",
                    input.trim()
                      ? "bg-blue-500 text-white hover:bg-blue-600 shadow-md"
                      : "bg-gray-100 text-gray-400"
                  )}
                >
                  <Send size={18} />
                </button>
              </div>
            </div>
          </div>
        ) : (
          // Chat interface after conversation starts
          <div className="flex flex-col h-[calc(100vh-73px)]">
            {/* Messages area */}
            <div className="flex-1 overflow-y-auto py-6 space-y-5">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    "flex gap-3",
                    message.role === "user" ? "justify-end" : "justify-start"
                  )}
                >
                  {/* Assistant avatar */}
                  {message.role === "assistant" && (
                    <div className="flex-shrink-0">
                      <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md">
                        <Bot size={18} className="text-white" />
                      </div>
                    </div>
                  )}
                  
                  {/* Message bubble */}
                  <div
                    className={cn(
                      "max-w-[85%] sm:max-w-[75%]",
                      message.role === "user"
                        ? "bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl rounded-br-md px-4 py-3 shadow-lg shadow-blue-500/20"
                        : "bg-white border border-gray-100 rounded-2xl rounded-bl-md p-4 shadow-md"
                    )}
                  >
                    {/* Text content */}
                    {message.role === "assistant" 
                      ? renderMessageContent(message.content)
                      : <p className="text-sm leading-relaxed">{message.content}</p>
                    }
                    
                    {/* Structured data: Recommendations */}
                    {message.structured?.recommendations && message.structured.recommendations.length > 0 && (
                      <div className="mt-4 space-y-3">
                        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                          추천 상권
                        </div>
                        {message.structured.recommendations.slice(0, 3).map((rec, i) => (
                          <RecommendationCard 
                            key={i} 
                            recommendation={convertToLocationRecommendation(rec)}
                            compact 
                            onAskAI={handleSend}
                          />
                        ))}
                      </div>
                    )}

                    {/* Structured data: Map */}
                    {message.structured?.recommendations && message.structured.recommendations.length > 0 && (() => {
                      const top = message.structured!.recommendations.slice(0, 3);
                      const locations = top
                        .filter((r) => !!r.coordinates)
                        .map((r) => ({
                          lat: r.coordinates!.lat,
                          lng: r.coordinates!.lng,
                          name: r.district_name,
                          rank: r.rank,
                        }));

                      const links = (
                        <div className="flex flex-wrap gap-2">
                          {top.map((r) => {
                            const q = r.address || `서울 ${r.district_name}`;
                            const url = makeKakaoMapUrl(q);
                            return (
                              <a
                                key={`map-${r.rank}`}
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs px-2.5 py-1.5 bg-white border border-gray-200 rounded-full text-gray-700 hover:bg-gray-50 transition-colors"
                              >
                                <MapPin size={12} className="text-blue-600" />
                                <span>카카오맵: {r.district_name}</span>
                              </a>
                            );
                          })}
                        </div>
                      );

                      if (locations.length === 0) {
                        return (
                          <div className="mt-4 space-y-2">
                            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                              지도
                            </div>
                            <p className="text-xs text-gray-500">
                              지도 좌표를 찾지 못해 외부 지도 링크로 안내합니다.
                            </p>
                            {links}
                          </div>
                        );
                      }

                      return (
                        <div className="mt-4 space-y-2">
                          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                            지도
                          </div>
                          <div className="rounded-xl overflow-hidden">
                            <MapView
                              locations={locations}
                              selectedLocation={null}
                              onLocationSelect={() => {}}
                            />
                          </div>
                          {links}
                        </div>
                      );
                    })()}
                    
                    {/* Structured data: Charts */}
                    {message.structured?.charts && message.structured.charts.length > 0 && (
                      <div className="mt-4">
                        <ChatChartSection charts={message.structured.charts as ChartData[]} />
                      </div>
                    )}
                    
                    {/* Structured data: Suggested questions */}
                    {message.structured?.suggestedQuestions && message.structured.suggestedQuestions.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-gray-100">
                        <SuggestedQuestions 
                          questions={message.structured.suggestedQuestions}
                          onSelect={handleSend}
                          variant="minimal"
                        />
                      </div>
                    )}
                  </div>

                  {/* User avatar */}
                  {message.role === "user" && (
                    <div className="flex-shrink-0">
                      <div className="w-9 h-9 rounded-xl bg-gray-100 flex items-center justify-center">
                        <User size={18} className="text-gray-500" />
                      </div>
                    </div>
                  )}
                </div>
              ))}
              
              {/* Loading indicator */}
              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="flex-shrink-0">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md">
                      <Bot size={18} className="text-white" />
                    </div>
                  </div>
                  <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-md px-5 py-4 shadow-md">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                      <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" />
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
            
            {/* Input area - sticky at bottom */}
            <div className="sticky bottom-0 bg-gradient-to-t from-white via-white to-transparent pt-4 pb-6">
              <div className="relative">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="메시지를 입력하세요..."
                  disabled={isLoading}
                  className={cn(
                    "w-full pl-5 pr-14 py-4 text-sm",
                    "bg-white border-2 border-gray-100 rounded-2xl",
                    "focus:outline-none focus:border-blue-400 focus:ring-4 focus:ring-blue-100",
                    "shadow-lg shadow-gray-200/50",
                    "placeholder:text-gray-400",
                    "disabled:opacity-60 disabled:cursor-not-allowed",
                    "transition-all duration-200"
                  )}
                />
                <button
                  onClick={() => handleSend()}
                  disabled={isLoading || !input.trim()}
                  className={cn(
                    "absolute right-2 top-1/2 -translate-y-1/2",
                    "w-10 h-10 rounded-xl",
                    "flex items-center justify-center",
                    "transition-all duration-200",
                    !isLoading && input.trim()
                      ? "bg-blue-500 text-white hover:bg-blue-600 shadow-md"
                      : "bg-gray-100 text-gray-400"
                  )}
                >
                  <Send size={18} />
                </button>
              </div>
              
              {/* Hint text */}
              <p className="mt-2 text-center text-xs text-gray-400">
                Enter로 전송
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

type Mode = "search" | "chat";

const ONBOARDING_DONE_KEY = "builder_curation_onboarding_done";
const ONBOARDING_CONTEXT_KEY = "builder_curation_onboarding_context";

const CAFE_TYPE_LABELS: Record<string, string> = {
  takeout: "테이크아웃 카페",
  brunch: "브런치 카페",
  aesthetic: "감성 카페",
  study: "스터디 카페",
};

const BUDGET_RENT_LABELS: Record<string, string> = {
  low: "월세 150~300만원",
  mid: "월세 200~500만원",
  high: "월세 300~800만원",
  unknown: "",
};

function buildAutoQuery(data: OnboardingData): string {
  const location = data.district ? `서울 ${data.district}` : "서울";
  const rent = BUDGET_RENT_LABELS[data.budget];
  const rentPart = rent ? ` ${rent}으로` : "";
  const cafeLabel = CAFE_TYPE_LABELS[data.cafeType] || "카페";

  return `${location}에서${rentPart} ${cafeLabel} 창업 추천해줘`;
}

function rentDefaultsFromOnboarding(budgetId: OnboardingData["budget"]): {
  budgetMin: number;
  budgetMax: number;
} {
  switch (budgetId) {
    case "low":
      return { budgetMin: 1500000, budgetMax: 3000000 };
    case "mid":
      return { budgetMin: 2000000, budgetMax: 5000000 };
    case "high":
      return { budgetMin: 3000000, budgetMax: 8000000 };
    case "unknown":
    default:
      return { budgetMin: 2000000, budgetMax: 5000000 };
  }
}

export default function Page() {
  const [mode, setMode] = useState<Mode>("chat");
  const [showOnboarding, setShowOnboarding] = useState<boolean | null>(null);
  const [initialQuery, setInitialQuery] = useState<string | undefined>(undefined);
  const [initialSearchParams, setInitialSearchParams] = useState<{
    budgetMin: number;
    budgetMax: number;
    district?: string;
  } | undefined>(undefined);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const done = window.localStorage.getItem(ONBOARDING_DONE_KEY);
    setShowOnboarding(!done);
  }, []);

  const completeOnboarding = (data: OnboardingData) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ONBOARDING_DONE_KEY, "1");
    }
    const { budgetMin, budgetMax } = rentDefaultsFromOnboarding(data.budget);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(
        ONBOARDING_CONTEXT_KEY,
        JSON.stringify({
          district: data.district,
          budget_min: budgetMin,
          budget_max: budgetMax,
          cafe_type: data.cafeType,
        })
      );
    }
    setInitialSearchParams({
      budgetMin,
      budgetMax,
      district: data.district || undefined,
    });
    setInitialQuery(buildAutoQuery(data));
    setShowOnboarding(false);
    setMode("chat");
  };

  const skipOnboarding = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ONBOARDING_DONE_KEY, "1");
      window.localStorage.removeItem(ONBOARDING_CONTEXT_KEY);
    }
    setShowOnboarding(false);
  };

  if (showOnboarding === null) {
    return null;
  }

  if (showOnboarding) {
    return <Onboarding onComplete={completeOnboarding} onSkip={skipOnboarding} />;
  }

  if (mode === "search") {
    return (
      <SearchMode
        initialSearchParams={initialSearchParams}
        onSwitchToChat={() => setMode("chat")}
      />
    );
  }

  return <ChatHome onSwitchToSearch={() => setMode("search")} initialQuery={initialQuery} />;
}
