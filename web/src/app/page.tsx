"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Send, Bot, User, BarChart3, MapPin, LayoutDashboard, TrendingUp, Store, Clock, DollarSign, CalendarDays } from "lucide-react";
import { ChatMessage, StructuredChatResponse, RecommendationCardData } from "@/types/chat";
import { SuggestedQuestions } from "@/components/SuggestedQuestions";
import { ChatChartSection } from "@/components/ChatChart";
import type { ChartData } from "@/types/chat";

import { sendStructuredChatMessage, GLOSSARY } from "@/lib/chat-api";
import DOMPurify from "dompurify";

import { cn } from "@/lib/utils";
import dynamic from "next/dynamic";
import SearchMode from "@/components/SearchMode";
import { Onboarding, OnboardingData } from "@/components/Onboarding";
import type { MapMarker } from "@/components/MiniMap";
import { ScorecardCard } from "@/components/ScorecardCard";
import TrendChart from "@/components/TrendChart";
import { SupportProgramList } from "@/components/SupportProgramCard";
import { PDFExportButton } from "@/components/PDFExportButton";


const INDUSTRY_NAMES: Record<string, string> = {
  CS100001: "한식", CS100002: "중식", CS100003: "일식", CS100004: "양식",
  CS100005: "베이커리", CS100006: "패스트푸드", CS100007: "치킨",
  CS100008: "분식", CS100009: "호프/주점", CS100010: "카페",
};

const INDUSTRY_ICONS: Record<string, string> = {
  CS100001: "🍚", CS100002: "🥟", CS100003: "🍣", CS100004: "🍝",
  CS100005: "🍞", CS100006: "🍔", CS100007: "🍗",
  CS100008: "🍜", CS100009: "🍺", CS100010: "☕",
};

function getStoredIndustry(): { code: string; name: string; icon: string } {
  if (typeof window === "undefined") return { code: "CS100010", name: "카페", icon: "☕" };
  const code = window.localStorage.getItem("builder_curation_industry_code") || "CS100010";
  return {
    code,
    name: INDUSTRY_NAMES[code] || "카페",
    icon: INDUSTRY_ICONS[code] || "☕",
  };
}

interface DistrictSearchResult {
  code: string;
  name: string;
  type: string;
  monthly_sales: number;
  store_count: number;
  survival_rate: number;
}

interface DistrictSearchResponse {
  results: DistrictSearchResult[];
  total: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002/api/v1";

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  
  return debouncedValue;
}

const MiniMap = dynamic(
  () => import("@/components/MiniMap").then((mod) => ({ default: mod.MiniMap })),
  {
    ssr: false,
    loading: () => (
      <div className="w-full min-h-[240px] flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl border border-blue-100">
        <div className="text-center text-gray-500">
          <MapPin size={32} className="mx-auto mb-2 opacity-60 animate-pulse" />
          <p className="text-sm">지도 로딩 중...</p>
        </div>
      </div>
    ),
  }
);

function ChatHome({ onSwitchToSearch, onGoHome, initialQuery }: { onSwitchToSearch: () => void; onGoHome: () => void; initialQuery?: string }) {
  const [industry] = useState(() => getStoredIndustry());
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const initialQuerySent = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const [districtResults, setDistrictResults] = useState<DistrictSearchResult[]>([]);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [autocompleteIndex, setAutocompleteIndex] = useState(-1);
  const autocompleteRef = useRef<HTMLDivElement>(null);
  
  const debouncedInput = useDebounce(input, 450);
  
  const extractKoreanLocation = useCallback((text: string): string | null => {
    const raw = (text || "").trim();
    if (!raw) return null;

    const stopwords = new Set([
      "추천",
      "추천해줘",
      "추천좀",
      "카페", "한식", "중식", "일식", "양식", "치킨", "분식", "베이커리", "패스트푸드", "호프", "주점",
      "창업",
      "예산",
      "월세",
      "타겟",
      "직장인",
      "여성",
      "남성",
      "점심",
      "오전",
      "오후",
      "저녁",
      "심야",
      "골목",
      "발달",
      "전통",
      "시장",
      "관광",
      "비교",
      "분석",
      "알려줘",
      "자세히",
    ]);

    const stripParticles = (token: string) =>
      token.replace(/(에서|으로|로|에|의|은|는|을|를|과|와)$/g, "");

    const cleanToken = (token: string) => {
      const t = stripParticles((token || "").trim());
      if (t.length < 2) return "";
      if (stopwords.has(t)) return "";
      return t;
    };

    // Prefer "서울 <지역>" pattern if present.
    const seoulMatch = raw.match(/서울\s+([\uAC00-\uD7A30-9]+(?:역|구|동|로|길|시장|관광특구)?)/);
    if (seoulMatch && seoulMatch[1]) {
      const tok = cleanToken(seoulMatch[1]);
      if (tok) return tok;
    }

    // Otherwise, scan tokens from the end.
    const tokens = raw.split(/[\s,]+/g).filter(Boolean);
    for (let i = tokens.length - 1; i >= 0; i--) {
      // Keep only Korean letters + digits (drop punctuation)
      const t = tokens[i].replace(/[^\uAC00-\uD7A30-9]/g, "");
      const tok = cleanToken(t);
      if (tok) return tok;
    }

    return null;
  }, []);
  
  const lastSearchRef = useRef("");
  
  useEffect(() => {
    const locationQuery = extractKoreanLocation(debouncedInput);
    if (!locationQuery || locationQuery.length < 2) {
      setDistrictResults([]);
      setShowAutocomplete(false);
      return;
    }
    
    if (locationQuery === lastSearchRef.current) return;
    lastSearchRef.current = locationQuery;

    let cancelled = false;
    
    fetch(`${API_BASE}/districts/search?q=${encodeURIComponent(locationQuery)}&limit=10`)
      .then(r => r.ok ? r.json() : null)
      .then((data: DistrictSearchResponse | null) => {
        if (cancelled || !data) return;
        setDistrictResults(data.results);
        setShowAutocomplete(data.results.length > 0);
        setAutocompleteIndex(-1);
      })
      .catch(() => {
        if (!cancelled) {
          setDistrictResults([]);
          setShowAutocomplete(false);
        }
      });

    return () => { cancelled = true; };
  }, [debouncedInput, extractKoreanLocation]);
  
  const handleDistrictSelect = useCallback((district: DistrictSearchResult) => {
    const locationQuery = extractKoreanLocation(input);
    const escapeRegExp = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    if (locationQuery) {
      const newInput = input.replace(
        new RegExp(escapeRegExp(locationQuery) + "$"),
        district.name
      );
      setInput(newInput);
    } else {
      setInput(input + " " + district.name);
    }
    setShowAutocomplete(false);
    setDistrictResults([]);
    inputRef.current?.focus();
  }, [input, extractKoreanLocation]);
  
  const handleAutocompleteKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!showAutocomplete || districtResults.length === 0) return;
    
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setAutocompleteIndex(prev => 
        prev < districtResults.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setAutocompleteIndex(prev => prev > 0 ? prev - 1 : -1);
    } else if (e.key === "Enter" && autocompleteIndex >= 0) {
      e.preventDefault();
      handleDistrictSelect(districtResults[autocompleteIndex]);
    } else if (e.key === "Escape") {
      setShowAutocomplete(false);
    }
  }, [showAutocomplete, districtResults, autocompleteIndex, handleDistrictSelect]);

  const makeKakaoMapUrl = (query: string) =>
    `https://map.kakao.com/link/search/${encodeURIComponent(query)}`;

  const formatKRWCompact = useCallback((value: number) => {
    if (!Number.isFinite(value) || value <= 0) return "-";
    // 억 단위
    if (value >= 100_000_000) {
      const eok = value / 100_000_000;
      return `${eok >= 100 ? eok.toFixed(0) : eok.toFixed(1)}억`;
    }
    // 만 단위
    if (value >= 10_000) {
      const man = value / 10_000;
      return `${man >= 1000 ? man.toFixed(0) : man.toFixed(0)}만`;
    }
    return `${Math.round(value)}원`;
  }, []);

  // Initialize welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        id: "welcome",
        role: "assistant",
        content: [
          `안녕하세요! ${industry.name} 창업 AI 컨설턴트 **SpotPick**입니다.`,
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
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages.length, scrollToBottom]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const convertToMapMarkers = useCallback((recommendations: RecommendationCardData[]): MapMarker[] => {
    return recommendations
      .filter((rec) => rec.coordinates?.lat && rec.coordinates?.lng)
      .map((rec) => ({
        lat: rec.coordinates!.lat,
        lng: rec.coordinates!.lng,
        label: rec.district_name,
        type: "recommended" as const,
        rank: rec.rank,
        successProbability: rec.success_probability,
      }));
  }, []);
  
  const hasStructuredData = useCallback((message: ChatMessage) => {
    return (
      (message.structured?.recommendations && message.structured.recommendations.length > 0) ||
      (message.structured?.charts && message.structured.charts.length > 0) ||
      (message.structured?.suggestedQuestions && message.structured.suggestedQuestions.length > 0)
    );
  }, []);

  const handleSend = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || isLoading) return;

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
      
      const isIntake = Boolean(
        response.context?.intake_needs && 
        Array.isArray(response.context.intake_needs) && 
        response.context.intake_needs.length > 0
      );

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.reply,
        timestamp: new Date(),
        structured: {
          recommendations: response.recommendations,
          charts: response.charts,
          suggestedQuestions: response.suggested_questions,
          isIntake,
          competitive: response.competitive,
          simulation: response.simulation,
          timeline: response.timeline,
          trademark: response.trademark,
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showAutocomplete && districtResults.length > 0) {
      handleAutocompleteKeyDown(e);
      if (["ArrowDown", "ArrowUp"].includes(e.key)) return;
      if (e.key === "Enter" && autocompleteIndex >= 0) return;
    }
    
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Process content with glossary terms and markdown
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set());

  const renderMessageContent = (content: string, messageIndex?: number) => {
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

    const isLong = content.length > 400;
    const isExpanded = messageIndex !== undefined && expandedMessages.has(messageIndex);

    return (
      <div>
        <div
          className={cn(
            "prose prose-sm max-w-none text-gray-700 leading-relaxed",
            isLong && !isExpanded && "line-clamp-6"
          )}
          dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(processedContent, { ALLOWED_TAGS: ['strong', 'br', 'span', 'em', 'b', 'i', 'p', 'ul', 'ol', 'li', 'a', 'h3', 'h4'], ALLOWED_ATTR: ['class', 'title', 'href', 'target', 'rel', 'style'] }) }}
        />
        {isLong && !isExpanded && (
          <button
            onClick={() => setExpandedMessages(prev => new Set(prev).add(messageIndex!))}
            className="mt-2 text-xs font-medium text-blue-500 hover:text-blue-700 transition-colors"
          >
            전체 보기 ▼
          </button>
        )}
        {isLong && isExpanded && (
          <button
            onClick={() => {
              setExpandedMessages(prev => {
                const next = new Set(prev);
                next.delete(messageIndex!);
                return next;
              });
            }}
            className="mt-2 text-xs font-medium text-slate-400 hover:text-slate-600 transition-colors"
          >
            접기 ▲
          </button>
        )}
      </div>
    );
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-blue-50/30">
      {/* Header */}
      <header className="bg-white/95 backdrop-blur-sm shadow-sm sticky top-0 z-40 border-b border-gray-100/50">
        <div className="max-w-3xl mx-auto px-3 sm:px-4 py-2.5 sm:py-3 flex items-center justify-between">
          <button onClick={onGoHome} className="flex items-center gap-2 sm:gap-3 hover:opacity-80 transition-opacity">
            <div className="relative">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/25">
                <span className="text-base sm:text-lg">{industry.icon}</span>
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 sm:w-3 sm:h-3 bg-emerald-400 rounded-full border-2 border-white" />
            </div>
            <div className="text-left hidden sm:block">
              <h1 className="text-lg font-bold text-gray-900 tracking-tight">SpotPick</h1>
              <p className="text-xs text-gray-500">AI가 골라주는 나만의 창업 자리</p>
            </div>
            <div className="text-left sm:hidden">
              <h1 className="text-base font-bold text-gray-900 tracking-tight">SpotPick</h1>
            </div>
          </button>

          <div className="flex items-center gap-2">
            <PDFExportButton
              messages={messages}
              industryName={industry.name}
              className="hidden sm:block"
            />
            <button
              onClick={onSwitchToSearch}
              className="text-xs sm:text-sm font-medium text-gray-700 hover:text-gray-900 px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg hover:bg-gray-50 transition-colors"
              title="고급 기능: 조건 검색, 지도/카드 비교"
            >
              <span className="hidden sm:inline">검색/비교</span>
              <span className="sm:hidden">검색</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="relative max-w-3xl mx-auto px-3 sm:px-4">
        {(
          <div className="flex flex-col h-[calc(100vh-60px)] sm:h-[calc(100vh-73px)]">
            {/* Messages area */}
            <div className="flex-1 overflow-y-auto py-4 sm:py-6 space-y-4 sm:space-y-5">
              {messages.map((message, msgIdx) => (
                <div key={message.id} className="space-y-4">
                  <div
                    className={cn(
                      "flex gap-2 sm:gap-3",
                      message.role === "user" ? "justify-end" : "justify-start"
                    )}
                  >
                    {message.role === "assistant" && (
                      <div className="flex-shrink-0">
                        <div className="w-7 h-7 sm:w-9 sm:h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-md">
                          <Bot size={16} className="text-white sm:w-[18px] sm:h-[18px]" />
                        </div>
                      </div>
                    )}

                    <div
                      className={cn(
                        "max-w-[82%] sm:max-w-[85%] md:max-w-[75%]",
                        message.role === "user"
                          ? "bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl rounded-br-md px-3 py-2 sm:px-4 sm:py-3 shadow-lg shadow-blue-500/20"
                          : "bg-white border border-gray-100 rounded-2xl rounded-bl-md p-3 sm:p-4 shadow-md"
                      )}
                    >
                      {message.role === "assistant"
                        ? renderMessageContent(message.content, msgIdx)
                        : <p className="text-xs sm:text-sm leading-relaxed">{message.content}</p>
                      }
                    </div>

                    {message.role === "user" && (
                      <div className="flex-shrink-0">
                        <div className="w-7 h-7 sm:w-9 sm:h-9 rounded-xl bg-gray-100 flex items-center justify-center">
                          <User size={16} className="text-gray-500 sm:w-[18px] sm:h-[18px]" />
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {message.role === "assistant" && hasStructuredData(message) && (
                    <div className="ml-12 animate-fade-in">
                      <div className={cn(
                        "relative overflow-hidden",
                        "bg-gradient-to-br from-slate-50 via-white to-blue-50/50",
                        "border border-slate-200/60 rounded-2xl",
                        "shadow-lg shadow-slate-200/40"
                      )}>
                        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-100/20 via-transparent to-transparent pointer-events-none" />
                        
                        <div className="relative px-4 py-3 border-b border-slate-100 bg-white/50 backdrop-blur-sm">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-sm">
                              <LayoutDashboard size={14} className="text-white" />
                            </div>
                            <span className="text-sm font-semibold text-slate-700">상권 분석 결과</span>
                          </div>
                        </div>
                        
                        <div className="relative p-4 space-y-5">
                          {message.structured?.recommendations && message.structured.recommendations.length > 0 && (() => {
                            const recommendations = message.structured!.recommendations.slice(0, 3);
                            const markers = convertToMapMarkers(recommendations);
                            const hasCoordinates = markers.length > 0;
                            
                            return (
                              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                <div className="space-y-3">
                                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                                    <TrendingUp size={12} className="text-blue-500" />
                                    추천 상권 TOP {recommendations.length}
                                    <span className="text-[10px] text-slate-400 font-normal ml-auto lg:hidden">← 스와이프</span>
                                  </div>
                                  {/* 모바일: 가로 스크롤 / 데스크톱: 세로 스택 */}
                                  <div className="lg:space-y-2.5">
                                    <div className="flex lg:flex-col gap-2.5 overflow-x-auto lg:overflow-x-visible snap-x snap-mandatory scrollbar-hide pb-2 lg:pb-0 -mx-1 px-1">
                                    {recommendations.map((rec, i) => {
                                      const probColor = rec.success_probability >= 0.7 
                                        ? "text-emerald-600 bg-emerald-50" 
                                        : rec.success_probability >= 0.5 
                                          ? "text-amber-600 bg-amber-50" 
                                          : "text-rose-600 bg-rose-50";
                                      
                                      return (
                                        <div
                                          key={i}
                                          className={cn(
                                            "group relative p-3 rounded-xl flex-shrink-0",
                                            "bg-white border border-slate-100",
                                            "hover:border-blue-200 hover:shadow-md",
                                            "transition-all duration-200 cursor-pointer",
                                            "w-[85%] sm:w-[70%] lg:w-full snap-center"
                                          )}
                                          onClick={() => handleSend(`${rec.district_name} 상권에 대해 자세히 알려줘`)}
                                        >
                                          <div className="flex items-start justify-between gap-3">
                                            <div className="flex items-center gap-2.5 min-w-0">
                                              <span className={cn(
                                                "flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center",
                                                "text-xs font-bold bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-sm"
                                              )}>
                                                {rec.rank}
                                              </span>
                                              <div className="min-w-0">
                                                <span className="font-semibold text-slate-800 text-sm block truncate">
                                                  {rec.district_name}
                                                </span>
                                                <span className="text-[10px] text-slate-500 font-medium">
                                                  {rec.district_type}
                                                </span>
                                              </div>
                                            </div>
                                            <div className={cn("px-2 py-1 rounded-lg text-sm font-bold", probColor)}>
                                              {Math.round(rec.success_probability * 100)}%
                                            </div>
                                          </div>
                                          
                                          <div className="flex items-center gap-3 mt-2.5 pt-2.5 border-t border-slate-50">
                                            {(rec.monthly_sales_total || rec.monthly_sales) && (
                                              <div className="flex items-center gap-2 text-[11px] text-slate-600 min-w-0">
                                                <Store size={10} className="text-slate-400" />
                                                {rec.monthly_sales_total ? (
                                                  <span className="font-medium truncate">총 {formatKRWCompact(rec.monthly_sales_total)} /월</span>
                                                ) : null}
                                                {rec.monthly_sales ? (
                                                  <span className={cn(
                                                    "font-medium truncate",
                                                    rec.monthly_sales_total ? "text-slate-500" : ""
                                                  )}>
                                                    점포당 {formatKRWCompact(rec.monthly_sales)} /월
                                                  </span>
                                                ) : null}
                                              </div>
                                            )}
                                            {rec.store_count !== undefined && (
                                              <div className="flex items-center gap-1 text-[11px] text-slate-600">
                                                <span className="font-medium">경쟁 {rec.store_count}개</span>
                                              </div>
                                            )}
                                            {rec.peak_time && (
                                              <div className="flex items-center gap-1 text-[11px] text-slate-600">
                                                <Clock size={10} className="text-slate-400" />
                                                <span className="font-medium">{rec.peak_time}</span>
                                              </div>
                                            )}
                                            {rec.survival_rate != null && (
                                              <span className="text-[10px] text-slate-500">
                                                생존율 {(rec.survival_rate * 100).toFixed(0)}%
                                              </span>
                                            )}
                                          </div>
                                          {(rec.foot_traffic_total || rec.worker_total || rec.facility_subway || rec.change_indicator) && (
                                            <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
                                              {rec.foot_traffic_total ? (
                                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-blue-50 text-blue-600 font-medium">
                                                  유동 {rec.foot_traffic_total >= 1000000 ? `${(rec.foot_traffic_total / 10000).toFixed(0)}만` : `${(rec.foot_traffic_total / 1000).toFixed(0)}K`}
                                                </span>
                                              ) : null}
                                              {rec.worker_total ? (
                                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-50 text-amber-600 font-medium">
                                                  직장인 {rec.worker_total >= 10000 ? `${(rec.worker_total / 10000).toFixed(1)}만` : `${(rec.worker_total / 1000).toFixed(1)}K`}
                                                </span>
                                              ) : null}
                                              {rec.facility_subway ? (
                                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-50 text-purple-600 font-medium">
                                                  🚇 {rec.facility_subway}개역
                                                </span>
                                              ) : null}
                                              {rec.change_indicator && (
                                                <span className={cn(
                                                  "px-1.5 py-0.5 rounded text-[10px] font-medium",
                                                  rec.change_indicator.includes("HH") || rec.change_indicator.includes("성장") ? "bg-emerald-50 text-emerald-600" :
                                                  rec.change_indicator.includes("HL") || rec.change_indicator.includes("안정") ? "bg-sky-50 text-sky-600" :
                                                  rec.change_indicator.includes("LL") || rec.change_indicator.includes("쇠퇴") ? "bg-rose-50 text-rose-600" :
                                                  "bg-slate-50 text-slate-500"
                                                )}>
                                                  {rec.change_indicator}
                                                </span>
                                              )}
                                              {rec.transit_percentile != null && rec.transit_percentile > 0 && (
                                                <span className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                                  rec.transit_percentile > 0.8 ? 'bg-emerald-50 text-emerald-600' :
                                                  rec.transit_percentile > 0.4 ? 'bg-sky-50 text-sky-600' :
                                                  'bg-slate-100 text-slate-500'
                                                }`}>
                                                  🚇 교통 {rec.transit_percentile > 0.8 ? '우수' : rec.transit_percentile > 0.4 ? '양호' : '보통'}
                                                </span>
                                              )}
                                            </div>
                                          )}
                                          {rec.positioning && (
                                            <div className="mt-2 px-3 py-2 rounded-lg bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-100/60">
                                              <p className="text-[11px] font-semibold text-indigo-700 mb-0.5">
                                                💡 {rec.positioning} 포지셔닝 적합
                                              </p>
                                              {rec.positioning_detail && (
                                                <p className="text-[10px] text-indigo-600/80">{rec.positioning_detail}</p>
                                              )}
                                            </div>
                                          )}
                                          {rec.scorecard && (
                                            <div className="mt-2">
                                              <ScorecardCard scorecard={rec.scorecard} />
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                    </div>
                                  </div>
                                </div>
                                
                                <div className="space-y-3">
                                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                                    <MapPin size={12} className="text-blue-500" />
                                    위치 지도
                                  </div>
                                  {hasCoordinates ? (
                                    <div className="rounded-xl overflow-hidden border border-slate-100">
                                      <MiniMap 
                                        markers={markers} 
                                        height={240}
                                        zoom={12}
                                      />
                                    </div>
                                  ) : (
                                    <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                      <p className="text-xs text-slate-500 mb-3">
                                        지도 좌표를 찾지 못해 외부 지도 링크로 안내합니다.
                                      </p>
                                      <div className="flex flex-wrap gap-2">
                                        {recommendations.map((r) => (
                                          <a
                                            key={`map-${r.rank}`}
                                            href={makeKakaoMapUrl(r.address || `서울 ${r.district_name}`)}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className={cn(
                                              "inline-flex items-center gap-1.5 text-xs px-3 py-1.5",
                                              "bg-white border border-slate-200 rounded-full",
                                              "text-slate-700 hover:border-blue-300 hover:text-blue-600",
                                              "transition-colors shadow-sm"
                                            )}
                                          >
                                            <MapPin size={11} className="text-blue-500" />
                                            <span>{r.district_name}</span>
                                          </a>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          })()}
                          
                          {message.structured?.charts && message.structured.charts.length > 0 && (
                            <div className="space-y-3">
                              <div className="flex items-center gap-2 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                                <BarChart3 size={12} className="text-blue-500" />
                                매출 분석
                              </div>
                              {message.structured?.recommendations && message.structured.recommendations.length > 0 && (() => {
                                const top = message.structured!.recommendations[0];
                                const show = Boolean(top.monthly_sales_total || top.monthly_transactions_total || top.avg_ticket);
                                if (!show) return null;
                                return (
                                  <div className={cn(
                                    "flex flex-wrap gap-2 text-[11px]",
                                    "px-3 py-2 rounded-xl",
                                    "bg-white/70 border border-slate-200/60"
                                  )}>
                                    {top.monthly_sales_total ? (
                                      <span className="font-medium text-slate-700">총 월매출 {formatKRWCompact(top.monthly_sales_total)}</span>
                                    ) : null}
                                    {top.monthly_transactions_total ? (
                                      <span className="text-slate-500">거래 {top.monthly_transactions_total.toLocaleString()}건</span>
                                    ) : null}
                                    {top.avg_ticket ? (
                                      <span className="text-slate-500">객단가 {top.avg_ticket.toLocaleString()}원</span>
                                    ) : null}
                                  </div>
                                );
                              })()}
                              <ChatChartSection charts={message.structured.charts as ChartData[]} />
                            </div>
                          )}

                          {message.structured?.competitive && (
                            <div className={cn(
                              "mt-3 p-3 rounded-xl",
                              "bg-white/70 border border-slate-200/60",
                              "space-y-2.5"
                            )}>
                              <div className="flex items-center gap-2">
                                <Store size={14} className="text-amber-600" />
                                <span className="text-xs font-semibold text-slate-700">주변 경쟁 분석</span>
                                <span className="text-[10px] text-slate-400 ml-auto">
                                  {message.structured.competitive.total_nearby_cafes}개 {industry.name} 분석
                                </span>
                              </div>
                              
                              {message.structured.competitive.cafe_types.length > 0 && (
                                <div className="flex flex-wrap gap-1.5">
                                  {message.structured.competitive.cafe_types.slice(0, 4).map((ct, i) => (
                                    <span 
                                      key={i}
                                      className={cn(
                                        "px-2 py-0.5 rounded-full text-[10px] font-medium",
                                        i === 0 ? "bg-amber-100 text-amber-700" :
                                        i === 1 ? "bg-blue-100 text-blue-700" :
                                        "bg-slate-100 text-slate-600"
                                      )}
                                    >
                                      {ct.type} {ct.ratio}%
                                    </span>
                                  ))}
                                </div>
                              )}

                              {message.structured.competitive.market_gaps.length > 0 && (
                                <div className="space-y-1">
                                  <p className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">시장 기회</p>
                                  {message.structured.competitive.market_gaps.slice(0, 2).map((gap, i) => (
                                    <div key={i} className="flex items-start gap-2 text-[11px]">
                                      <span className={cn(
                                        "w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0",
                                        gap.opportunity_score >= 0.7 ? "bg-emerald-500" :
                                        gap.opportunity_score >= 0.4 ? "bg-amber-500" : "bg-slate-400"
                                      )} />
                                      <span className="text-slate-600 leading-snug">{gap.description}</span>
                                    </div>
                                  ))}
                                </div>
                              )}

                              {message.structured.competitive.strategies.length > 0 && (
                                <div className="space-y-1">
                                  <p className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">차별화 전략</p>
                                  {message.structured.competitive.strategies.slice(0, 2).map((s, i) => (
                                    <div key={i} className="flex items-start gap-2 text-[11px]">
                                      <span className={cn(
                                        "px-1.5 py-0.5 rounded text-[9px] font-semibold flex-shrink-0 mt-0.5",
                                        s.priority === "high" ? "bg-rose-100 text-rose-700" :
                                        s.priority === "medium" ? "bg-amber-100 text-amber-700" :
                                        "bg-emerald-100 text-emerald-700"
                                      )}>
                                        {s.priority === "high" ? "높음" : s.priority === "medium" ? "중간" : "낮음"}
                                      </span>
                                      <span className="text-slate-600 leading-snug">{s.strategy}</span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {message.structured?.simulation && (() => {
                            const sim = message.structured!.simulation;
                            const startup = sim.startup_cost;
                            const operating = sim.operating_cost;
                            const breakEven = sim.break_even;
                            const menuCosts = sim.menu_costs;
                            const formatMan = (value: number) => `${Math.round(value / 10000).toLocaleString()}만원`;
                            const formatManRange = (min: number, max: number) => `${formatMan(min)} ~ ${formatMan(max)}`;
                            const formatCompactWon = (value: number) => {
                              const compact = formatKRWCompact(value);
                              return compact.endsWith("원") ? compact : `${compact}원`;
                            };
                            const operatingPercent = (value: number) =>
                              operating.total > 0 ? Math.round((value / operating.total) * 100) : 0;

                            return (
                              <div className={cn(
                                "mt-3 p-3 rounded-xl",
                                "bg-white/70 border border-slate-200/60",
                                "space-y-3"
                              )}>
                                <div className="flex items-center gap-2">
                                  <LayoutDashboard size={14} className="text-slate-600" />
                                  <span className="text-xs font-semibold text-slate-700">창업 시뮬레이션</span>
                                  <span className="text-[10px] text-slate-400 ml-auto">
                                    {sim.district_name}
                                  </span>
                                </div>
                                {sim.assumptions && (
                                  <div className="text-[10px] text-slate-400 -mt-1.5">
                                    {sim.assumptions.summary} · {sim.assumptions.disclaimer}
                                  </div>
                                )}

                                <div className="space-y-1.5">
                                  <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-600">
                                    <DollarSign size={12} className="text-emerald-600" />
                                    초기 투자비용
                                  </div>
                                  <div className="flex items-center justify-between text-[12px]">
                                    <span className="text-slate-500">총 투자</span>
                                    <span className="font-semibold text-slate-800">
                                      {formatManRange(startup.total_min, startup.total_max)}
                                    </span>
                                  </div>
                                  <div className="flex flex-wrap gap-1.5 text-[10px]">
                                    <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700">
                                      보증금 {formatMan(startup.deposit)}
                                    </span>
                                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                                      인테리어 {formatMan(startup.interior)} ({startup.area_pyeong}평/{startup.interior_grade})
                                    </span>
                                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                                      장비 {formatMan(startup.equipment_min)}~{formatMan(startup.equipment_max)}
                                    </span>
                                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                                      재고+기타 {formatMan(startup.initial_inventory_min + startup.permits_misc_min)}~{formatMan(startup.initial_inventory_max + startup.permits_misc_max)}
                                    </span>
                                  </div>
                                </div>

                                <div className="space-y-1.5">
                                  <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-600">
                                    <Clock size={12} className="text-amber-600" />
                                    월 운영비
                                  </div>
                                  <div className="flex items-center justify-between text-[12px]">
                                    <span className="text-slate-500">총 운영비</span>
                                    <span className="font-semibold text-slate-800">{formatMan(operating.total)}/월</span>
                                  </div>
                                  <div className="flex flex-wrap gap-1.5 text-[10px]">
                                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                                      월세 {formatMan(operating.rent)}
                                    </span>
                                    <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                                      재료비 {operatingPercent(operating.cogs)}%
                                    </span>
                                    <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                                      인건비 {operatingPercent(operating.labor)}%
                                    </span>
                                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                                      공과금 {formatMan(operating.utilities)}
                                    </span>
                                    <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                                      기타 {formatMan(operating.other)}
                                    </span>
                                  </div>
                                </div>

                                <div className="space-y-1.5">
                                  <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-600">
                                    <TrendingUp size={12} className="text-emerald-600" />
                                    손익분기
                                  </div>
                                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                                    <span className="text-slate-500">월 순이익</span>
                                    <span className="font-semibold text-emerald-700">
                                      {formatMan(breakEven.monthly_net_profit)}
                                    </span>
                                    <span className="text-slate-500">마진</span>
                                    <span className="font-semibold text-emerald-700">
                                      {(breakEven.net_profit_margin * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                                    <span className="text-slate-500">투자 회수</span>
                                    <span className="font-semibold text-slate-700">
                                      {breakEven.break_even_months_min}~{breakEven.break_even_months_max}개월
                                    </span>
                                    <span className="text-slate-500">일 손익분기</span>
                                    <span className="font-semibold text-amber-700">
                                      {formatMan(breakEven.daily_break_even_sales)}
                                    </span>
                                  </div>
                                </div>

                                {menuCosts && menuCosts.menu_costs.length > 0 && (
                                  <div className="space-y-1.5">
                                    <div className="flex items-center gap-2 text-[11px] font-semibold text-slate-600">
                                      <span className="text-xs">{industry.icon}</span>
                                      메뉴 원가
                                    </div>
                                    <div className="grid gap-1 text-[10px] text-slate-600">
                                      {menuCosts.menu_costs.slice(0, 4).map((item) => (
                                        <div key={item.menu} className="flex items-center justify-between">
                                          <span className="truncate">
                                            {item.menu} {item.cost.toLocaleString()}원 → {item.selling_price.toLocaleString()}원
                                          </span>
                                          <span className="text-emerald-700 font-semibold">
                                            마진 {(item.margin_rate * 100).toFixed(0)}%
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                    <div className="text-[10px] text-slate-500">
                                      {menuCosts.daily_sales_scenario.unit_name || `일 ${(menuCosts.daily_sales_scenario.daily_orders ?? menuCosts.daily_sales_scenario.daily_cups ?? 100).toLocaleString()}${menuCosts.daily_sales_scenario.unit || "식"}`} 시나리오: 일매출 {formatCompactWon(menuCosts.daily_sales_scenario.daily_revenue)} / 원가 {formatCompactWon(menuCosts.daily_sales_scenario.daily_cogs)} / 마진 {formatCompactWon(menuCosts.daily_sales_scenario.daily_gross_profit)}
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })()}

                          {message.structured?.timeline && (
                            <div className="space-y-3">
                              <h4 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                                <CalendarDays size={16} className="text-teal-500" />
                                예상 창업 일정
                                <span className="text-xs font-normal text-slate-400">
                                  약 {message.structured.timeline.total_months}개월
                                </span>
                              </h4>
                              <div className="space-y-1.5">
                                {message.structured.timeline.stages.map((stage, idx) => {
                                  const maxWeek = message.structured!.timeline!.total_weeks;
                                  const leftPct = (stage.start_week / maxWeek) * 100;
                                  const widthPct = Math.max(4, ((stage.end_week - stage.start_week) / maxWeek) * 100);
                                  const colors = [
                                    'bg-blue-400', 'bg-emerald-400', 'bg-amber-400',
                                    'bg-purple-400', 'bg-rose-400', 'bg-teal-400'
                                  ];
                                  return (
                                    <div key={idx} className="flex items-center gap-2">
                                      <span className="text-[10px] text-slate-500 w-20 text-right flex-shrink-0 truncate">
                                        {stage.name}
                                      </span>
                                      <div className="flex-1 h-5 bg-slate-100 rounded-full relative overflow-hidden">
                                        <div
                                          className={`absolute h-full rounded-full ${colors[idx % colors.length]} opacity-80`}
                                          style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                                        />
                                        <span className="absolute inset-0 flex items-center justify-center text-[9px] text-slate-600 font-medium">
                                          {stage.duration_weeks}주
                                        </span>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                              <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                                <span>⚡ 빠르게 ~{message.structured.timeline.fast_estimate_months}개월</span>
                                <span>여유있게 ~{message.structured.timeline.slow_estimate_months}개월</span>
                              </div>
                              <p className="text-[10px] text-slate-400 italic">
                                {message.structured.timeline.summary}
                              </p>
                            </div>
                          )}

                          {message.structured?.trend && (
                            <div className="mt-4">
                              <TrendChart data={message.structured.trend} />
                            </div>
                          )}

                          {message.structured?.trademark && (
                            <div className={cn(
                              "mt-3 p-3 rounded-xl border space-y-2",
                              message.structured.trademark.risk_level === "high" ? "bg-rose-50 border-rose-200" :
                              message.structured.trademark.risk_level === "medium" ? "bg-amber-50 border-amber-200" :
                              "bg-emerald-50 border-emerald-200"
                            )}>
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-semibold text-slate-700">
                                  &ldquo;{message.structured.trademark.query}&rdquo; 상표 충돌 확인
                                </span>
                                <span className={cn(
                                  "text-[10px] font-semibold px-2 py-0.5 rounded-full",
                                  message.structured.trademark.risk_level === "high" ? "bg-rose-100 text-rose-700" :
                                  message.structured.trademark.risk_level === "medium" ? "bg-amber-100 text-amber-700" :
                                  "bg-emerald-100 text-emerald-700"
                                )}>
                                  {message.structured.trademark.risk_level === "high" ? "위험 높음" :
                                   message.structured.trademark.risk_level === "medium" ? "주의" : "양호"}
                                </span>
                              </div>
                              {message.structured.trademark.conflicts.length > 0 && (
                                <div className="flex flex-wrap gap-1.5">
                                  {message.structured.trademark.conflicts.slice(0, 5).map((c, i) => (
                                    <span key={i} className={cn(
                                      "px-2 py-0.5 rounded text-[10px] font-medium",
                                      c.similarity >= 0.95 ? "bg-rose-100 text-rose-700" :
                                      c.similarity >= 0.85 ? "bg-amber-100 text-amber-700" :
                                      "bg-slate-100 text-slate-600"
                                    )}>
                                      {c.name} ({Math.round(c.similarity * 100)}%)
                                    </span>
                                  ))}
                                </div>
                              )}
                              {message.structured.trademark.suggestions.length > 0 && (
                                <ul className="text-[10px] text-slate-600 space-y-0.5">
                                  {message.structured.trademark.suggestions.map((s, i) => (
                                    <li key={i}>• {s}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          )}

                          {message.structured?.support_programs && message.structured.support_programs.length > 0 && (
                            <div className="mt-4">
                              <h4 className="text-xs font-bold text-slate-700 mb-3 flex items-center gap-2">
                                <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                신청 가능한 창업 지원사업
                              </h4>
                              <SupportProgramList programs={message.structured.support_programs} />
                            </div>
                          )}

                          {message.structured?.suggestedQuestions && message.structured.suggestedQuestions.length > 0 && (
                            message.structured.isIntake ? (
                              <div className="pt-4 space-y-2">
                                <p className="text-xs font-semibold text-slate-500 tracking-wide uppercase">아래에서 선택하세요</p>
                                <div className="grid gap-2">
                                  {message.structured.suggestedQuestions.map((q, qi) => (
                                    <button
                                      key={qi}
                                      onClick={() => handleSend(q)}
                                      className={cn(
                                        "w-full text-left px-4 py-3 rounded-xl",
                                        "bg-gradient-to-r from-blue-50 to-indigo-50",
                                        "border border-blue-200/60",
                                        "hover:from-blue-100 hover:to-indigo-100 hover:border-blue-300",
                                        "hover:shadow-md active:scale-[0.98]",
                                        "transition-all duration-150",
                                        "text-sm font-medium text-slate-700"
                                      )}
                                    >
                                      <div className="flex items-center gap-3">
                                        <div className="w-7 h-7 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0">
                                          <MapPin size={14} className="text-blue-600" />
                                        </div>
                                        <span className="leading-snug">{q}</span>
                                      </div>
                                    </button>
                                  ))}
                                </div>
                              </div>
                            ) : (
                              <div className="pt-3 border-t border-slate-100">
                                <SuggestedQuestions 
                                  questions={message.structured.suggestedQuestions}
                                  onSelect={handleSend}
                                  variant="minimal"
                                />
                              </div>
                            )
                          )}
                        </div>
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
            
            <div className="sticky bottom-0 bg-gradient-to-t from-white via-white to-transparent pt-3 pb-4 sm:pt-4 sm:pb-6">
              <div className="relative">
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onBlur={() => setTimeout(() => setShowAutocomplete(false), 150)}
                  onFocus={() => districtResults.length > 0 && setShowAutocomplete(true)}
                  placeholder="메시지를 입력하세요..."
                  disabled={isLoading}
                  className={cn(
                    "w-full pl-4 pr-12 py-3 text-sm sm:pl-5 sm:pr-14 sm:py-4",
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
                    "absolute right-1.5 top-1/2 -translate-y-1/2",
                    "w-9 h-9 rounded-xl sm:w-10 sm:h-10 sm:right-2",
                    "flex items-center justify-center",
                    "transition-all duration-200",
                    !isLoading && input.trim()
                      ? "bg-blue-500 text-white hover:bg-blue-600 shadow-md active:scale-95"
                      : "bg-gray-100 text-gray-400"
                  )}
                >
                  <Send size={16} className="sm:w-[18px] sm:h-[18px]" />
                </button>
                
                {showAutocomplete && districtResults.length > 0 && (
                  <div 
                    ref={autocompleteRef}
                    className={cn(
                      "absolute bottom-full left-0 right-0 mb-2",
                      "bg-white border border-slate-200 rounded-xl",
                      "shadow-xl shadow-slate-200/50",
                      "max-h-64 overflow-y-auto",
                      "animate-fade-in z-50"
                    )}
                  >
                    <div className="px-3 py-2 border-b border-slate-100 bg-slate-50/50">
                      <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                        상권 자동완성
                      </span>
                    </div>
                    <div className="p-1">
                      {districtResults.map((district, index) => (
                        <button
                          key={district.code}
                          onClick={() => handleDistrictSelect(district)}
                          className={cn(
                            "w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg",
                            "text-left transition-colors",
                            index === autocompleteIndex
                              ? "bg-blue-50 text-blue-700"
                              : "hover:bg-slate-50 text-slate-700"
                          )}
                        >
                          <div className="flex items-center gap-2.5 min-w-0">
                            <MapPin size={14} className={cn(
                              index === autocompleteIndex ? "text-blue-500" : "text-slate-400"
                            )} />
                            <div className="min-w-0">
                              <span className="font-medium text-sm block truncate">
                                {district.name}
                              </span>
                              <span className="text-[11px] text-slate-500">
                                {district.type}
                              </span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            {district.survival_rate > 0 && (
                              <span className={cn(
                                "text-[10px] font-medium px-1.5 py-0.5 rounded",
                                district.survival_rate >= 0.8 
                                  ? "bg-emerald-50 text-emerald-600" 
                                  : district.survival_rate >= 0.6 
                                    ? "bg-amber-50 text-amber-600"
                                    : "bg-rose-50 text-rose-600"
                              )}>
                                생존율 {Math.round(district.survival_rate * 100)}%
                              </span>
                            )}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              
              <p className="mt-2 text-center text-xs text-gray-400">
                Enter로 전송 · 지역명 입력시 자동완성
              </p>
            </div>
           </div>
         )}
       </div>
     </main>
   );
 }

type Mode = "landing" | "onboarding" | "search" | "chat";

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
};

const TARGET_LABELS: Record<string, string> = {
  office: "직장인",
  "20s_female": "20대 여성",
  "30s": "30~40대",
  student: "대학생",
  local: "동네 주민",
  tourist: "관광객",
};

function buildAutoQuery(data: OnboardingData): string {
  const location = data.district ? `서울 ${data.district}` : "서울";
  const rent = BUDGET_RENT_LABELS[data.budget];
  const rentPart = rent ? ` ${rent}으로` : "";
  const industryName = INDUSTRY_NAMES[data.industryCode] || "카페";
  const cafeLabel = data.industryCode === "CS100010"
    ? (CAFE_TYPE_LABELS[data.cafeType] || industryName)
    : industryName;
  const targetLabel = TARGET_LABELS[data.target];
  const targetPart = targetLabel ? `, ${targetLabel} 타겟` : "";

  return `${location}에서${rentPart}${targetPart} ${cafeLabel} 창업 추천해줘`;
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
    default:
      return { budgetMin: 2000000, budgetMax: 5000000 };
  }
}

function LandingPage({ onStart, hasSaved, onResume, onClear }: {
  onStart: () => void;
  hasSaved: boolean;
  onResume: () => void;
  onClear: () => void;
}) {
  const [savedLabel, setSavedLabel] = useState<string | null>(null);

  useEffect(() => {
    if (!hasSaved || typeof window === "undefined") return;
    try {
      const raw = window.localStorage.getItem("builder_curation_onboarding_context");
      if (raw) {
        const ctx = JSON.parse(raw);
        const parts: string[] = [];
        if (ctx.district) parts.push(ctx.district);
        if (ctx.cafe_type) parts.push(ctx.cafe_type);
        setSavedLabel(parts.length ? parts.join(" · ") : null);
      }
    } catch { /* ignore */ }
  }, [hasSaved]);

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-blue-50/30 flex flex-col items-center justify-center px-4">
      <div className="relative mb-8">
        <div className="w-20 h-20 bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center shadow-2xl shadow-blue-500/30">
          <Store className="text-white" size={36} />
        </div>
        <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-emerald-400 rounded-full border-[3px] border-white" />
      </div>

      <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3 tracking-tight text-center">
        창업,<br className="sm:hidden" /> 어디서 해야 성공할까?
      </h1>
      <p className="text-gray-500 max-w-sm mx-auto text-center mb-2 text-sm leading-relaxed">
        서울시 1,077개 상권 · 6년간 데이터를<br />AI가 분석해 맞춤 추천합니다.
      </p>
      <p className="text-xs text-gray-400 mb-10">몇 가지 질문에 답하면 바로 시작됩니다</p>

      <div className="flex flex-col items-center gap-3">
        <button
          onClick={onStart}
          className={cn(
            "px-10 py-4 rounded-2xl text-base font-semibold",
            "bg-gradient-to-r from-blue-500 to-indigo-600 text-white",
            "shadow-xl shadow-blue-500/30",
            "hover:shadow-2xl hover:shadow-blue-500/40 hover:scale-[1.02]",
            "active:scale-[0.98]",
            "transition-all duration-200"
          )}
        >
          {hasSaved ? "새로 시작하기" : "시작하기"}
        </button>

        {hasSaved && (
          <div className="flex flex-col items-center gap-2 mt-2">
            <button
              onClick={onResume}
              className={cn(
                "px-8 py-3 rounded-xl text-sm font-medium",
                "bg-white border border-slate-200 text-slate-700",
                "shadow-sm hover:shadow-md hover:border-blue-300 hover:text-blue-600",
                "active:scale-[0.98] transition-all duration-200"
              )}
            >
              이전 분석 이어하기
              {savedLabel && (
                <span className="ml-2 text-xs text-slate-400">{savedLabel}</span>
              )}
            </button>
            <button
              onClick={onClear}
              className="text-xs text-slate-400 hover:text-rose-500 transition-colors"
            >
              이전 데이터 삭제
            </button>
          </div>
        )}
      </div>
    </main>
  );
}

export default function Page() {
  const [mode, setMode] = useState<Mode | null>(null);
  const [initialQuery, setInitialQuery] = useState<string | undefined>(undefined);
  const [initialSearchParams, setInitialSearchParams] = useState<{
    budgetMin: number;
    budgetMax: number;
    district?: string;
  } | undefined>(undefined);

  const [hasSavedSession, setHasSavedSession] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setHasSavedSession(!!window.localStorage.getItem(ONBOARDING_DONE_KEY));
    setMode("landing");
  }, []);

  const completeOnboarding = (data: OnboardingData) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ONBOARDING_DONE_KEY, "1");
      if (data.industryCode) {
        window.localStorage.setItem("builder_curation_industry_code", data.industryCode);
      }
      const { budgetMin, budgetMax } = rentDefaultsFromOnboarding(data.budget);
      window.localStorage.setItem(
        ONBOARDING_CONTEXT_KEY,
        JSON.stringify({
          district: data.district,
          budget_min: budgetMin,
          budget_max: budgetMax,
          cafe_type: data.cafeType,
          target: data.target,
          industry_code: data.industryCode || "CS100010",
        })
      );
      setInitialSearchParams({
        budgetMin,
        budgetMax,
        district: data.district || undefined,
      });
      setInitialQuery(buildAutoQuery(data));
    }
    setMode("chat");
  };

  if (mode === null) {
    // Hydration: waiting for localStorage check — render nothing to prevent flash
    return null;
  }

  if (mode === "landing") {
    return (
      <LandingPage
        onStart={() => setMode("onboarding")}
        hasSaved={hasSavedSession}
        onResume={() => {
          if (typeof window !== "undefined") {
            try {
              const raw = window.localStorage.getItem(ONBOARDING_CONTEXT_KEY);
              if (raw) {
                const ctx = JSON.parse(raw);
                setInitialSearchParams({
                  budgetMin: ctx.budget_min ?? 2000000,
                  budgetMax: ctx.budget_max ?? 5000000,
                  district: ctx.district || undefined,
                });
                setInitialQuery(
                  `서울 ${ctx.district || ""}에서 월세 ${Math.round((ctx.budget_min ?? 2000000) / 10000)}~${Math.round((ctx.budget_max ?? 5000000) / 10000)}만원 ${ctx.industry_code ? (INDUSTRY_NAMES[ctx.industry_code] || "창업") : "창업"} 추천해줘`.trim()
                );
              }
            } catch { /* parse error */ }
          }
          setMode("chat");
        }}
        onClear={() => {
          if (typeof window !== "undefined") {
            window.localStorage.removeItem(ONBOARDING_DONE_KEY);
            window.localStorage.removeItem(ONBOARDING_CONTEXT_KEY);
          }
          setHasSavedSession(false);
        }}
      />
    );
  }

  if (mode === "onboarding") {
    return (
      <Onboarding
        onComplete={completeOnboarding}
        onSkip={() => {
          if (typeof window !== "undefined") {
            window.localStorage.setItem(ONBOARDING_DONE_KEY, "1");
            window.localStorage.removeItem(ONBOARDING_CONTEXT_KEY);
          }
          setMode("chat");
        }}
      />
    );
  }

  if (mode === "search") {
    return (
      <SearchMode
        initialSearchParams={initialSearchParams}
        onSwitchToChat={() => setMode("chat")}
      />
    );
  }

  return <ChatHome onSwitchToSearch={() => setMode("search")} onGoHome={() => setMode("landing")} initialQuery={initialQuery} />;
}
