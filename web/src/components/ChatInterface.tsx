"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Loader2, Sparkles, X, MessageCircle, ChevronRight } from "lucide-react";
import DOMPurify from "dompurify";
import { 
  ChatMessage, 
  hasRecommendations, 
  hasCharts, 
  hasSuggestedQuestions,
  GLOSSARY,
  DEFAULT_SUGGESTED_QUESTIONS,
} from "@/types/chat";
import { 
  sendStructuredChatMessage, 
  createUserMessage, 
  createAssistantMessage,
  createErrorMessage,
} from "@/lib/chat-api";
import { DistrictCharts } from "./DistrictCharts";
import { ChatChartSection } from "./ChatChart";
import { cn } from "@/lib/utils";

// ============================================================================
// Props Types
// ============================================================================

interface ChatInterfaceProps {
  isOpen: boolean;
  onClose: () => void;
}

// ============================================================================
// Sub-Components for Structured Data Rendering
// ============================================================================

/**
 * Renders recommendation cards within a chat message
 * Placeholder component - will be fully implemented in Part B
 */
function RecommendationCards({ 
  data 
}: { 
  data: NonNullable<ChatMessage['structured']>['recommendations'] 
}) {
  if (!data || data.length === 0) return null;
  
  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-medium text-gray-500 flex items-center gap-1">
        <Sparkles size={12} />
        추천 상권 {data.length}개
      </p>
      <div className="grid gap-2">
        {data.slice(0, 3).map((rec, idx) => (
          <div 
            key={`rec-${idx}`}
            className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-3 border border-blue-100"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-blue-600">#{rec.rank}</span>
                <span className="font-medium text-gray-900">{rec.district_name}</span>
                <span className="text-xs px-1.5 py-0.5 bg-white/80 rounded text-gray-600">
                  {rec.district_type}
                </span>
              </div>
              <div className="text-right">
                <span className={cn(
                  "text-lg font-bold",
                  rec.success_probability >= 0.7 ? "text-green-600" :
                  rec.success_probability >= 0.5 ? "text-amber-600" : "text-red-600"
                )}>
                  {Math.round(rec.success_probability * 100)}%
                </span>
              </div>
            </div>
            <div className="mt-2 flex flex-wrap gap-2 text-xs text-gray-600">
              <span>월세 {(rec.estimated_rent / 10000).toFixed(0)}만</span>
              <span>•</span>
              <span>피크 {rec.peak_time}</span>
              <span>•</span>
              <span>주 고객 {rec.main_age_group}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}



/**
 * Renders suggested follow-up questions
 */
function SuggestedQuestions({ 
  questions,
  onSelect,
}: { 
  questions: string[];
  onSelect: (question: string) => void;
}) {
  if (!questions || questions.length === 0) return null;
  
  return (
    <div className="mt-3 pt-3 border-t border-gray-100">
      <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
        <ChevronRight size={12} />
        이어서 질문하기
      </p>
      <div className="flex flex-wrap gap-1.5">
        {questions.slice(0, 3).map((q, idx) => (
          <button
            key={idx}
            onClick={() => onSelect(q)}
            className="text-xs px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100 transition-colors"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ChatInterface({ isOpen, onClose }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "안녕하세요! 창업 AI 컨설턴트 **SpotPick**입니다. 🏪\n\n서울시 1,077개 상권 데이터를 기반으로 최적의 창업 위치를 추천해드려요.\n\n무엇이 궁금하세요?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const handleSend = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText || isLoading) return;

    const userMessage = createUserMessage(messageText);
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await sendStructuredChatMessage(messageText, messages);
      const assistantMessage = createAssistantMessage(response.reply, {
        recommendations: response.recommendations,
        charts: response.charts,
        suggestedQuestions: response.suggested_questions,
      });
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage = createErrorMessage(
        error instanceof Error ? error.message : "Unknown error"
      );
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderMessageContent = (content: string) => {
    let processedContent = content;
    
    Object.keys(GLOSSARY).forEach((term) => {
      const regex = new RegExp(`(${term})`, "g");
      processedContent = processedContent.replace(
        regex,
        `<span class="glossary-term" data-term="${term}">$1</span>`
      );
    });

    processedContent = processedContent
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br />");

    return (
      <div
        className="prose prose-sm max-w-none"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(processedContent, { ALLOWED_TAGS: ['strong', 'br', 'span', 'em', 'b', 'i', 'p', 'ul', 'ol', 'li', 'a', 'h3', 'h4'], ALLOWED_ATTR: ['class', 'title', 'href', 'target', 'rel', 'style'] }) }}
      />
    );
  };

  /**
   * Renders a complete message with text and structured data
   */
  const renderMessage = (message: ChatMessage) => {
    return (
      <>
        {/* Text Content */}
        <div className="message-content">
          {message.role === "assistant" 
            ? renderMessageContent(message.content)
            : message.content
          }
        </div>
        
        {/* Legacy data support (DistrictCharts) */}
        {message.data && (
          <div className="mt-3 pt-3 border-t">
            <DistrictCharts data={message.data} />
          </div>
        )}
        
        {/* Structured Data: Recommendations */}
        {hasRecommendations(message) && (
          <RecommendationCards data={message.structured!.recommendations} />
        )}
        
        {/* Structured Data: Charts */}
        {hasCharts(message) && (
          <ChatChartSection charts={message.structured!.charts!} />
        )}
        
        {/* Structured Data: Suggested Questions */}
        {hasSuggestedQuestions(message) && (
          <SuggestedQuestions 
            questions={message.structured!.suggestedQuestions!} 
            onSelect={handleSend}
          />
        )}
      </>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end p-4 sm:p-6">
      <div 
        className="fixed inset-0 bg-black/20 backdrop-blur-sm"
        onClick={onClose}
      />
      
      <div className="relative w-full max-w-lg h-[600px] max-h-[80vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
              <Bot size={18} />
            </div>
            <div>
              <h3 className="font-semibold text-sm">SpotPick AI</h3>
              <p className="text-xs text-blue-100">창업 입지 전문</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-white/20 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "flex gap-2",
                message.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              {message.role === "assistant" && (
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <Bot size={16} className="text-blue-600" />
                </div>
              )}
              
              <div
                className={cn(
                  "max-w-[80%] rounded-2xl px-4 py-2.5 text-sm",
                  message.role === "user"
                    ? "bg-blue-600 text-white rounded-br-md"
                    : "bg-white shadow-sm border rounded-bl-md"
                )}
              >
                {renderMessage(message)}
              </div>

              {message.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                  <User size={16} className="text-gray-600" />
                </div>
              )}
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex gap-2">
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                <Bot size={16} className="text-blue-600" />
              </div>
              <div className="bg-white shadow-sm border rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2 text-gray-500">
                  <Loader2 size={16} className="animate-spin" />
                  <span className="text-sm">분석 중...</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Questions (initial state) */}
        {messages.length === 1 && (
          <div className="px-4 py-3 border-t bg-white">
            <p className="text-xs text-gray-500 mb-2 flex items-center gap-1">
              <Sparkles size={12} />
              추천 질문
            </p>
            <div className="flex flex-wrap gap-2">
              {DEFAULT_SUGGESTED_QUESTIONS.slice(0, 3).map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(q)}
                  className="text-xs px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full hover:bg-blue-100 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="p-3 border-t bg-white">
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="질문을 입력하세요..."
              disabled={isLoading}
              className="flex-1 px-4 py-2.5 bg-gray-100 rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className="w-10 h-10 bg-blue-600 text-white rounded-full flex items-center justify-center hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Chat Button Component
// ============================================================================

export function ChatButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-6 right-6 w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 hover:scale-105 transition-all flex items-center justify-center z-40"
    >
      <MessageCircle size={24} />
    </button>
  );
}
