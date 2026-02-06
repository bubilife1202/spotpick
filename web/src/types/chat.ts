/**
 * Chat Message Types for Conversation-Driven UI
 * 
 * This module defines TypeScript types for the chat interface,
 * including structured responses with charts, recommendations, and maps.
 */

// ============================================================================
// Chart Data Types
// ============================================================================

/**
 * Supported chart types for visualization
 */
export type ChartType = 'time' | 'day' | 'age' | 'gender';

/**
 * Single data point for chart visualization
 */
export interface ChartDataPoint {
  /** Display label for the data point */
  name: string;
  /** Numeric value */
  value: number;
  /** Optional additional label */
  label?: string;
}

/**
 * Chart configuration with data
 */
export interface ChartData {
  /** Chart type determining visualization style */
  type: ChartType;
  /** Display title for the chart */
  title: string;
  /** Data points to visualize */
  data: ChartDataPoint[];
  /** Optional highlight information (e.g., "피크: 점심시간") */
  highlight?: string;
}

// ============================================================================
// Recommendation Card Types
// ============================================================================

/**
 * Detailed recommendation data for a district/area
 * Compatible with existing LocationRecommendation structure
 */
export interface RecommendationCardData {
  /** Ranking position (1-based) */
  rank: number;
  /** Name of the district/area (e.g., "홍대입구역") */
  district_name: string;
  /** Type of commercial area (발달상권, 골목상권, 전통시장, 관광특구) */
  district_type: string;
  /** Predicted success probability (0.0 - 1.0) */
  success_probability: number;
  /** Estimated monthly rent in KRW */
  estimated_rent: number;
  /** Peak business hours (e.g., "점심(11-14시)") */
  peak_time: string;
  /** Primary customer age group (e.g., "20대") */
  main_age_group: string;
  /** List of potential risk factors */
  risk_factors: string[];
  /** Strategic recommendations */
  recommendations: string[];
  
  // Extended fields for detailed analysis
  /** Estimated monthly sales in KRW */
  monthly_sales?: number;
  /** Number of competing stores */
  store_count?: number;
  /** 2-year survival rate (0.0 - 1.0) */
  survival_rate?: number;
  /** Geographic coordinates */
  coordinates?: {
    lat: number;
    lng: number;
  };
  /** Key success factors for the location */
  key_success_factors?: string[];
  /** Address string */
  address?: string;
}

// ============================================================================
// Map Types
// ============================================================================

/**
 * Marker types for map visualization
 */
export type MapMarkerType = 'recommended' | 'competitor' | 'selected' | 'alternative';

/**
 * Map marker configuration
 */
export interface MapMarker {
  /** Latitude coordinate */
  lat: number;
  /** Longitude coordinate */
  lng: number;
  /** Display label for the marker */
  label: string;
  /** Marker type determining style */
  type?: MapMarkerType;
  /** Optional popup content */
  popup?: string;
  /** Reference to recommendation rank (if applicable) */
  rank?: number;
}

/**
 * Map viewport configuration
 */
export interface MapViewport {
  /** Center latitude */
  centerLat: number;
  /** Center longitude */
  centerLng: number;
  /** Zoom level (1-20) */
  zoom: number;
}

// ============================================================================
// Structured Response Types
// ============================================================================

/**
 * Context information extracted from conversation
 */
export interface ConversationContext {
  /** Selected district/area name */
  district?: string;
  /** Minimum budget in KRW */
  budget_min?: number;
  /** Maximum budget in KRW */
  budget_max?: number;
  /** Type of commercial area preference */
  area_type?: string;
  /** Target customer demographics */
  target_demographic?: string;
  /** Preferred business hours */
  preferred_hours?: string;
  /** Additional user preferences */
  preferences?: Record<string, string | number | boolean>;
}

/**
 * Structured response from the chat API
 * Contains both text reply and interactive components
 */
export interface StructuredChatResponse {
  /** Natural language reply text */
  reply: string;
  /** Ranked location recommendations */
  recommendations: RecommendationCardData[];
  /** Data visualizations */
  charts: ChartData[];
  /** Map markers for location display */
  maps?: MapMarker[];
  /** Map viewport settings */
  mapViewport?: MapViewport;
  /** Follow-up questions to guide conversation */
  suggested_questions: string[];
  /** Extracted conversation context */
  context: ConversationContext;
  /** Response metadata */
  metadata?: {
    /** Processing time in ms */
    processingTime?: number;
    /** Data freshness timestamp */
    dataTimestamp?: string;
    /** Confidence score for the response */
    confidence?: number;
  };
}

// ============================================================================
// Message Types
// ============================================================================

/**
 * Structured data attached to assistant messages
 * All fields are optional for progressive enhancement
 */
export interface MessageStructuredData {
  /** Location recommendations */
  recommendations?: RecommendationCardData[];
  /** Chart visualizations */
  charts?: ChartData[];
  /** Map markers */
  maps?: MapMarker[];
  /** Map viewport configuration */
  mapViewport?: MapViewport;
  /** Suggested follow-up questions */
  suggestedQuestions?: string[];
}

/**
 * Chat message role
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * Complete chat message structure
 * Backward compatible with existing ChatMessage type
 */
export interface ChatMessage {
  /** Unique message identifier */
  id: string;
  /** Message sender role */
  role: MessageRole;
  /** Text content of the message */
  content: string;
  /** Message timestamp */
  timestamp: Date;
  
  /**
   * Structured data for rich responses (assistant messages only)
   * @example
   * ```typescript
   * if (message.structured?.recommendations) {
   *   // Render recommendation cards
   * }
   * ```
   */
  structured?: MessageStructuredData;
  
  /**
   * Legacy district analysis data
   * @deprecated Use structured.charts instead
   */
  data?: DistrictAnalysis;
  
  /** Whether the message is currently streaming */
  isStreaming?: boolean;
  
  /** Error state for failed messages */
  error?: {
    code: string;
    message: string;
  };
}

// ============================================================================
// Conversation State Types
// ============================================================================

/**
 * Budget range specification
 */
export interface BudgetRange {
  /** Minimum budget in KRW */
  min: number;
  /** Maximum budget in KRW */
  max: number;
}

/**
 * Complete conversation state
 * For use with state management (useState, Redux, Zustand, etc.)
 */
export interface ConversationState {
  /** All messages in the conversation */
  messages: ChatMessage[];
  /** Accumulated context from conversation */
  context: {
    district?: string;
    budget?: BudgetRange;
    preferences?: Record<string, string | number | boolean>;
    /** Conversation intent (e.g., "finding_location", "comparing_areas") */
    intent?: string;
  };
  /** Loading state for API calls */
  isLoading: boolean;
  /** Current streaming message ID (if any) */
  streamingMessageId?: string;
  /** Error state */
  error?: {
    code: string;
    message: string;
  } | null;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

/**
 * Chat API request payload
 */
export interface ChatRequest {
  /** User's message text */
  message: string;
  /** Conversation history for context */
  history?: Array<{
    role: string;
    content: string;
  }>;
  /** Session context */
  context?: ConversationContext;
}

/**
 * Simple chat response (text only)
 */
export interface ChatResponse {
  /** Reply text */
  reply: string;
}

/**
 * Streaming chunk from chat API
 */
export interface StreamingChunk {
  /** Text content chunk */
  text?: string;
  /** Whether streaming is complete */
  done?: boolean;
  /** Partial structured data */
  structured?: Partial<MessageStructuredData>;
  /** Error during streaming */
  error?: {
    code: string;
    message: string;
  };
}

// ============================================================================
// Legacy Types (for backward compatibility)
// ============================================================================

/**
 * District analysis data structure
 * Used by DistrictCharts component
 */
export interface DistrictAnalysis {
  district_name: string;
  district_type: string;
  success_probability: number;
  estimated_monthly_rent: number;
  estimated_monthly_sales: number;
  survival_rate_2y: number;
  time_analysis: {
    peak_time: string;
    peak_day: string;
    time_00_06: number;
    time_06_11: number;
    time_11_14: number;
    time_14_17: number;
    time_17_21: number;
    time_21_24: number;
  };
  day_analysis: {
    peak_day: string;
    weekday_ratio: number;
    weekend_ratio: number;
    mon: number;
    tue: number;
    wed: number;
    thu: number;
    fri: number;
    sat: number;
    sun: number;
  };
  customer_analysis: {
    main_age_group: string;
    male_ratio: number;
    female_ratio: number;
    age_10: number;
    age_20: number;
    age_30: number;
    age_40: number;
    age_50: number;
    age_60: number;
  };
  competition: {
    store_count: number;
    new_stores: number;
    closed_stores: number;
    franchise_stores: number;
    franchise_ratio: number;
  };
  risk_factors: string[];
  key_success_factors: string[];
}

// ============================================================================
// Type Guards
// ============================================================================

/**
 * Check if a message has structured recommendation data
 */
export function hasRecommendations(message: ChatMessage): boolean {
  return Boolean(
    message.structured?.recommendations && 
    message.structured.recommendations.length > 0
  );
}

/**
 * Check if a message has chart data
 */
export function hasCharts(message: ChatMessage): boolean {
  return Boolean(
    message.structured?.charts && 
    message.structured.charts.length > 0
  );
}

/**
 * Check if a message has map markers
 */
export function hasMaps(message: ChatMessage): boolean {
  return Boolean(
    message.structured?.maps && 
    message.structured.maps.length > 0
  );
}

/**
 * Check if a message has suggested questions
 */
export function hasSuggestedQuestions(message: ChatMessage): boolean {
  return Boolean(
    message.structured?.suggestedQuestions && 
    message.structured.suggestedQuestions.length > 0
  );
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Default suggested questions for new conversations
 */
export const DEFAULT_SUGGESTED_QUESTIONS = [
  "홍대에서 20대 여성 타겟 카페 추천해줘",
  "강남 vs 성수 상권 비교해줘",
  "월세 300만원대 골목상권 추천",
  "점심 피크 상권 알려줘",
  "창업 초보가 주의할 점이 뭐야?",
] as const;

/**
 * Glossary terms for tooltip display
 */
export const GLOSSARY: Record<string, string> = {
  "생존율": "창업 후 2년 동안 폐업하지 않고 운영을 유지한 매장의 비율입니다. 90% 이상이면 안정적인 상권입니다.",
  "발달상권": "대로변이나 번화가에 위치한 상권으로, 유동인구가 많고 임대료가 높습니다.",
  "골목상권": "주택가 안쪽에 위치한 소규모 상권으로, 임대료가 낮고 단골 고객 위주입니다.",
  "전통시장": "재래시장 주변 상권으로, 중장년층 고객이 많고 임대료가 저렴합니다.",
  "관광특구": "외국인 관광객이 많은 지역으로, 계절/상황에 따른 변동이 큽니다.",
  "피크 시간": "하루 중 매출이 가장 높은 시간대입니다.",
  "프랜차이즈 비율": "해당 상권 내 프랜차이즈 매장의 비율입니다. 높으면 경쟁이 치열합니다.",
} as const;
