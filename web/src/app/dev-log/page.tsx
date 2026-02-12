import Link from "next/link";
import {
  MapPin,
  Sparkles,
  Code2,
  Database,
  Cpu,
  BarChart3,
  FileText,
  MessageSquare,
  GitBranch,
  Rocket,
} from "lucide-react";

const STATS = [
  { value: "200+", label: "총 커밋" },
  { value: "25+", label: "API 엔드포인트" },
  { value: "15+", label: "페이지" },
  { value: "7개", label: "데이터셋" },
];

const AI_FEATURES = [
  { icon: BarChart3, title: "상권 분석", desc: "1,077개 상권 데이터 기반 종합 점수 산출" },
  { icon: FileText, title: "사업계획서 생성", desc: "맞춤형 사업계획서 자동 작성" },
  { icon: Sparkles, title: "AI 브리핑", desc: "실시간 상권 진단 요약" },
  { icon: GitBranch, title: "상권 비교 판정", desc: "A vs B 상권 AI 판정" },
  { icon: MessageSquare, title: "AI 상담", desc: "대화형 창업 코칭" },
];

const TECH_STACK: { category: string; items: string[] }[] = [
  { category: "Frontend", items: ["Next.js 14", "TypeScript", "Tailwind CSS", "Zustand", "MapLibre GL"] },
  { category: "Backend", items: ["FastAPI", "Python 3.11", "Pandas"] },
  { category: "AI", items: ["Google Gemini 2.5 Flash"] },
  { category: "Data", items: ["서울시 공공데이터 7종", "1,077개 상권"] },
];

const VERSIONS = [
  { tag: "v0.1.0", desc: "MVP 출시 (상권 분석 기본 기능)" },
  { tag: "v0.5.0", desc: "10개 업종 지원 확대" },
  { tag: "v0.9.0", desc: "벤치마크 + 경쟁 분석 추가" },
  { tag: "v1.0.0", desc: "풀 스택 완성 (비교, 타임라인, 개발기)" },
];

export default function DevLogPage() {
  return (
    <div className="min-h-screen bg-white">
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
            className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md"
          >
            시작하기
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 sm:px-6">
        {/* Hero */}
        <section className="py-12 sm:py-16">
          <div className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600">
              <Rocket className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
              개발 현황
            </h1>
          </div>
          <p className="mt-3 text-base text-slate-500">
            1인 개발 · AI 네이티브 · 14일 완성
          </p>

          <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
            {STATS.map((s) => (
              <div
                key={s.label}
                className="rounded-2xl border border-slate-200/80 bg-white px-4 py-5 shadow-sm"
              >
                <p className="text-2xl font-extrabold text-slate-900 sm:text-3xl">{s.value}</p>
                <p className="mt-1 text-xs font-medium text-slate-500 sm:text-sm">{s.label}</p>
              </div>
            ))}
          </div>
        </section>

        {/* AI in Product */}
        <section className="border-t border-slate-100 py-12 sm:py-16">
          <div className="flex items-center gap-3">
            <Cpu className="h-5 w-5 text-blue-600" />
            <h2 className="text-xl font-extrabold text-slate-900 sm:text-2xl">제품 속 AI 활용</h2>
            <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700">
              Gemini 2.5 Flash
            </span>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {AI_FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <div
                  key={f.title}
                  className="flex items-start gap-3 rounded-xl border border-slate-200/80 bg-white p-4 shadow-sm"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                    <Icon className="h-4.5 w-4.5" />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-slate-900">{f.title}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{f.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* AI in Development */}
        <section className="border-t border-slate-100 py-12 sm:py-16">
          <div className="flex items-center gap-3">
            <Code2 className="h-5 w-5 text-indigo-600" />
            <h2 className="text-xl font-extrabold text-slate-900 sm:text-2xl">개발에 AI 활용</h2>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            Claude Code로 전체 프론트엔드/백엔드 개발
          </p>
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-500">
            <span><strong className="text-slate-800">200+</strong> 커밋</span>
            <span><strong className="text-slate-800">14일</strong> 개발 기간</span>
            <span><strong className="text-slate-800">1인</strong> 풀스택</span>
          </div>
        </section>

        {/* Tech Stack */}
        <section className="border-t border-slate-100 py-12 sm:py-16">
          <div className="flex items-center gap-3">
            <Database className="h-5 w-5 text-emerald-600" />
            <h2 className="text-xl font-extrabold text-slate-900 sm:text-2xl">기술 스택</h2>
          </div>

          <div className="mt-8 space-y-5">
            {TECH_STACK.map((group) => (
              <div key={group.category}>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  {group.category}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {group.items.map((item) => (
                    <span
                      key={item}
                      className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Version History */}
        <section className="border-t border-slate-100 py-12 sm:py-16">
          <h2 className="text-xl font-extrabold text-slate-900 sm:text-2xl">버전 히스토리</h2>

          <ul className="mt-8 space-y-4">
            {VERSIONS.map((v) => (
              <li key={v.tag} className="flex items-baseline gap-4">
                <span className="shrink-0 rounded-md bg-slate-900 px-2.5 py-1 text-xs font-bold text-white">
                  {v.tag}
                </span>
                <span className="text-sm text-slate-600">{v.desc}</span>
              </li>
            ))}
          </ul>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-10">
        <p className="text-center text-sm text-slate-500">&copy; 2026 SpotPick</p>
      </footer>
    </div>
  );
}