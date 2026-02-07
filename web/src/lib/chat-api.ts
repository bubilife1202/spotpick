/**
 * Chat API Module
 * 
 * Handles communication with the chat backend, including:
 * - Simple text chat
 * - Streaming responses
 * - Structured responses with recommendations, charts, and maps
 */

import {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  DistrictAnalysis,
  StructuredChatResponse,
  StreamingChunk,
  MessageStructuredData,
  DEFAULT_SUGGESTED_QUESTIONS,
  GLOSSARY,
} from "@/types/chat";

// Re-export types for backward compatibility
export type { ChatMessage, DistrictAnalysis, ChatRequest, ChatResponse };
export { GLOSSARY };

// Re-export suggested questions for backward compatibility
export const SUGGESTED_QUESTIONS = [...DEFAULT_SUGGESTED_QUESTIONS];

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002/api/v1";

function getStoredIndustryCode(): string {
  if (typeof window === "undefined") return "CS100010";
  return window.localStorage.getItem("builder_curation_industry_code") || "CS100010";
}

function loadStoredChatContext(): ChatRequest["context"] | undefined {
  if (typeof window === "undefined") return undefined;
  const raw = window.localStorage.getItem("builder_curation_onboarding_context");
  if (!raw) return undefined;

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return undefined;

    const p = parsed as Record<string, unknown>;
    const ctx: ChatRequest["context"] = {};

    if (typeof p.district === "string" && p.district.trim()) ctx.district = p.district;
    if (typeof p.budget_min === "number") ctx.budget_min = p.budget_min;
    if (typeof p.budget_max === "number") ctx.budget_max = p.budget_max;
    if (typeof p.cafe_type === "string" && p.cafe_type.trim()) ctx.cafe_type = p.cafe_type;

    return Object.keys(ctx).length > 0 ? ctx : undefined;
  } catch {
    return undefined;
  }
}

// ============================================================================
// Simple Chat API (backward compatible)
// ============================================================================

/**
 * Send a chat message and receive a text reply
 * @param message - User's message text
 * @param history - Previous messages for context
 * @returns Promise resolving to the assistant's reply text
 */
export async function sendChatMessage(
  message: string,
  history: ChatMessage[]
): Promise<string> {
  const context = loadStoredChatContext();
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      industry_code: getStoredIndustryCode(),
      history: history.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      })),
      ...(context ? { context } : {}),
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to send message");
  }

  const data: ChatResponse = await response.json();
  return data.reply;
}

// ============================================================================
// Structured Chat API
// ============================================================================

/**
 * Send a chat message and receive a structured response
 * Includes recommendations, charts, maps, and suggested questions
 * 
 * @param message - User's message text
 * @param history - Previous messages for context
 * @returns Promise resolving to structured chat response
 */
export async function sendStructuredChatMessage(
  message: string,
  history: ChatMessage[]
): Promise<StructuredChatResponse> {
  const context = loadStoredChatContext();
  // Backend returns the structured payload directly from `/chat`.
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      industry_code: getStoredIndustryCode(),
      history: history.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      })),
      ...(context ? { context } : {}),
    }),
  });

  if (!response.ok) {
    // Fallback to simple chat if structured endpoint not available
    if (response.status === 404) {
      const textReply = await sendChatMessage(message, history);
      return {
        reply: textReply,
        recommendations: [],
        charts: [],
        suggested_questions: [...DEFAULT_SUGGESTED_QUESTIONS],
        context: {},
      };
    }
    throw new Error("Failed to send structured message");
  }

  return response.json();
}

// ============================================================================
// Streaming Chat API
// ============================================================================

/**
 * Stream a chat message response (text only)
 * @param message - User's message text
 * @param history - Previous messages for context
 * @yields Text chunks as they arrive
 */
export async function* streamChatMessage(
  message: string,
  history: ChatMessage[]
): AsyncGenerator<string> {
  const context = loadStoredChatContext();
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      industry_code: getStoredIndustryCode(),
      history: history.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      })),
      ...(context ? { context } : {}),
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to stream message");
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No reader available");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.text) yield data.text;
          if (data.done) return;
        } catch {
          continue;
        }
      }
    }
  }
}

/**
 * Streaming chunk result with text and optional structured data
 */
export interface StreamedChunkResult {
  /** Text content (may be partial) */
  text?: string;
  /** Whether streaming is complete */
  done: boolean;
  /** Structured data (only on final chunk) */
  structured?: MessageStructuredData;
}

/**
 * Stream a chat message with structured response support
 * Text streams progressively, structured data arrives at end
 * 
 * @param message - User's message text
 * @param history - Previous messages for context
 * @yields Streaming chunks with text and final structured data
 */
export async function* streamStructuredChatMessage(
  message: string,
  history: ChatMessage[]
): AsyncGenerator<StreamedChunkResult> {
  const context = loadStoredChatContext();
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      industry_code: getStoredIndustryCode(),
      history: history.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      })),
      ...(context ? { context } : {}),
    }),
  });

  if (!response.ok) {
    // Fallback to simple streaming if structured endpoint not available
    if (response.status === 404) {
      for await (const text of streamChatMessage(message, history)) {
        yield { text, done: false };
      }
      yield { done: true };
      return;
    }
    throw new Error("Failed to stream structured message");
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No reader available");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const chunk: StreamingChunk = JSON.parse(line.slice(6));
          
          if (chunk.error) {
            throw new Error(chunk.error.message);
          }
          
          if (chunk.done) {
            yield { 
              done: true, 
              structured: chunk.structured 
            };
            return;
          }
          
          if (chunk.text) {
            yield { 
              text: chunk.text, 
              done: false 
            };
          }
        } catch (e) {
          // Skip malformed JSON lines
          if (e instanceof SyntaxError) continue;
          throw e;
        }
      }
    }
  }

  // Ensure we always emit a final done chunk
  yield { done: true };
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Parse a text response and attempt to extract structured data
 * Useful for responses that embed JSON in markdown code blocks
 * 
 * @param text - Response text potentially containing JSON
 * @returns Extracted structured data or undefined
 */
export function parseStructuredFromText(text: string): MessageStructuredData | undefined {
  // Look for JSON in markdown code blocks
  const jsonMatch = text.match(/```json\n([\s\S]*?)\n```/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[1]);
      return {
        recommendations: parsed.recommendations,
        charts: parsed.charts,
        maps: parsed.maps,
        suggestedQuestions: parsed.suggested_questions,
      };
    } catch {
      return undefined;
    }
  }
  return undefined;
}

/**
 * Create a new user message object
 * @param content - Message text
 * @returns ChatMessage object
 */
export function createUserMessage(content: string): ChatMessage {
  return {
    id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    role: "user",
    content,
    timestamp: new Date(),
  };
}

/**
 * Create a new assistant message object
 * @param content - Message text
 * @param structured - Optional structured data
 * @returns ChatMessage object
 */
export function createAssistantMessage(
  content: string,
  structured?: MessageStructuredData
): ChatMessage {
  return {
    id: `assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    role: "assistant",
    content,
    timestamp: new Date(),
    structured,
  };
}

/**
 * Create a streaming placeholder message
 * @returns ChatMessage object with isStreaming flag
 */
export function createStreamingMessage(): ChatMessage {
  return {
    id: `streaming-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    role: "assistant",
    content: "",
    timestamp: new Date(),
    isStreaming: true,
  };
}

/**
 * Create an error message
 * @param errorMessage - Error description
 * @returns ChatMessage object with error state
 */
export function createErrorMessage(errorMessage: string): ChatMessage {
  return {
    id: `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    role: "assistant",
    content: "죄송합니다, 일시적인 오류가 발생했습니다. 다시 시도해주세요.",
    timestamp: new Date(),
    error: {
      code: "UNKNOWN_ERROR",
      message: errorMessage,
    },
  };
}
