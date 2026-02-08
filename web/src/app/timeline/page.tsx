"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  MapPin,
  Loader2,
  CheckCircle2,
  Clock,
  Banknote,
  FileCheck,
  Hammer,
  Megaphone,
  Settings,
  Sparkles,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface TimelineItem {
  day: number;
  title: string;
  detail: string;
  cost_man: number;
  duration: string;
  category: string;
}

interface Permit {
  order: number;
  name: string;
  agency: string;
  duration: string;
  cost: number;
  required: boolean;
}

const CATEGORY_STYLES: Record<string, { color: string; icon: React.ReactNode }> = {
  "인허가": { color: "bg-amber-500", icon: <FileCheck className="h-3.5 w-3.5" /> },
  "자금": { color: "bg-emerald-500", icon: <Banknote className="h-3.5 w-3.5" /> },
  "시설": { color: "bg-blue-500", icon: <Hammer className="h-3.5 w-3.5" /> },
  "운영": { color: "bg-purple-500", icon: <Settings className="h-3.5 w-3.5" /> },
  "마케팅": { color: "bg-rose-500", icon: <Megaphone className="h-3.5 w-3.5" /> },
};

function getDayLabel(day: number): string {
  if (day === 0) return "D-Day";
  if (day < 0) return `D${day}`;
  return `D+${day}`;
}

/* ─── Timeline Content ─────────────────────────────────────── */
function TimelineContent() {
  const searchParams = useSearchParams();
  const districtCode = searchParams?.get("district_code") || "";
  const industryCode = searchParams?.get("industry_code") || "CS100010";
  const budget = Number(searchParams?.get("budget")) || 5000;

  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [permits, setPermits] = useState<Permit[]>([]);
  const [notes, setNotes] = useState<string[]>([]);
  const [summary, setSummary] = useState<{ district_name?: string; industry_name?: string; estimated_rent?: number; budget_man?: number }>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Permit checklist state (persisted to localStorage)
  const [checked, setChecked] = useState<Record<string, boolean>>(() => {
    if (typeof window === "undefined") return {};
    try {
      return JSON.parse(localStorage.getItem(`permits_${industryCode}`) || "{}");
    } catch {
      return {};
    }
  });

  const togglePermit = (name: string) => {
    setChecked((prev) => {
      const next = { ...prev, [name]: !prev[name] };
      try {
        localStorage.setItem(`permits_${industryCode}`, JSON.stringify(next));
      } catch { /* noop */ }
      return next;
    });
  };

  useEffect(() => {
    if (!districtCode) {
      setError("상권 코드가 필요합니다. 분석 페이지에서 다시 시작하세요.");
      setLoading(false);
      return;
    }
    const fetchTimeline = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({
          district_code: districtCode,
          industry_code: industryCode,
          budget: String(budget),
        });
        const res = await fetch(`${API_BASE}/timeline/generate?${params}`);
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        setTimeline(data.timeline || []);
        setPermits(data.permits || []);
        setNotes(data.notes || []);
        setSummary(data.summary || {});
      } catch {
        setError("타임라인 생성에 실패했습니다.");
      } finally {
        setLoading(false);
      }
    };
    fetchTimeline();
  }, [districtCode, industryCode, budget]);

  const totalCost = timeline.reduce((sum, t) => sum + (t.cost_man || 0), 0);
  const checkedCount = permits.filter((p) => checked[p.name]).length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600">
              <MapPin className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-bold text-slate-900">SpotPick</span>
          </Link>
          <Link
            href="/analyze"
            className="text-sm font-medium text-slate-500 hover:text-slate-700"
          >
            분석으로 돌아가기
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-20 pt-8 sm:px-6">
        <div className="mb-8 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-50 px-3 py-1 text-xs font-semibold text-purple-700">
            <Sparkles className="h-3.5 w-3.5" />
            AI 맞춤 생성
          </span>
          <h1 className="mt-3 text-2xl font-extrabold text-slate-900 sm:text-3xl">
            창업 타임라인
          </h1>
          {summary.district_name && (
            <p className="mt-1 text-sm text-slate-500">
              {summary.district_name} · {summary.industry_name} · 예산 {budget.toLocaleString()}만원
            </p>
          )}
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
            <p className="mt-3 text-sm text-slate-500">AI가 맞춤 타임라인을 생성하고 있습니다...</p>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center">
            <p className="text-sm text-rose-600">{error}</p>
            <Link
              href="/analyze"
              className="mt-3 inline-block text-sm font-semibold text-blue-600 hover:text-blue-700"
            >
              분석 페이지로 이동
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-xl border border-slate-200 bg-white p-4 text-center">
                <Clock className="mx-auto h-5 w-5 text-slate-400" />
                <p className="mt-1 text-lg font-extrabold text-slate-900">{timeline.length}</p>
                <p className="text-[10px] text-slate-500">마일스톤</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 text-center">
                <Banknote className="mx-auto h-5 w-5 text-emerald-500" />
                <p className="mt-1 text-lg font-extrabold text-slate-900">{totalCost.toLocaleString()}</p>
                <p className="text-[10px] text-slate-500">예상 비용 (만원)</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 text-center">
                <FileCheck className="mx-auto h-5 w-5 text-amber-500" />
                <p className="mt-1 text-lg font-extrabold text-slate-900">
                  {checkedCount}/{permits.length}
                </p>
                <p className="text-[10px] text-slate-500">인허가 완료</p>
              </div>
            </div>

            {/* Timeline */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <h2 className="mb-4 text-sm font-bold text-slate-900">실행 타임라인</h2>
              <div className="relative ml-4 border-l-2 border-slate-200 pl-6">
                {timeline.map((item, i) => {
                  const cat = CATEGORY_STYLES[item.category] || CATEGORY_STYLES["운영"];
                  const isOpen = item.day === 0;
                  return (
                    <div key={i} className="relative mb-6 last:mb-0">
                      {/* Dot */}
                      <div
                        className={cn(
                          "absolute -left-[31px] flex h-5 w-5 items-center justify-center rounded-full text-white",
                          isOpen ? "bg-gradient-to-br from-blue-600 to-indigo-600 ring-4 ring-blue-100" : cat.color,
                        )}
                      >
                        {cat.icon}
                      </div>

                      <div className={cn("rounded-xl border p-4", isOpen ? "border-blue-200 bg-blue-50/50" : "border-slate-100 bg-slate-50/30")}>
                        <div className="mb-1 flex items-center gap-2">
                          <span className={cn(
                            "rounded-full px-2 py-0.5 text-[10px] font-bold",
                            isOpen ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-500",
                          )}>
                            {getDayLabel(item.day)}
                          </span>
                          <span className={cn(
                            "rounded-full px-2 py-0.5 text-[10px] font-bold text-white",
                            cat.color,
                          )}>
                            {item.category}
                          </span>
                          {item.duration && (
                            <span className="text-[10px] text-slate-400">{item.duration}</span>
                          )}
                        </div>
                        <p className="text-sm font-bold text-slate-900">{item.title}</p>
                        <p className="mt-0.5 text-xs text-slate-500">{item.detail}</p>
                        {item.cost_man > 0 && (
                          <p className="mt-1 text-[10px] font-semibold text-emerald-600">
                            예상 비용: {item.cost_man.toLocaleString()}만원
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Permit Checklist */}
            {permits.length > 0 && (
              <div className="rounded-2xl border border-slate-200 bg-white p-6">
                <div className="mb-4 flex items-center gap-2">
                  <FileCheck className="h-5 w-5 text-amber-500" />
                  <h2 className="text-sm font-bold text-slate-900">인허가 체크리스트</h2>
                  <span className="ml-auto rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                    {checkedCount}/{permits.length} 완료
                  </span>
                </div>

                {/* Progress bar */}
                <div className="mb-4 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-400 to-amber-500 transition-all duration-500"
                    style={{ width: `${permits.length > 0 ? (checkedCount / permits.length) * 100 : 0}%` }}
                  />
                </div>

                <div className="space-y-2">
                  {permits.map((p) => (
                    <button
                      key={p.name}
                      onClick={() => togglePermit(p.name)}
                      className={cn(
                        "flex w-full items-start gap-3 rounded-xl border p-3 text-left transition",
                        checked[p.name]
                          ? "border-emerald-200 bg-emerald-50/50"
                          : "border-slate-100 bg-white hover:border-slate-200",
                      )}
                    >
                      <CheckCircle2
                        className={cn(
                          "mt-0.5 h-5 w-5 shrink-0 transition",
                          checked[p.name] ? "text-emerald-500" : "text-slate-200",
                        )}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className={cn("text-sm font-semibold", checked[p.name] ? "text-emerald-700 line-through" : "text-slate-900")}>
                            {p.name}
                          </p>
                          {p.required && (
                            <span className="rounded bg-rose-50 px-1.5 py-0.5 text-[9px] font-bold text-rose-600">
                              필수
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-slate-500">
                          {p.agency} · {p.duration}
                          {p.cost > 0 && ` · ${p.cost.toLocaleString()}원`}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>

                {/* Notes */}
                {notes.length > 0 && (
                  <div className="mt-4 rounded-xl bg-amber-50/50 p-3">
                    <p className="mb-1 text-[10px] font-bold text-amber-700">참고 사항</p>
                    <ul className="space-y-0.5 text-[11px] text-amber-900/70">
                      {notes.map((n, i) => (
                        <li key={i}>· {n}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default function TimelinePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <TimelineContent />
    </Suspense>
  );
}
