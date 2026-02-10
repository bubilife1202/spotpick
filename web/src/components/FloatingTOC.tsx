"use client";

import { useState } from "react";
import { List, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface TOCItem {
  id: string;
  label: string;
  icon?: string;
}

const REPORT_SECTIONS: TOCItem[] = [
  { id: "section-top3", label: "TOP 3 추천", icon: "🏆" },
  { id: "group-core", label: "핵심 판단 근거", icon: "🎯" },
  { id: "group-detail", label: "상세 분석", icon: "🔍" },
  { id: "group-risk", label: "리스크 & 지원", icon: "🛡️" },
];

export function FloatingTOC() {
  const [isOpen, setIsOpen] = useState(false);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setIsOpen(false);
    }
  };

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "fixed bottom-6 right-6 z-40 flex h-12 w-12 items-center justify-center rounded-full shadow-lg transition-all lg:hidden",
          isOpen
            ? "bg-slate-800 text-white"
            : "bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:shadow-xl",
        )}
      >
        {isOpen ? <X className="h-5 w-5" /> : <List className="h-5 w-5" />}
      </button>

      {/* TOC panel */}
      {isOpen && (
        <div className="fixed bottom-20 right-6 z-40 w-56 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl lg:hidden">
          <div className="border-b border-slate-100 px-4 py-2.5">
            <p className="text-xs font-bold text-slate-900">섹션 이동</p>
          </div>
          <div className="max-h-80 overflow-y-auto p-1.5">
            {REPORT_SECTIONS.map((section) => (
              <button
                key={section.id}
                onClick={() => scrollTo(section.id)}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs font-medium text-slate-600 transition hover:bg-blue-50 hover:text-blue-700"
              >
                <span className="text-sm">{section.icon}</span>
                {section.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
