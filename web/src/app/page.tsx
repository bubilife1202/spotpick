import Link from "next/link";
import {
  MapPin,
  Sparkles,
  ChevronRight,
  Utensils,
  BarChart3,
  FileText,
} from "lucide-react";
import { cn } from "@/lib/utils";

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

        <Link
          href="/analyze"
          className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md"
        >
          시작하기
        </Link>
      </div>
    </header>
  );
}

function HeroSection() {
   const stats = [
     { value: "1,077", label: "서울 전체 상권" },
     { value: "10종", label: "외식업 전 업종" },
     { value: "7대", label: "공공 빅데이터" },
     { value: "3분", label: "AI 진단 완료" },
   ];

  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-slate-50 to-white py-20 sm:py-28">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -right-40 -top-40 h-[500px] w-[500px] rounded-full bg-blue-100/40 blur-3xl" />
        <div className="absolute -left-40 top-40 h-[400px] w-[400px] rounded-full bg-indigo-100/30 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-6xl px-4 text-center sm:px-6">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
          <Sparkles className="h-3.5 w-3.5" />
          AI 창업 의사결정 플랫폼
        </span>

        <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-slate-900 sm:text-5xl lg:text-6xl">
          창업, 감으로 하지 마세요
        </h1>

         <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-slate-600 sm:text-lg">
           서울 <strong className="text-slate-800">1,077개 상권</strong> ·{" "}
           <strong className="text-slate-800">외식업 전 업종</strong> ·{" "}
           <strong className="text-slate-800">7대 공공 빅데이터</strong>
           <br />
           5가지 질문에 답하면, AI가 정직하게 Go/No-Go를 판정합니다
         </p>

        <div className="mt-8 flex items-center justify-center">
          <Link
            href="/analyze"
            className={cn(
              "inline-flex items-center rounded-xl",
              "bg-gradient-to-r from-blue-600 to-indigo-600",
              "px-7 py-3.5 text-base font-semibold text-white",
              "shadow-lg shadow-blue-500/25 transition",
              "hover:shadow-xl hover:shadow-blue-500/30",
            )}
          >
            무료로 시작하기 →
          </Link>
        </div>

        <div className="mt-14 grid grid-cols-2 gap-4 sm:grid-cols-4 sm:gap-6">
          {stats.map((stat) => (
            <div
              key={stat.label}
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

const PIPELINE_STEPS = [
  {
    icon: Utensils,
    title: "입력",
    desc: "5가지 질문, AI 상담",
    href: "/analyze",
  },
  {
    icon: BarChart3,
    title: "AI 리포트",
    desc: "Go/No-Go 정직한 진단",
    href: "/analyze/report",
  },
  {
    icon: FileText,
    title: "액션 플랜",
    desc: "실행 체크리스트",
    href: "/analyze/action",
  },
];

function PipelineSection() {
  return (
    <section className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl">
            3단계로 끝나는 창업 분석
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-base text-slate-500 sm:text-lg">
            업종과 예산만 입력하면, AI가 모든 분석을 한 번에
          </p>
        </div>

        <div className="mt-14 grid grid-cols-1 gap-4 sm:grid-cols-3 lg:gap-6">
          {PIPELINE_STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <Link
                key={step.title}
                href={step.href}
                className="relative flex flex-col items-center gap-3 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm text-center hover:border-slate-300 transition-colors"
              >
                <div className="absolute -top-2.5 left-1/2 flex h-6 w-6 -translate-x-1/2 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-xs font-bold text-white">
                  {i + 1}
                </div>

                <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
                  <Icon className="h-7 w-7" />
                </div>

                <div>
                  <p className="text-base font-bold text-slate-900">{step.title}</p>
                  <p className="mt-0.5 text-sm text-slate-500">{step.desc}</p>
                </div>

                {i < PIPELINE_STEPS.length - 1 && (
                  <ChevronRight className="absolute -right-5 top-1/2 hidden h-5 w-5 -translate-y-1/2 text-slate-300 sm:block" />
                )}
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function FinalCtaBanner() {
  return (
    <section className="bg-gradient-to-r from-blue-600 to-indigo-600 py-16 sm:py-20">
      <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
        <Sparkles className="mx-auto h-8 w-8 text-white/80" />
        <h2 className="mt-4 text-3xl font-extrabold text-white sm:text-4xl">
          베타 기간 전체 무료
        </h2>
         <p className="mx-auto mt-3 max-w-xl text-base text-blue-100 sm:text-lg">
           AI 진단 · Go/No-Go 판정 · 실행 체크리스트까지
           <br />
           지금 바로 무료로 시작해보세요
         </p>
        <Link
          href="/analyze"
          className="mt-8 inline-flex items-center rounded-xl bg-white px-7 py-3.5 text-base font-semibold text-blue-700 shadow-lg transition hover:bg-blue-50 hover:shadow-xl"
        >
          무료로 시작하기 →
        </Link>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white py-10">
      <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
        <p className="text-sm text-slate-500">&copy; 2026 SpotPick</p>
        <p className="mt-2 text-xs leading-relaxed text-slate-400">
          데이터 출처: 서울시 우리마을가게 상권분석 · 소상공인시장진흥공단 · 공정거래위원회 정보공개서
        </p>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main>
        <HeroSection />
        <PipelineSection />
        <FinalCtaBanner />
      </main>
      <Footer />
    </div>
  );
}
