"use client";

import React from "react";
import { SupportProgramData } from "@/types/chat";

interface SupportProgramCardProps {
  program: SupportProgramData;
}

/**
 * 정부 창업 지원사업 카드 컴포넌트
 *
 * 사업명, 지원대상, 신청기간, 지원금액, 마감 D-day를 표시합니다.
 */
export function SupportProgramCard({ program }: SupportProgramCardProps) {
  const {
    program_name,
    support_target,
    support_amount,
    application_start_date,
    application_end_date,
    managing_org,
    executing_org,
    detail_url,
    days_until_deadline,
  } = program;

  // 마감 임박 뱃지 스타일 결정
  const getDeadlineBadge = () => {
    if (days_until_deadline < 0) {
      return {
        text: "마감",
        bgColor: "bg-gray-400",
        textColor: "text-white",
      };
    } else if (days_until_deadline <= 3) {
      return {
        text: `D-${days_until_deadline}`,
        bgColor: "bg-red-500",
        textColor: "text-white",
      };
    } else if (days_until_deadline <= 7) {
      return {
        text: `D-${days_until_deadline}`,
        bgColor: "bg-orange-500",
        textColor: "text-white",
      };
    } else if (days_until_deadline <= 14) {
      return {
        text: `D-${days_until_deadline}`,
        bgColor: "bg-yellow-500",
        textColor: "text-gray-900",
      };
    } else {
      return {
        text: `D-${days_until_deadline}`,
        bgColor: "bg-green-100",
        textColor: "text-green-800",
      };
    }
  };

  const badge = getDeadlineBadge();

  // 날짜 포맷팅 (YYYY-MM-DD → MM.DD)
  const formatDate = (dateStr: string) => {
    try {
      const [, month, day] = dateStr.split("-");
      return `${month}.${day}`;
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow p-4 sm:p-5">
      {/* 헤더: 사업명 + D-day 뱃지 */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="font-bold text-base sm:text-lg text-gray-900 flex-1 leading-tight">
          {program_name}
        </h3>
        <span
          className={`px-2.5 py-1 rounded-full text-xs font-bold whitespace-nowrap ${badge.bgColor} ${badge.textColor}`}
        >
          {badge.text}
        </span>
      </div>

      {/* 지원대상 */}
      <div className="mb-3">
        <span className="inline-flex items-center gap-1.5 text-sm text-gray-700">
          <svg
            className="w-4 h-4 text-blue-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
            />
          </svg>
          <span className="font-medium">대상:</span> {support_target}
        </span>
      </div>

      {/* 지원금액 */}
      <div className="mb-3">
        <span className="inline-flex items-center gap-1.5 text-sm text-gray-700">
          <svg
            className="w-4 h-4 text-green-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="font-medium">지원금:</span> {support_amount}
        </span>
      </div>

      {/* 신청기간 */}
      <div className="mb-4">
        <span className="inline-flex items-center gap-1.5 text-sm text-gray-700">
          <svg
            className="w-4 h-4 text-purple-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <span className="font-medium">신청:</span>{" "}
          {formatDate(application_start_date)} ~ {formatDate(application_end_date)}
        </span>
      </div>

      {/* 기관 정보 */}
      <div className="flex flex-wrap gap-2 mb-4 text-xs text-gray-600">
        <span className="bg-gray-100 px-2 py-1 rounded">
          {managing_org}
        </span>
        {executing_org !== managing_org && (
          <span className="bg-gray-100 px-2 py-1 rounded">
            {executing_org}
          </span>
        )}
      </div>

      {/* 상세 보기 버튼 */}
      <a
        href={detail_url}
        target="_blank"
        rel="noopener noreferrer"
        className="block w-full text-center bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-lg transition-colors"
      >
        상세 보기
      </a>
    </div>
  );
}

interface SupportProgramListProps {
  programs: SupportProgramData[];
}

/**
 * 지원사업 목록 컴포넌트 (그리드 레이아웃)
 */
export function SupportProgramList({ programs }: SupportProgramListProps) {
  if (programs.length === 0) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
        <p className="text-yellow-800 text-sm">
          현재 신청 가능한 지원사업이 없습니다.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {programs.map((program) => (
        <SupportProgramCard key={program.program_id} program={program} />
      ))}
    </div>
  );
}
