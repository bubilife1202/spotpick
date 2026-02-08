// Simple analytics event tracker
// Tracks key user journey events for understanding conversion funnel

type EventName =
  | "page_view"
  | "journey_start"
  | "industry_select"
  | "franchise_compare"
  | "franchise_choice"
  | "location_search"
  | "district_select"
  | "report_view"
  | "simulation_run"
  | "support_match"
  | "business_plan_generate"
  | "business_plan_download"
  | "cta_click"
  | "premium_nudge_shown"
  | "premium_nudge_click";

interface AnalyticsEvent {
  event: EventName;
  properties?: Record<string, string | number | boolean>;
  timestamp: number;
}

// Store events in memory + localStorage for demo
const EVENT_QUEUE: AnalyticsEvent[] = [];
const STORAGE_KEY = "spotpick_events";

export function track(event: EventName, properties?: Record<string, string | number | boolean>) {
  const entry: AnalyticsEvent = {
    event,
    properties,
    timestamp: Date.now(),
  };

  EVENT_QUEUE.push(entry);

  // Persist to localStorage
  if (typeof window !== "undefined") {
    try {
      const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      stored.push(entry);
      // Keep last 500 events
      if (stored.length > 500) stored.splice(0, stored.length - 500);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
    } catch {}
  }

  // Log in development
  if (process.env.NODE_ENV === "development") {
    console.log(`[Analytics] ${event}`, properties || "");
  }
}

export function getEvents(): AnalyticsEvent[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

export function getJourneyFunnel(): Record<string, number> {
  const events = getEvents();
  const funnel: Record<string, number> = {};
  for (const e of events) {
    funnel[e.event] = (funnel[e.event] || 0) + 1;
  }
  return funnel;
}
