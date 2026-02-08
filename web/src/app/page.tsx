"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  MapPin,
  Store,
  BarChart3,
  Calculator,
  Coins,
  FileText,
  ArrowRight,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Cpu,
  Code2,
  Sparkles,
  Search,
  Trophy,
  MessageCircle,
  Utensils,
  Zap,
  Crown,
} from "lucide-react";

/* ─────────────────────────────────────────────
   Header
   ───────────────────────────────────────────── */
function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-lg">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600">
            <MapPin className="h-4 w-4 text-white" />
          </div>
          <span className="text-lg font-bold text-slate-900">SpotPick</span>
        </Link>

        <nav className="hidden items-center gap-6 text-sm font-medium text-slate-600 md:flex">
          <Link href="/explore" className="transition hover:text-slate-900">
            탐색
          </Link>
          <Link href="/results" className="transition hover:text-slate-900">
            랭킹
          </Link>
          <Link href="/simulator" className="transition hover:text-slate-900">
            시뮬레이터
          </Link>
          <Link href="/support" className="transition hover:text-slate-900">
            지원금
          </Link>
        </nav>

        <Link
          href="/onboarding"
          className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md"
        >
          시작하기
        </Link>
      </div>
    </header>
  );
}

/* ─────────────────────────────────────────────
   Section 1 -- Hero
   ───────────────────────────────────────────── */
function HeroSection() {
  const stats = [
    { value: "1,077", label: "분석상권" },
    { value: "10개", label: "지원업종" },
    { value: "23개", label: "정부지원" },
    { value: "5분", label: "플랜완성" },
  ];

  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-slate-50 to-white py-20 sm:py-28">
      {/* Background decorations */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -right-40 -top-40 h-[500px] w-[500px] rounded-full bg-blue-100/40 blur-3xl" />
        <div className="absolute -left-40 top-40 h-[400px] w-[400px] rounded-full bg-indigo-100/30 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-6xl px-4 text-center sm:px-6">
        <div className="animate-fade-in">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
            <Sparkles className="h-3.5 w-3.5" />
            AI 창업 의사결정 플랫폼
          </span>
        </div>

        <h1 className="animate-slide-up mt-6 text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
          창업, 감으로 하지 마세요
        </h1>

        <p className="animate-slide-up animation-delay-100 mx-auto mt-5 max-w-2xl text-base leading-relaxed text-slate-600 sm:text-lg">
          서울 <strong className="text-slate-800">1,077개 상권</strong> ·{" "}
          <strong className="text-slate-800">10개 업종</strong> ·{" "}
          <strong className="text-slate-800">7종 공공데이터</strong>
          <br />
          AI가 모든 창업 의사결정을 도와드립니다
        </p>

        <div className="animate-slide-up animation-delay-200 mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/onboarding"
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-7 py-3.5 text-base font-semibold text-white shadow-lg shadow-blue-500/25 transition hover:shadow-xl hover:shadow-blue-500/30"
          >
            무료로 시작하기
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/explore"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-7 py-3.5 text-base font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
          >
            지도로 둘러보기
          </Link>
        </div>

        <div className="animate-slide-up animation-delay-300 mt-14 grid grid-cols-2 gap-4 sm:grid-cols-4 sm:gap-6">
          {stats.map((stat, i) => (
            <div
              key={i}
              className="rounded-2xl border border-slate-200/80 bg-white/70 px-4 py-5 shadow-sm backdrop-blur"
            >
              <p className="text-2xl font-extrabold text-slate-900 sm:text-3xl">
                {stat.value}
              </p>
              <p className="mt-1 text-xs font-medium text-slate-500 sm:text-sm">
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────────────────────
   Section 2 -- Pipeline (7-Step Journey)
   ───────────────────────────────────────────── */
const PIPELINE_STEPS = [
  {
    icon: Utensils,
    title: "업종 선택",
    desc: "10개 요식업종 중 선택",
    href: "/onboarding",
  },
  {
    icon: Store,
    title: "프랜차이즈 비교",
    desc: "공정위 공시 데이터 기반",
    href: "/franchise",
  },
  {
    icon: MapPin,
    title: "AI 입지 추천",
    desc: "1,077개 상권 자동 분석",
    href: "/results",
  },
  {
    icon: BarChart3,
    title: "상세 분석",
    desc: "투명 스코어카드 제공",
    href: "/explore",
  },
  {
    icon: Calculator,
    title: "수익 시뮬레이션",
    desc: "손익분기점 자동 계산",
    href: "/simulator",
  },
  {
    icon: Coins,
    title: "지원금 매칭",
    desc: "23개 프로그램 자동 매칭",
    href: "/support",
  },
  {
    icon: FileText,
    title: "사업계획서",
    desc: "AI가 5분 안에 생성",
    href: "/business-plan",
  },
];

function PipelineSection() {
  return (
    <section className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl">
            창업의 모든 단계를 한 곳에서
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-base text-slate-500 sm:text-lg">
            업종 선택부터 사업계획서까지, 7단계 원스톱 여정
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-7 lg:gap-3">
          {PIPELINE_STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <Link
                key={i}
                href={step.href}
                className={cn(
                  "group relative flex flex-row items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-300 hover:shadow-md",
                  "lg:flex-col lg:items-center lg:gap-2 lg:p-5 lg:text-center"
                )}
              >
                {/* Step number badge */}
                <div className="absolute -top-2.5 left-3 flex h-5 w-5 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-[10px] font-bold text-white lg:left-1/2 lg:-translate-x-1/2">
                  {i + 1}
                </div>

                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition group-hover:bg-blue-100 lg:h-14 lg:w-14">
                  <Icon className="h-6 w-6" />
                </div>

                <div className="min-w-0 lg:mt-1">
                  <p className="text-sm font-bold text-slate-900">
                    {step.title}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">{step.desc}</p>
                </div>

                {/* Arrow connector between steps (lg only) */}
                {i < PIPELINE_STEPS.length - 1 && (
                  <ChevronRight className="hidden h-4 w-4 shrink-0 text-slate-300 lg:absolute lg:-right-3.5 lg:top-1/2 lg:block lg:-translate-y-1/2" />
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────────────────────
   Section 3 -- Comparison Table
   ───────────────────────────────────────────── */
type CellStatus = "yes" | "no" | "partial";

const COMPARISON_FEATURES: {
  feature: string;
  openup: CellStatus;
  chatgpt: CellStatus;
  spotpick: CellStatus;
}[] = [
  { feature: "상권 데이터 분석", openup: "yes", chatgpt: "no", spotpick: "yes" },
  { feature: "AI 해석 · 전략", openup: "partial", chatgpt: "yes", spotpick: "yes" },
  { feature: "프랜차이즈 비교", openup: "no", chatgpt: "no", spotpick: "yes" },
  { feature: "수익 시뮬레이션", openup: "no", chatgpt: "no", spotpick: "yes" },
  { feature: "정부지원 매칭", openup: "no", chatgpt: "no", spotpick: "yes" },
  { feature: "상표 검색", openup: "no", chatgpt: "no", spotpick: "yes" },
  { feature: "사업계획서 PDF", openup: "no", chatgpt: "no", spotpick: "yes" },
  { feature: "7단계 원스톱", openup: "no", chatgpt: "no", spotpick: "yes" },
];

function StatusIcon({ status }: { status: CellStatus }) {
  if (status === "yes")
    return <CheckCircle2 className="mx-auto h-5 w-5 text-emerald-500" />;
  if (status === "partial")
    return <AlertTriangle className="mx-auto h-5 w-5 text-amber-500" />;
  return <XCircle className="mx-auto h-5 w-5 text-slate-300" />;
}

function ComparisonSection() {
  return (
    <section className="bg-slate-50 py-20 sm:py-24">
      <div className="mx-auto max-w-4xl px-4 sm:px-6">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl">
            왜 SpotPick인가요?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-base text-slate-500 sm:text-lg">
            기존 서비스와 한눈에 비교해보세요
          </p>
        </div>

        <div className="mt-12 overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full min-w-[480px] text-sm">
            <thead>
              <tr className="border-b border-slate-100 text-xs font-semibold uppercase tracking-wider text-slate-500">
                <th className="py-4 pl-5 pr-3 text-left">기능</th>
                <th className="px-3 py-4 text-center">오픈업</th>
                <th className="px-3 py-4 text-center">ChatGPT</th>
                <th className="px-3 py-4 text-center">
                  <span className="text-blue-600">SpotPick</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON_FEATURES.map((row, i) => (
                <tr
                  key={i}
                  className={cn(
                    "border-b border-slate-50 transition hover:bg-slate-50/60",
                    i === COMPARISON_FEATURES.length - 1 && "border-b-0"
                  )}
                >
                  <td className="py-3.5 pl-5 pr-3 font-medium text-slate-700">
                    {row.feature}
                  </td>
                  <td className="px-3 py-3.5 text-center">
                    <StatusIcon status={row.openup} />
                  </td>
                  <td className="px-3 py-3.5 text-center">
                    <StatusIcon status={row.chatgpt} />
                  </td>
                  <td className="px-3 py-3.5 bg-blue-50/30 text-center">
                    <StatusIcon status={row.spotpick} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────────────────────
   Section 4 -- Entry Points
   ───────────────────────────────────────────── */
const ENTRY_POINTS = [
  {
    question: "어디가 좋을까?",
    label: "AI 입지추천",
    desc: "업종만 고르면 최적 상권을 AI가 골라드려요",
    href: "/onboarding",
    icon: MapPin,
    color: "from-blue-500 to-blue-600",
  },
  {
    question: "여기는 어떨까?",
    label: "위치 진단",
    desc: "관심 상권을 지도에서 찍으면 즉시 진단해드려요",
    href: "/explore",
    icon: Search,
    color: "from-emerald-500 to-emerald-600",
  },
  {
    question: "잘되는 곳 알려줘",
    label: "성공 랭킹",
    desc: "매출 상위 상권을 한눈에 확인하세요",
    href: "/results",
    icon: Trophy,
    color: "from-amber-500 to-amber-600",
  },
  {
    question: "잘 모르겠어",
    label: "AI 상담",
    desc: "어떤 질문이든 AI가 친절하게 안내해드려요",
    href: "/onboarding",
    icon: MessageCircle,
    color: "from-purple-500 to-purple-600",
  },
];

function EntryPointSection() {
  return (
    <section className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl">
            어디서 시작하든, SpotPick이 도와드려요
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-base text-slate-500 sm:text-lg">
            상황에 맞는 진입점을 선택하세요
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {ENTRY_POINTS.map((ep, i) => {
            const Icon = ep.icon;
            return (
              <Link
                key={i}
                href={ep.href}
                className="group flex flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-blue-200 hover:shadow-lg"
              >
                <div
                  className={cn(
                    "flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br text-white",
                    ep.color
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>

                <p className="mt-5 text-lg font-extrabold text-slate-900">
                  &ldquo;{ep.question}&rdquo;
                </p>
                <span className="mt-1 text-sm font-semibold text-blue-600">
                  {ep.label}
                </span>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-500">
                  {ep.desc}
                </p>

                <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-blue-600 transition group-hover:gap-2">
                  바로가기 <ArrowRight className="h-3.5 w-3.5" />
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────────────────────
   Section 5 -- Pricing
   ───────────────────────────────────────────── */
function PricingSection() {
  return (
    <section className="bg-slate-50 py-20 sm:py-24">
      <div className="mx-auto max-w-4xl px-4 sm:px-6">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl">
            합리적인 요금제
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-base text-slate-500 sm:text-lg">
            베타 기간 중 모든 기능을 무료로 이용하세요
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2">
          {/* Free tier */}
          <div className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100">
                <Zap className="h-5 w-5 text-slate-600" />
              </div>
              <div>
                <p className="text-lg font-bold text-slate-900">무료</p>
                <p className="text-2xl font-extrabold text-slate-900">
                  &#8361;0
                </p>
              </div>
            </div>
            <ul className="mt-6 space-y-3 text-sm text-slate-600">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                기본 상권 분석
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                TOP 5 추천
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                사업계획서 1회/일
              </li>
            </ul>
            <Link
              href="/onboarding"
              className="mt-7 block w-full rounded-xl border border-slate-300 py-3 text-center text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
            >
              무료로 시작하기
            </Link>
          </div>

          {/* Pro tier */}
          <div className="relative rounded-2xl border-2 border-blue-600 bg-white p-7 shadow-md">
            <div className="absolute -top-3 right-5 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 px-3 py-0.5 text-xs font-bold text-white">
              추천
            </div>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50">
                <Crown className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-lg font-bold text-slate-900">Pro</p>
                <p className="text-2xl font-extrabold text-slate-900">
                  &#8361;9,900
                  <span className="text-sm font-medium text-slate-500">
                    /월
                  </span>
                </p>
              </div>
            </div>
            <ul className="mt-6 space-y-3 text-sm text-slate-600">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
                무제한 상권 분석
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
                전체 상권 추천
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
                무제한 사업계획서 + PDF
              </li>
            </ul>
            <Link
              href="/onboarding"
              className="mt-7 block w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-3 text-center text-sm font-semibold text-white shadow-sm transition hover:shadow-md"
            >
              Pro 시작하기
            </Link>
          </div>
        </div>

        <p className="mt-6 text-center text-sm text-slate-400">
          * 베타 기간 전체 무료
        </p>
      </div>
    </section>
  );
}

/* ─────────────────────────────────────────────
   Section 6 -- Tech Stack (바이브랩스 심사용)
   ───────────────────────────────────────────── */
function TechStackSection() {
  return (
    <section className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-4xl px-4 sm:px-6">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl">
            AI 네이티브로 만들었습니다
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-base text-slate-500 sm:text-lg">
            제품도, 개발 과정도 AI-First
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2">
          {/* Product AI */}
          <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-blue-50/60 to-indigo-50/40 p-7">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100 text-blue-600">
              <Cpu className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-lg font-bold text-slate-900">
              제품 내 AI
            </h3>
            <p className="mt-1 text-sm font-semibold text-blue-600">
              Gemini 2.5 Flash
            </p>
            <ul className="mt-4 space-y-2 text-sm text-slate-600">
              <li className="flex items-start gap-2">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
                상권 분석 및 전략 해석
              </li>
              <li className="flex items-start gap-2">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
                사업계획서 자동 생성
              </li>
              <li className="flex items-start gap-2">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
                AI 창업 상담
              </li>
            </ul>
          </div>

          {/* Development AI */}
          <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-slate-100/60 p-7">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-200 text-slate-700">
              <Code2 className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-lg font-bold text-slate-900">
              개발 과정 AI
            </h3>
            <p className="mt-1 text-sm font-semibold text-slate-600">
              Claude Code
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {[
                { value: "58", label: "API 엔드포인트" },
                { value: "21", label: "라우터 모듈" },
                { value: "11,430", label: "코드 줄 수" },
                { value: "2주", label: "개발 기간" },
              ].map((stat, i) => (
                <div key={i} className="rounded-lg bg-white/80 px-3 py-2">
                  <p className="text-lg font-extrabold text-slate-900">
                    {stat.value}
                  </p>
                  <p className="text-[11px] text-slate-500">{stat.label}</p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-slate-400">
              1인 개발 · AI 페어 프로그래밍
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─────────────────────────────────────────────
   Footer
   ───────────────────────────────────────────── */
function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white py-10">
      <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
        <p className="text-sm text-slate-500">
          &copy; 2026 SpotPick &mdash; AI 창업 의사결정 플랫폼
        </p>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">
          데이터 출처: 서울시 우리마을가게 상권분석 · 소상공인시장진흥공단 ·
          공정거래위원회 정보공개서 · KOSIS 통계 · 국세청 사업자등록 · 특허청
          KIPRIS · 중소벤처기업부 지원사업
        </p>
      </div>
    </footer>
  );
}

/* ─────────────────────────────────────────────
   Page
   ───────────────────────────────────────────── */
export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main>
        <HeroSection />
        <PipelineSection />
        <ComparisonSection />
        <EntryPointSection />
        <PricingSection />
        <TechStackSection />
      </main>
      <Footer />
    </div>
  );
}
