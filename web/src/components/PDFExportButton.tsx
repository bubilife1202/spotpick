"use client";

import { useState } from "react";
import { FileDown, Loader2 } from "lucide-react";
import { ChatMessage, RecommendationCardData, ChartData, CompetitiveInsight, SimulationData } from "@/types/chat";

// ============================================================================
// Props Types
// ============================================================================

interface PDFExportButtonProps {
  messages: ChatMessage[];
  industryName?: string;
  className?: string;
}

// ============================================================================
// PDF Export Button Component
// ============================================================================

/**
 * PDF 리포트 내보내기 버튼
 *
 * 대화 기록에서 추천, 차트, 시뮬레이션 등 데이터를 수집하여
 * PDF 리포트로 내보냅니다.
 */
export function PDFExportButton({
  messages,
  industryName = "카페",
  className = "",
}: PDFExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setIsExporting(true);
    setError(null);

    try {
      // 메시지에서 구조화된 데이터 수집
      const conversationData = extractConversationData(messages);

      if (!hasExportableData(conversationData)) {
        setError("PDF로 내보낼 데이터가 없습니다. 먼저 상권 추천을 받아보세요.");
        setIsExporting(false);
        return;
      }

      // API 호출
      const response = await fetch("/api/v1/pdf/report", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          conversation_data: conversationData,
          industry_name: industryName,
          filename: `${industryName}_창업_리포트.pdf`,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "알 수 없는 오류" }));
        throw new Error(errorData.detail || "PDF 생성에 실패했습니다.");
      }

      // PDF 다운로드
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${industryName}_창업_리포트.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

    } catch (err) {
      console.error("PDF 내보내기 오류:", err);
      setError(err instanceof Error ? err.message : "PDF 생성 중 오류가 발생했습니다.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className={className}>
      <button
        onClick={handleExport}
        disabled={isExporting}
        className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isExporting ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            <span>PDF 생성 중...</span>
          </>
        ) : (
          <>
            <FileDown size={16} />
            <span>PDF 다운로드</span>
          </>
        )}
      </button>

      {error && (
        <div className="mt-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * 메시지 목록에서 PDF 생성에 필요한 데이터 추출
 */
function extractConversationData(messages: ChatMessage[]) {
  let recommendations: RecommendationCardData[] = [];
  let charts: ChartData[] = [];
  let competitive: CompetitiveInsight | null = null;
  let simulation: SimulationData | null = null;
  let context: Record<string, unknown> = {};

  // 가장 최근 어시스턴트 메시지부터 역순으로 탐색
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    if (msg.role !== "assistant" || !msg.structured) continue;

    // 추천 데이터 (첫 번째 발견한 것만)
    if (!recommendations.length && msg.structured?.recommendations?.length) {
      recommendations = msg.structured.recommendations;
    }

    // 차트 데이터 (모두 수집)
    if (msg.structured?.charts?.length) {
      charts = [...charts, ...msg.structured.charts];
    }

    // 경쟁 분석 (첫 번째 발견한 것만)
    if (!competitive && msg.structured?.competitive) {
      competitive = msg.structured.competitive;
    }

    // 시뮬레이션 (첫 번째 발견한 것만)
    if (!simulation && msg.structured?.simulation) {
      simulation = msg.structured.simulation;
    }
  }

  // 컨텍스트 추출 (가장 최근 것)
  const lastAssistantMsg = messages
    .slice()
    .reverse()
    .find((m) => m.role === "assistant" && m.structured);

  if (lastAssistantMsg?.structured) {
    // structured에서 context를 찾거나, 추천의 첫 번째 항목에서 district 등 추출
    if (recommendations.length > 0) {
      const firstRec = recommendations[0];
      context = {
        district: firstRec.district_name || "",
        budget_min: firstRec.estimated_rent ? firstRec.estimated_rent * 10 : undefined,
        budget_max: firstRec.estimated_rent ? firstRec.estimated_rent * 15 : undefined,
      };
    }
  }

  return {
    recommendations,
    charts,
    competitive,
    simulation,
    context,
  };
}

/**
 * 내보낼 데이터가 있는지 확인
 */
function hasExportableData(data: ReturnType<typeof extractConversationData>): boolean {
  return (
    data.recommendations.length > 0 ||
    data.charts.length > 0 ||
    !!data.competitive ||
    !!data.simulation
  );
}
