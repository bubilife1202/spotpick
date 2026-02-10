"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

const STORAGE_KEY = "builder_curation_industry_code";

/** Fallback industry list used when the API is unavailable. */
const FALLBACK_INDUSTRIES: Industry[] = [
  { code: "CS100001", display_name: "한식", icon: "🍚" },
  { code: "CS100002", display_name: "중식", icon: "🥟" },
  { code: "CS100003", display_name: "일식", icon: "🍣" },
  { code: "CS100004", display_name: "양식", icon: "🍝" },
  { code: "CS100005", display_name: "베이커리", icon: "🍞" },
  { code: "CS100006", display_name: "패스트푸드", icon: "🍔" },
  { code: "CS100007", display_name: "치킨", icon: "🍗" },
  { code: "CS100008", display_name: "분식", icon: "🍜" },
  { code: "CS100009", display_name: "호프/주점", icon: "🍺" },
  { code: "CS100010", display_name: "카페", icon: "☕" },
];

/** Map from industry code to emoji icon. */
const ICON_MAP: Record<string, string> = {
  CS100001: "🍚",
  CS100002: "🥟",
  CS100003: "🍣",
  CS100004: "🍝",
  CS100005: "🍞",
  CS100006: "🍔",
  CS100007: "🍗",
  CS100008: "🍜",
  CS100009: "🍺",
  CS100010: "☕",
};

interface Industry {
  code: string;
  display_name: string;
  icon: string;
  available?: boolean;
}

interface IndustrySelectorProps {
  value?: string;
  onChange?: (code: string) => void;
  /** If true, show as a horizontal scroll strip instead of a 2x5 grid. */
  compact?: boolean;
}

export function IndustrySelector({ value, onChange, compact }: IndustrySelectorProps) {
  const [industries, setIndustries] = useState<Industry[]>(FALLBACK_INDUSTRIES);
  const [selected, setSelected] = useState<string>(value ?? "");
  const [loading, setLoading] = useState(true);

  // Sync controlled value prop
  useEffect(() => {
    if (value !== undefined) {
      setSelected(value);
    }
  }, [value]);

  // Hydrate from localStorage when no controlled value is provided
  useEffect(() => {
    if (value === undefined) {
      try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
          setSelected(stored);
        }
      } catch {
        // localStorage not available (SSR or private browsing)
      }
    }
  }, [value]);

  // Fetch industry list from API
  useEffect(() => {
    let cancelled = false;

    async function fetchIndustries() {
      try {
        const res = await fetch(`${API_BASE}/industries`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const items = Array.isArray(data) ? data : data.industries ?? [];
        if (!cancelled && items.length > 0) {
          const mapped: Industry[] = items.map((item: { code?: string; display_name?: string; icon?: string; data_available?: boolean }) => ({
            code: item.code ?? "",
            display_name: item.display_name ?? item.code ?? "",
            icon: item.icon ?? ICON_MAP[item.code ?? ""] ?? "🍽️",
            available: item.data_available ?? true,
          }));
          setIndustries(mapped);
        }
      } catch {
        // API unavailable -- keep fallback list
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchIndustries();
    return () => { cancelled = true; };
  }, []);

  const handleSelect = (code: string) => {
    const industry = industries.find((i) => i.code === code);
    if (industry && industry.available === false) return;
    const next = selected === code ? "" : code;
    setSelected(next);

    // Persist to localStorage
    try {
      if (next) {
        localStorage.setItem(STORAGE_KEY, next);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // localStorage not available
    }

    onChange?.(next);
  };

  // ----- Compact (horizontal scroll strip) -----
  if (compact) {
    return (
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
        {industries.map((industry) => (
          (() => {
            const disabled = industry.available === false;
            return (
          <button
            key={industry.code}
            onClick={() => handleSelect(industry.code)}
            className={cn(
              "flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm font-medium transition-all whitespace-nowrap",
              selected === industry.code
                ? "border-blue-500 bg-blue-50 text-blue-700"
                : disabled
                  ? "border-gray-200 bg-white text-gray-400 opacity-60 cursor-not-allowed"
                  : "border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50"
            )}
          >
            <span className="text-base">{ICON_MAP[industry.code] ?? industry.icon}</span>
            <span>{industry.display_name}</span>
            {disabled && (
              <span className="ml-1 rounded-full bg-slate-400 px-1.5 py-0.5 text-[9px] font-bold text-white">
                준비 중
              </span>
            )}
          </button>
            );
          })()
        ))}
      </div>
    );
  }

  // ----- Standard grid (2 columns x 5 rows) -----
  return (
    <div
      className={cn(
        "grid grid-cols-2 gap-3",
        loading && "animate-pulse"
      )}
    >
      {industries.map((industry) => (
        (() => {
          const disabled = industry.available === false;
          return (
        <button
          key={industry.code}
          onClick={() => handleSelect(industry.code)}
          className={cn(
            "p-4 rounded-xl border-2 text-left transition-all",
            selected === industry.code
              ? "border-blue-500 bg-blue-50 shadow-sm"
              : disabled
                ? "border-gray-200 bg-white opacity-60 cursor-not-allowed"
                : "border-gray-200 hover:border-gray-300 bg-white"
          )}
        >
          <span className="text-2xl block mb-1">
            {ICON_MAP[industry.code] ?? industry.icon}
          </span>
          <p
            className={cn(
              "font-medium",
              selected === industry.code ? "text-blue-700" : "text-gray-900"
            )}
          >
            {industry.display_name}
          </p>
          {disabled && (
            <span className="mt-2 inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">
              준비 중
            </span>
          )}
        </button>
          );
        })()
      ))}
    </div>
  );
}
