"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  FileText,
  TrendingUp,
  DollarSign,
  Store,
  Shield,
  CalendarDays,
  ChevronRight,
  Loader2,
  CheckCircle,
  RefreshCw,
  Pencil,
  ShoppingBag,
  Megaphone,
} from "lucide-react";
import DOMPurify from "dompurify";
import { cn } from "@/lib/utils";

// ============================================================================
// Constants
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

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

const SECTION_ICONS: Record<string, React.ReactNode> = {
  overview: <FileText className="w-4 h-4" />,
  market: <TrendingUp className="w-4 h-4" />,
  competition: <Store className="w-4 h-4" />,
  menu: <ShoppingBag className="w-4 h-4" />,
  marketing: <Megaphone className="w-4 h-4" />,
  financials: <DollarSign className="w-4 h-4" />,
  risk: <Shield className="w-4 h-4" />,
  roadmap: <CalendarDays className="w-4 h-4" />,
};

// ============================================================================
// Types
// ============================================================================

interface PlanSection {
  id: string;
  title: string;
  content: string;
  data?: Record<string, unknown>;
}

interface BusinessPlanData {
  business_name: string;
  district_name: string;
  industry_name: string;
  sections: PlanSection[];
  generated_at: string;
}

type Stage = "confirm" | "loading" | "preview";

interface LoadingStep {
  label: string;
  done: boolean;
}

// ============================================================================
// Markdown → HTML (simple converter for generated content)
// ============================================================================

function markdownToHtml(md: string): string {
  let html = md;

  // Escape HTML entities first (except our markdown chars)
  html = html
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Restore markdown-style blockquote (> at start of line)
  html = html.replace(/^&gt;\s?(.*)$/gm, "<blockquote>$1</blockquote>");
  // Merge consecutive blockquotes
  html = html.replace(/<\/blockquote>\n<blockquote>/g, "<br/>");

  // Tables
  html = html.replace(
    /^\|(.+)\|\s*\n\|[-| :]+\|\s*\n((?:\|.+\|\s*\n?)*)/gm,
    (_match, headerRow: string, bodyRows: string) => {
      const headers = headerRow.split("|").map((h: string) => h.trim()).filter(Boolean);
      const thRow = headers.map((h: string) => `<th>${h}</th>`).join("");
      const rows = bodyRows.trim().split("\n").map((row: string) => {
        const cells = row.split("|").map((c: string) => c.trim()).filter(Boolean);
        return `<tr>${cells.map((c: string) => `<td>${c}</td>`).join("")}</tr>`;
      }).join("");
      return `<div class="table-wrap"><table><thead><tr>${thRow}</tr></thead><tbody>${rows}</tbody></table></div>`;
    },
  );

  // Headers
  html = html.replace(/^#### (.+)$/gm, '<h4 class="bp-h4">$1</h4>');
  html = html.replace(/^### (.+)$/gm, '<h3 class="bp-h3">$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2 class="bp-h2">$1</h2>');

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Ordered lists
  html = html.replace(/^(\d+)\.\s+(.+)$/gm, '<li class="bp-oli">$2</li>');
  html = html.replace(/((?:<li class="bp-oli">.*<\/li>\n?)+)/g, '<ol class="bp-ol">$1</ol>');

  // Unordered lists
  html = html.replace(/^- (.+)$/gm, '<li class="bp-uli">$1</li>');
  html = html.replace(/((?:<li class="bp-uli">.*<\/li>\n?)+)/g, '<ul class="bp-ul">$1</ul>');

  // Paragraphs: wrap loose lines that aren't already wrapped in tags
  html = html
    .split("\n\n")
    .map((block) => {
      const trimmed = block.trim();
      if (!trimmed) return "";
      if (
        trimmed.startsWith("<") ||
        trimmed.startsWith("#")
      )
        return trimmed;
      return `<p>${trimmed.replace(/\n/g, "<br/>")}</p>`;
    })
    .join("\n");

  return html;
}

// ============================================================================
// Components
// ============================================================================

function ConfirmScreen({
  industryCode,
  districtName,
  industryName,
  budget,
  areaPyeong,
  onGenerate,
}: {
  industryCode: string;
  districtName: string;
  industryName: string;
  budget: number;
  areaPyeong: number;
  onGenerate: (businessName: string) => void;
}) {
  const [businessName, setBusinessName] = useState("");
  const icon = INDUSTRY_ICONS[industryCode] || "🏪";

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-8 text-white text-center">
            <div className="text-4xl mb-3">{icon}</div>
            <h1 className="text-xl font-bold">AI 사업계획서</h1>
            <p className="text-blue-100 text-sm mt-1">입력 정보를 확인하고 생성하세요</p>
          </div>

          {/* Info Cards */}
          <div className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <InfoCard label="업종" value={`${icon} ${industryName}`} />
              <InfoCard label="상권" value={districtName} />
              <InfoCard label="총 예산" value={`${budget.toLocaleString()}만원`} />
              <InfoCard label="매장 면적" value={`${areaPyeong}평`} />
            </div>

            {/* Business Name Input */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                상호명 (선택)
              </label>
              <input
                type="text"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                placeholder="예) 카페 모닝글로우"
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              />
            </div>

            {/* Generate Button */}
            <button
              onClick={() => onGenerate(businessName)}
              className="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold text-lg hover:from-blue-700 hover:to-indigo-700 transition-all shadow-md hover:shadow-lg active:scale-[0.98]"
            >
              사업계획서 생성하기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-50 rounded-xl px-4 py-3 border border-slate-100">
      <div className="text-xs text-slate-500 mb-0.5">{label}</div>
      <div className="text-sm font-semibold text-slate-800 truncate">{value}</div>
    </div>
  );
}

function LoadingScreen({ steps }: { steps: LoadingStep[] }) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-50 rounded-2xl mb-4">
              <FileText className="w-8 h-8 text-blue-600" />
            </div>
            <h2 className="text-lg font-bold text-slate-800">사업계획서 생성 중</h2>
            <p className="text-sm text-slate-500 mt-1">잠시만 기다려주세요...</p>
          </div>

          <div className="space-y-3">
            {steps.map((step, i) => (
              <div
                key={i}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-500",
                  step.done
                    ? "bg-emerald-50 border border-emerald-100"
                    : i === steps.findIndex((s) => !s.done)
                    ? "bg-blue-50 border border-blue-100"
                    : "bg-slate-50 border border-slate-100",
                )}
              >
                {step.done ? (
                  <CheckCircle className="w-5 h-5 text-emerald-500 shrink-0" />
                ) : i === steps.findIndex((s) => !s.done) ? (
                  <Loader2 className="w-5 h-5 text-blue-500 animate-spin shrink-0" />
                ) : (
                  <div className="w-5 h-5 rounded-full border-2 border-slate-200 shrink-0" />
                )}
                <span
                  className={cn(
                    "text-sm font-medium",
                    step.done ? "text-emerald-700" : i === steps.findIndex((s) => !s.done) ? "text-blue-700" : "text-slate-400",
                  )}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>

          {/* Progress bar */}
          <div className="mt-6 h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-700"
              style={{
                width: `${(steps.filter((s) => s.done).length / steps.length) * 100}%`,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function PreviewScreen({
  plan,
  onRegenerate,
}: {
  plan: BusinessPlanData;
  onRegenerate: () => void;
}) {
  const [activeSection, setActiveSection] = useState(0);
  const sectionRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  };

  const scrollToSection = (idx: number) => {
    setActiveSection(idx);
    sectionRefs.current[idx]?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  // Track active section on scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const idx = sectionRefs.current.findIndex((ref) => ref === entry.target);
            if (idx >= 0) setActiveSection(idx);
          }
        }
      },
      { rootMargin: "-20% 0px -60% 0px" },
    );

    sectionRefs.current.forEach((ref) => {
      if (ref) observer.observe(ref);
    });

    return () => observer.disconnect();
  }, [plan]);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-slate-800 text-white px-6 py-3 rounded-xl shadow-lg text-sm animate-fade-in">
          {toast}
        </div>
      )}

      {/* Header */}
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-blue-600" />
            <div>
              <h1 className="text-sm font-bold text-slate-800">{plan.business_name}</h1>
              <p className="text-xs text-slate-500">
                {plan.industry_name} · {plan.district_name}
              </p>
            </div>
          </div>
          <div className="text-xs text-slate-400">
            {new Date(plan.generated_at).toLocaleDateString("ko-KR")} 생성
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto flex">
        {/* Sidebar (목차) — desktop only */}
        <aside className="hidden lg:block w-64 shrink-0 sticky top-14 h-[calc(100vh-3.5rem)] overflow-y-auto border-r border-slate-200 bg-white">
          <nav className="p-4 space-y-1">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              목차
            </div>
            {plan.sections.map((sec, i) => (
              <button
                key={sec.id}
                onClick={() => scrollToSection(i)}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left transition-all text-sm",
                  activeSection === i
                    ? "bg-blue-50 text-blue-700 font-semibold"
                    : "text-slate-600 hover:bg-slate-50",
                )}
              >
                <span className="shrink-0">{SECTION_ICONS[sec.id] || <ChevronRight className="w-4 h-4" />}</span>
                <span className="truncate">{sec.title}</span>
              </button>
            ))}
          </nav>
        </aside>

        {/* Mobile Section Navigation */}
        <div className="lg:hidden sticky top-14 z-30 bg-white border-b border-slate-200 overflow-x-auto">
          <div className="flex gap-1 p-2 min-w-max">
            {plan.sections.map((sec, i) => (
              <button
                key={sec.id}
                onClick={() => scrollToSection(i)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs whitespace-nowrap transition",
                  activeSection === i
                    ? "bg-blue-50 text-blue-700 font-semibold"
                    : "text-slate-500 hover:bg-slate-50",
                )}
              >
                {SECTION_ICONS[sec.id]}
                <span>{sec.title.replace(/^\d+\.\s*/, "")}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <main className="flex-1 min-w-0 px-4 lg:px-8 py-8 space-y-8">
          {plan.sections.map((sec, i) => (
            <div
              key={sec.id}
              ref={(el) => { sectionRefs.current[i] = el; }}
              className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden"
            >
              {/* Section header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
                <div className="flex items-center gap-2.5">
                  <span className="text-blue-600">{SECTION_ICONS[sec.id]}</span>
                  <h2 className="font-bold text-slate-800">{sec.title}</h2>
                </div>
                <button
                  onClick={() => showToast("향후 AI 수정 기능 지원 예정입니다")}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition"
                >
                  <Pencil className="w-3.5 h-3.5" />
                  수정
                </button>
              </div>

              {/* Section body */}
              <div
                className="bp-content px-6 py-6"
                dangerouslySetInnerHTML={{
                  __html: DOMPurify.sanitize(markdownToHtml(sec.content), {
                    ALLOWED_TAGS: [
                      "h2", "h3", "h4", "p", "br", "strong", "em",
                      "table", "thead", "tbody", "tr", "th", "td",
                      "ul", "ol", "li", "blockquote", "div", "span",
                    ],
                    ALLOWED_ATTR: ["class"],
                  }),
                }}
              />
            </div>
          ))}

          {/* Bottom CTA */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4 pb-12">
            <button
              onClick={onRegenerate}
              className="flex items-center justify-center gap-2 px-6 py-3.5 bg-white border border-slate-200 rounded-xl text-slate-700 font-medium hover:bg-slate-50 transition shadow-sm"
            >
              <RefreshCw className="w-4 h-4" />
              조건 바꿔서 다시 생성
            </button>
          </div>
        </main>
      </div>

      {/* Inline styles for business-plan content */}
      <style jsx global>{`
        .bp-content .bp-h2 {
          display: none; /* Already shown in section header */
        }
        .bp-content .bp-h3 {
          font-size: 1rem;
          font-weight: 700;
          color: #1e293b;
          margin: 1.5rem 0 0.75rem 0;
          padding-bottom: 0.5rem;
          border-bottom: 1px solid #f1f5f9;
        }
        .bp-content .bp-h4 {
          font-size: 0.925rem;
          font-weight: 600;
          color: #334155;
          margin: 1.25rem 0 0.5rem 0;
        }
        .bp-content p {
          color: #475569;
          line-height: 1.7;
          margin: 0.5rem 0;
          font-size: 0.9rem;
        }
        .bp-content strong {
          color: #1e293b;
          font-weight: 600;
        }
        .bp-content .table-wrap {
          overflow-x: auto;
          margin: 0.75rem 0;
          border-radius: 0.75rem;
          border: 1px solid #e2e8f0;
        }
        .bp-content table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.85rem;
        }
        .bp-content th {
          background: #f8fafc;
          color: #475569;
          font-weight: 600;
          text-align: left;
          padding: 0.625rem 0.875rem;
          border-bottom: 1px solid #e2e8f0;
          white-space: nowrap;
        }
        .bp-content td {
          padding: 0.5rem 0.875rem;
          border-bottom: 1px solid #f1f5f9;
          color: #334155;
        }
        .bp-content tr:last-child td {
          border-bottom: none;
        }
        .bp-content tr:hover td {
          background: #f8fafc;
        }
        .bp-content .bp-ul, .bp-content .bp-ol {
          margin: 0.5rem 0;
          padding-left: 1.25rem;
        }
        .bp-content .bp-uli, .bp-content .bp-oli {
          color: #475569;
          font-size: 0.875rem;
          line-height: 1.7;
          margin: 0.25rem 0;
        }
        .bp-content .bp-uli {
          list-style: disc;
        }
        .bp-content .bp-oli {
          list-style: decimal;
        }
        .bp-content blockquote {
          margin: 0.75rem 0;
          padding: 0.75rem 1rem;
          background: #f0f9ff;
          border-left: 3px solid #3b82f6;
          border-radius: 0 0.5rem 0.5rem 0;
          color: #1e40af;
          font-size: 0.85rem;
        }
        @keyframes fade-in {
          from { opacity: 0; transform: translate(-50%, -8px); }
          to { opacity: 1; transform: translate(-50%, 0); }
        }
        .animate-fade-in {
          animation: fade-in 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}

// ============================================================================
// Main Page (inner, uses useSearchParams)
// ============================================================================

function BusinessPlanPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Read params
  const industryCode = searchParams?.get("industry_code") || "CS100010";
  const districtCode = searchParams?.get("district_code") || "";
  const budgetParam = parseInt(searchParams?.get("budget") || "0", 10);
  const areaParam = parseInt(searchParams?.get("area_pyeong") || "15", 10);
  const districtNameParam = searchParams?.get("district_name") || "";

  // Fallbacks from localStorage
  const [budget, setBudget] = useState(budgetParam || 8000);
  const [areaPyeong, setAreaPyeong] = useState(areaParam || 15);
  const [districtName, setDistrictName] = useState(districtNameParam || "");

  useEffect(() => {
    if (!budgetParam) {
      const stored = localStorage.getItem("builder_curation_onboarding_context");
      if (stored) {
        try {
          const ctx = JSON.parse(stored);
          if (ctx.budget) setBudget(ctx.budget);
          if (ctx.area_pyeong) setAreaPyeong(ctx.area_pyeong);
        } catch {}
      }
    }
    if (!districtNameParam) {
      setDistrictName(districtCode);
    }
  }, [budgetParam, districtNameParam, districtCode]);

  const industryName = INDUSTRY_NAMES[industryCode] || "카페";

  const [stage, setStage] = useState<Stage>("confirm");
  const [plan, setPlan] = useState<BusinessPlanData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [loadingSteps, setLoadingSteps] = useState<LoadingStep[]>([
    { label: "상권 데이터 수집", done: false },
    { label: "경쟁 분석", done: false },
    { label: "재무 시뮬레이션", done: false },
    { label: "분석 & 작성", done: false },
    { label: "완료", done: false },
  ]);

  const handleGenerate = async (businessName: string) => {
    setStage("loading");
    setError(null);

    // Reset loading steps
    const steps = [
      { label: "상권 데이터 수집", done: false },
      { label: "경쟁 분석", done: false },
      { label: "재무 시뮬레이션", done: false },
      { label: "분석 & 작성", done: false },
      { label: "완료", done: false },
    ];
    setLoadingSteps([...steps]);

    // Simulate progress steps
    const stepDelays = [600, 1200, 1800, 2400];
    for (let i = 0; i < stepDelays.length; i++) {
      setTimeout(() => {
        setLoadingSteps((prev) =>
          prev.map((s, j) => (j <= i ? { ...s, done: true } : s)),
        );
      }, stepDelays[i]);
    }

    try {
      const res = await fetch(`${API_BASE}/business-plan/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry_code: industryCode,
          district_code: districtCode,
          budget,
          area_pyeong: areaPyeong,
          business_name: businessName || undefined,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `HTTP ${res.status}`);
      }

      const data: BusinessPlanData = await res.json();
      setPlan(data);

      // Mark final step done
      setLoadingSteps((prev) => prev.map((s) => ({ ...s, done: true })));

      // Brief delay then show preview
      setTimeout(() => setStage("preview"), 600);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "알 수 없는 오류";
      setError(msg);
      setStage("confirm");
    }
  };

  const handleRegenerate = () => {
    setPlan(null);
    setStage("confirm");
  };

  if (!districtCode) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-lg p-8 text-center max-w-sm">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h2 className="font-bold text-slate-800 mb-2">상권을 먼저 선택해주세요</h2>
          <p className="text-sm text-slate-500 mb-6">
            대시보드에서 상권을 선택한 후 사업계획서를 생성할 수 있습니다.
          </p>
          <button
            onClick={() => router.push("/results")}
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 transition"
          >
            상권 탐색하기
          </button>
        </div>
      </div>
    );
  }

  if (stage === "loading") {
    return <LoadingScreen steps={loadingSteps} />;
  }

  if (stage === "preview" && plan) {
    return <PreviewScreen plan={plan} onRegenerate={handleRegenerate} />;
  }

  return (
    <>
      {error && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-red-600 text-white px-6 py-3 rounded-xl shadow-lg text-sm animate-fade-in">
          {error}
        </div>
      )}
      <ConfirmScreen
        industryCode={industryCode}
        districtName={districtName || districtCode}
        industryName={industryName}
        budget={budget}
        areaPyeong={areaPyeong}
        onGenerate={handleGenerate}
      />
    </>
  );
}

// ============================================================================
// Page export (with Suspense for useSearchParams)
// ============================================================================

export default function BusinessPlanPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-50 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
        </div>
      }
    >
      <BusinessPlanPageInner />
    </Suspense>
  );
}
