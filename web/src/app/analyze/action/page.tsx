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
  Database,
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
  const budget = Number(searchParams?.get("budget")) || Number(searchParams?.get("budget_max")) || store.budget;

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

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60_000);

      const requestBody = {
        industry_code: industryCode,
        district_code: districtCode,
        budget,
        area_pyeong: 15,
      };

      try {
        const res = await fetch(`${API_BASE}/business-plan/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(requestBody),
          signal: controller.signal,
        });

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          console.error("Business plan request body:", requestBody);
          console.error("Business plan error response:", errorData);
          const detail = errorData.detail || `API 오류 (${res.status})`;
          throw new Error(detail);
        }

        const data = await res.json();
        setSections(data.sections || []);
        if (data.sections?.length > 0) {
          setExpandedSection(data.sections[0].id);
        }
      } catch (err) {
        console.error("Business plan request body:", requestBody);
        console.error("Business plan error:", err);
        if (err instanceof DOMException && err.name === "AbortError") {
          setError("사업계획서 생성 시간이 초과되었습니다. 다시 시도해주세요.");
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("사업계획서 생성 중 오류가 발생했습니다. 다시 시도해주세요.");
        }
      } finally {
        clearTimeout(timeoutId);
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
      // Build conversation_data matching the backend PDFReportRequest schema
      const cachedData = store.sectionData[districtCode] || {};
      const conversationData = {
        recommendations: store.topDistricts.map((d) => ({
          district_code: d.district_code,
          district_name: d.district_name,
          scorecard_total: d.scorecard_total,
          monthly_sales: d.monthly_sales,
          store_count: d.store_count,
          survival_rate: d.survival_rate,
        })),
        simulation: cachedData.simulation || {},
        competitive: cachedData.competition || {},
        timeline: cachedData.timeline || {},
        support_programs: cachedData.support || [],
        charts: cachedData.customer || {},
        context: {
          industry_code: industryCode,
          industry_name: store.industryName || "카페",
          district_code: districtCode,
          district_name: selectedDistrict?.district_name || "",
          budget,
          sections: sections.map((s) => ({ title: s.title, content: s.content })),
        },
      };

      const res = await fetch(`${API_BASE}/pdf/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_data: conversationData,
          industry_name: store.industryName || "카페",
        }),
      });

      if (!res.ok) throw new Error("PDF generation failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `SpotPick_사업계획서_${selectedDistrict?.district_name || districtCode}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download error:", err);
      alert("사업계획서 생성 중 오류가 발생했습니다. 다시 시도해주세요.");
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
            href={`/analyze/report?industry_code=${industryCode}&budget=${budget}`}
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

        {/* AI Consultation Context Card */}
        {selectedDistrict && (
          <div className="mb-6 rounded-xl border border-blue-100 bg-blue-50/50 p-4">
            <div className="mb-2 flex items-center gap-2">
              <Database className="h-4 w-4 text-blue-500" />
              <p className="text-xs font-bold text-blue-900">AI 상담 기반 데이터</p>
            </div>
            <p className="text-xs leading-relaxed text-blue-800">
              AI 상담은 아래 데이터를 기반으로 답변합니다:
            </p>
            <ul className="mt-1 space-y-0.5 text-xs text-blue-700">
              <li>· {selectedDistrict.district_name} 상권 분석 결과</li>
              <li>· {store.industryName || "카페"} 업종 매출·경쟁·입지 데이터</li>
              <li>· 서울시 공공데이터 (상권분석서비스)</li>
            </ul>
          </div>
        )}

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
            {selectedDistrict && (
              <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-600">
                {selectedDistrict.district_name} · {store.industryName}
              </span>
            )}
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
