"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useAnalyzeStore } from "@/lib/analyze-store";
import { AnalyzeStepper } from "@/components/AnalyzeStepper";
import {
  MapPin,
  Download,
  MessageCircle,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface BusinessPlanSection {
  id: string;
  title: string;
  content: string;
}

function ActionContent() {
  const searchParams = useSearchParams();
  const store = useAnalyzeStore();

  const industryCode = searchParams?.get("industry_code") || store.industryCode;
  const districtCode = searchParams?.get("district_code") || store.selectedDistrictCode;
  const budgetMin = Number(searchParams?.get("budget_min")) || store.budgetMin;
  const budgetMax = Number(searchParams?.get("budget_max")) || store.budgetMax;

  const [sections, setSections] = useState<BusinessPlanSection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    store.setStep(3);

    if (!districtCode) {
      setError("상권이 선택되지 않았습니다. 리포트 페이지에서 상권을 선택해주세요.");
      setLoading(false);
      return;
    }

    const generatePlan = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/business-plan`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            industry_code: industryCode,
            district_code: districtCode,
            budget: Math.round((budgetMin + budgetMax) / 2),
            area_pyeong: 15,
          }),
        });

        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        setSections(data.sections || []);
        if (data.sections?.length > 0) {
          setExpandedSection(data.sections[0].id);
        }
      } catch (err) {
        setError("사업계획서 생성 중 오류가 발생했습니다. 다시 시도해주세요.");
        console.error("Business plan error:", err);
      } finally {
        setLoading(false);
      }
    };

    generatePlan();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [districtCode, industryCode]);

  const handlePdfDownload = async () => {
    if (!districtCode || sections.length === 0) return;
    setPdfLoading(true);
    try {
      const res = await fetch(`${API_BASE}/pdf/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          industry_code: industryCode,
          district_code: districtCode,
          budget: Math.round((budgetMin + budgetMax) / 2),
          sections: sections,
        }),
      });

      if (!res.ok) throw new Error("PDF generation failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `SpotPick_사업계획서_${districtCode}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download error:", err);
      alert("PDF 다운로드에 실패했습니다. 다시 시도해주세요.");
    } finally {
      setPdfLoading(false);
    }
  };

  const selectedDistrict = store.topDistricts.find(
    (d) => d.district_code === districtCode,
  );

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
            href={`/analyze/report?industry_code=${industryCode}&budget_min=${budgetMin}&budget_max=${budgetMax}`}
            className="flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-slate-700"
          >
            <ArrowLeft className="h-4 w-4" />
            리포트로 돌아가기
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-20 pt-8 sm:px-6">
        {/* Stepper */}
        <AnalyzeStepper currentStep={3} className="mb-8" />

        {/* Title */}
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-extrabold text-slate-900 sm:text-3xl">
            AI 사업계획서 & 액션 플랜
          </h1>
          {selectedDistrict && (
            <p className="mt-1 text-sm text-slate-500">
              {selectedDistrict.district_name} / {store.industryName}
            </p>
          )}
        </div>

        {/* Action buttons */}
        <div className="mb-6 flex flex-col gap-3 sm:flex-row">
          <button
            onClick={handlePdfDownload}
            disabled={pdfLoading || sections.length === 0}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-md transition hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-50"
          >
            {pdfLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            PDF 다운로드
          </button>
          <Link
            href={`/chat?industry_code=${industryCode}&district_code=${districtCode}`}
            className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          >
            <MessageCircle className="h-4 w-4" />
            AI 상담 시작
          </Link>
        </div>

        {/* Business plan content */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
            <p className="mt-4 text-sm text-slate-500">
              AI가 사업계획서를 생성하고 있습니다...
            </p>
            <p className="mt-1 text-xs text-slate-400">약 30초 소요</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-rose-200 bg-rose-50 py-12">
            <p className="text-sm text-rose-600">{error}</p>
            <Link
              href="/analyze/report"
              className="mt-4 rounded-lg bg-white px-4 py-2 text-xs font-semibold text-slate-700 shadow-sm"
            >
              리포트로 돌아가기
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {sections.map((section) => {
              const isExpanded = expandedSection === section.id;
              return (
                <div
                  key={section.id}
                  className="rounded-2xl border border-slate-200 bg-white transition-shadow hover:shadow-sm"
                >
                  <button
                    onClick={() =>
                      setExpandedSection(isExpanded ? null : section.id)
                    }
                    className="flex w-full items-center justify-between px-6 py-4"
                  >
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                      <h3 className="text-sm font-bold text-slate-900">
                        {section.title}
                      </h3>
                    </div>
                    <span
                      className={cn(
                        "text-xs text-slate-400 transition-transform",
                        isExpanded && "rotate-180",
                      )}
                    >
                      &#9660;
                    </span>
                  </button>

                  {isExpanded && (
                    <div className="border-t border-slate-100 px-6 py-4">
                      <div className="prose prose-sm prose-slate max-w-none">
                        {section.content.split("\n").map((line, i) => (
                          <p key={i} className="mb-2 text-sm leading-relaxed text-slate-700">
                            {line}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Restart */}
        <div className="mt-10 text-center">
          <Link
            href="/analyze"
            className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-700"
          >
            <RefreshCw className="h-4 w-4" />
            처음부터 다시 분석하기
          </Link>
        </div>
      </main>
    </div>
  );
}

export default function AnalyzeActionPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <ActionContent />
    </Suspense>
  );
}
