"use client";

import Link from "next/link";
import { MapPin, Sparkles, GitCommit, Zap, Brain, RefreshCw } from "lucide-react";

const MILESTONES = [
  {
    version: "v0.1.0",
    date: "2026-01-15",
    title: "MVP 런칭",
    desc: "서울시 상권 데이터 파싱 + 카페 업종 기본 추천 알고리즘",
    ai: "데이터 파이프라인 설계, API 스캐폴딩, 기본 스코어카드 로직 전체를 AI와 페어프로그래밍",
  },
  {
    version: "v0.3.0",
    date: "2026-01-22",
    title: "10개 업종 확장",
    desc: "한식~호프/주점 전 업종 지원, 프랜차이즈 정보공개서 통합",
    ai: "업종별 가중치 매트릭스, 프랜차이즈 API 연동 전체를 AI가 생성하고 사람이 검증",
  },
  {
    version: "v0.5.0",
    date: "2026-01-28",
    title: "AI 리포트 엔진",
    desc: "Gemini 기반 상권 분석 리포트, 리스크 판정, 경쟁 분석 자동 생성",
    ai: "프롬프트 엔지니어링, 폴백 로직, 리포트 섹션 구조 전체를 AI가 설계",
  },
  {
    version: "v0.7.0",
    date: "2026-02-01",
    title: "원페이지 리포트 + 시뮬레이터",
    desc: "5대 카테고리 레이더, 워터폴 수익 구조, 인라인 시뮬레이터",
    ai: "React 컴포넌트 설계, 차트 시각화, 슬라이더 UX 전체를 AI가 구현",
  },
  {
    version: "v0.9.0",
    date: "2026-02-06",
    title: "3-Step 워크플로우",
    desc: "입력 → AI 리포트 → 사업계획서+PDF, 경쟁지도, 매출 트렌드",
    ai: "전체 UX 플로우 재설계, 컴포넌트 리팩토링, PDF 생성 파이프라인을 AI가 주도",
  },
  {
    version: "v0.9.5",
    date: "2026-02-09",
    title: "비교 분석 + 타임라인 + 리스크 알림",
    desc: "상권 A vs B 비교, AI 타임라인, 폐업 위험도 분석, 인허가 체크리스트",
    ai: "5개 신규 API + 3개 프론트엔드 페이지를 AI 단독으로 설계·구현·테스트",
  },
];

const AI_METRICS = [
  { label: "AI 생성 코드", value: "95%+", desc: "전체 코드베이스 중 AI가 생성한 비율" },
  { label: "일평균 배포", value: "3.2회", desc: "지속적 배포를 통한 빠른 이터레이션" },
  { label: "API 엔드포인트", value: "40+", desc: "자동 생성된 REST API 수" },
  { label: "에러 복구 속도", value: "<5분", desc: "AI가 에러를 감지하고 수정하는 평균 시간" },
];

export default function DevLogPage() {
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
            href="/"
            className="text-sm font-medium text-slate-500 hover:text-slate-700"
          >
            홈으로
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-20 pt-8 sm:px-6">
        <div className="mb-10 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
            <Brain className="h-3.5 w-3.5" />
            AI-Native Development
          </span>
          <h1 className="mt-3 text-2xl font-extrabold text-slate-900 sm:text-3xl">
            빌드 히스토리
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            SpotPick은 AI를 도구가 아닌 공동 창업자로 활용해 구축되었습니다
          </p>
        </div>

        {/* Metrics */}
        <div className="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {AI_METRICS.map((m) => (
            <div
              key={m.label}
              className="rounded-2xl border border-slate-200 bg-white p-4 text-center shadow-sm"
            >
              <p className="text-2xl font-extrabold text-slate-900">{m.value}</p>
              <p className="mt-0.5 text-xs font-semibold text-slate-700">{m.label}</p>
              <p className="mt-0.5 text-[10px] text-slate-400">{m.desc}</p>
            </div>
          ))}
        </div>

        {/* AI Philosophy */}
        <div className="mb-10 rounded-2xl border border-indigo-100 bg-indigo-50/30 p-6">
          <div className="mb-3 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-500" />
            <h2 className="text-sm font-bold text-indigo-900">AI-Native 철학</h2>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-xl bg-white/80 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-indigo-600">
                <Zap className="h-3.5 w-3.5" />
                <p className="text-xs font-bold">AI = 공동 창업자</p>
              </div>
              <p className="text-[11px] text-slate-600">
                설계·구현·테스트 전 과정에서 AI가 주도적으로 의사결정에 참여
              </p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-indigo-600">
                <RefreshCw className="h-3.5 w-3.5" />
                <p className="text-xs font-bold">빠른 실행 루프</p>
              </div>
              <p className="text-[11px] text-slate-600">
                문제 발견 → AI 분석 → 수정 → 배포를 5분 이내에 완료하는 사이클
              </p>
            </div>
            <div className="rounded-xl bg-white/80 p-3">
              <div className="mb-1 flex items-center gap-1.5 text-indigo-600">
                <Brain className="h-3.5 w-3.5" />
                <p className="text-xs font-bold">태스크 분해</p>
              </div>
              <p className="text-[11px] text-slate-600">
                복잡한 기능을 마이크로 태스크로 분해하고 AI에게 위임하여 병렬 처리
              </p>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="relative ml-4 border-l-2 border-indigo-200 pl-6">
          {MILESTONES.map((m, i) => (
            <div key={i} className="relative mb-8 last:mb-0">
              {/* Dot */}
              <div className="absolute -left-[31px] flex h-5 w-5 items-center justify-center rounded-full bg-indigo-500 text-white">
                <GitCommit className="h-3 w-3" />
              </div>

              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-2 flex items-center gap-2">
                  <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-[10px] font-bold text-indigo-600">
                    {m.version}
                  </span>
                  <span className="text-[10px] text-slate-400">{m.date}</span>
                </div>
                <h3 className="text-sm font-bold text-slate-900">{m.title}</h3>
                <p className="mt-1 text-xs text-slate-600">{m.desc}</p>
                <div className="mt-3 flex items-start gap-2 rounded-lg bg-indigo-50/50 p-2.5">
                  <Sparkles className="mt-0.5 h-3 w-3 shrink-0 text-indigo-400" />
                  <p className="text-[11px] leading-relaxed text-indigo-700">{m.ai}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
