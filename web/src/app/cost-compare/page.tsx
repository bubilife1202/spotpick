"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  MapPin,
  Loader2,
  Sparkles,
  ArrowRight,
  Building2,
  Store,
  Banknote,
  FileText,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

function formatWon(value: number): string {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}억원`;
  if (value >= 10_000) return `${Math.round(value / 10_000).toLocaleString()}만원`;
  return `${value.toLocaleString()}원`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CostBar({ label, value, maxValue, color }: { label: string; value: number; maxValue: number; color: string }) {
  const pct = maxValue > 0 ? (value / maxValue) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 text-xs font-medium text-slate-600">{label}</span>
      <div className="flex-1">
        <div className="h-5 overflow-hidden rounded bg-slate-50">
          <div
            className={cn("h-full rounded transition-all duration-500", color)}
            style={{ width: `${Math.min(100, pct)}%` }}
          />
        </div>
      </div>
      <span className="w-20 text-right text-xs font-bold text-slate-700">
        {formatWon(value)}
      </span>
    </div>
  );
}

function CostCompareContent() {
  const searchParams = useSearchParams();
  const industryCode = searchParams?.get("industry_code") || "CS100010";
  const districtCode = searchParams?.get("district_code") || "";
  const monthlyRent = Number(searchParams?.get("monthly_rent")) || 0;
  const budgetMax = Number(searchParams?.get("budget_max")) || 0;

  const [areaPyeong, setAreaPyeong] = useState(15);
  const [deposit, setDeposit] = useState(monthlyRent * 10);
  const [rent, setRent] = useState(monthlyRent);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCompare = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        industry_code: industryCode,
        monthly_rent: String(rent),
        deposit: String(deposit),
        area_pyeong: String(areaPyeong),
      });
      const res = await fetch(`${API_BASE}/property/cost-compare?${params}`);
      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch {
      setError("비용 비교에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCompare();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRecalculate = () => {
    fetchCompare();
  };

  const indTotal = result?.independent?.total_initial_cost || 0;
  const franTotal = result?.franchise?.total_initial_cost || 0;
  const maxTotal = Math.max(indTotal, franTotal) || 1;

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600">
              <MapPin className="h-4 w-4 text-white" />
            </div>
            <span className="text-lg font-bold text-slate-900">SpotPick</span>
          </Link>
          <Link
            href={`/property?district_code=${districtCode}&industry_code=${industryCode}`}
            className="text-sm font-medium text-slate-500 hover:text-slate-700"
          >
            매물로 돌아가기
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-20 pt-8 sm:px-6">
        <div className="mb-8 text-center">
          <h1 className="mt-3 text-2xl font-extrabold text-slate-900 sm:text-3xl">
            프랜차이즈 vs 독립창업
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            총 투자금과 월 고정비를 비교하고 AI 추천을 확인하세요
          </p>
        </div>

        {/* Input controls */}
        <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-bold text-slate-900">조건 설정</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-500">면적 (평)</label>
              <input
                type="number"
                value={areaPyeong}
                onChange={(e) => setAreaPyeong(Number(e.target.value) || 15)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                min={5}
                max={100}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-500">보증금 (원)</label>
              <input
                type="number"
                value={deposit}
                onChange={(e) => setDeposit(Number(e.target.value) || 0)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-500">월 임대료 (원)</label>
              <input
                type="number"
                value={rent}
                onChange={(e) => setRent(Number(e.target.value) || 0)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <button
            onClick={handleRecalculate}
            disabled={loading}
            className="mt-4 w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-2.5 text-sm font-semibold text-white transition hover:shadow-md disabled:opacity-50"
          >
            {loading ? "계산 중..." : "다시 계산하기"}
          </button>
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-rose-200 bg-rose-50 p-4 text-center text-sm text-rose-600">
            {error}
          </div>
        )}

        {result && !loading && (
          <div className="space-y-6">
            {/* Total comparison header */}
            <div className="grid grid-cols-2 gap-4">
              <div className={cn(
                "rounded-2xl border-2 p-5 text-center",
                result.cheaper === "independent"
                  ? "border-emerald-300 bg-emerald-50/50"
                  : "border-slate-200 bg-white",
              )}>
                <Store className="mx-auto h-6 w-6 text-emerald-500" />
                <p className="mt-2 text-xs font-semibold text-slate-500">독립창업</p>
                <p className="mt-1 text-xl font-extrabold text-slate-900">
                  {formatWon(indTotal)}
                </p>
                {result.cheaper === "independent" && (
                  <span className="mt-1 inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                    저렴
                  </span>
                )}
              </div>
              <div className={cn(
                "rounded-2xl border-2 p-5 text-center",
                result.cheaper === "franchise"
                  ? "border-blue-300 bg-blue-50/50"
                  : "border-slate-200 bg-white",
              )}>
                <Building2 className="mx-auto h-6 w-6 text-blue-500" />
                <p className="mt-2 text-xs font-semibold text-slate-500">프랜차이즈</p>
                <p className="mt-1 text-xl font-extrabold text-slate-900">
                  {formatWon(franTotal)}
                </p>
                {result.cheaper === "franchise" && (
                  <span className="mt-1 inline-block rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-bold text-blue-700">
                    저렴
                  </span>
                )}
              </div>
            </div>

            {/* Difference banner */}
            <div className="rounded-xl bg-slate-100 p-3 text-center">
              <p className="text-xs text-slate-500">차액</p>
              <p className="text-lg font-extrabold text-slate-900">
                {formatWon(Math.abs(result.difference))}
              </p>
              <p className="text-[10px] text-slate-400">
                {result.cheaper === "independent" ? "독립창업" : "프랜차이즈"}이 저렴
              </p>
            </div>

            {/* Independent breakdown */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <div className="mb-4 flex items-center gap-2">
                <Store className="h-5 w-5 text-emerald-500" />
                <h3 className="text-sm font-bold text-slate-900">독립창업 비용 구조</h3>
              </div>
              <div className="space-y-2">
                <CostBar label="인테리어" value={result.independent.breakdown.interior} maxValue={maxTotal} color="bg-emerald-400" />
                <CostBar label="장비" value={result.independent.breakdown.equipment} maxValue={maxTotal} color="bg-emerald-500" />
                <CostBar label="초도물량" value={result.independent.breakdown.initial_inventory} maxValue={maxTotal} color="bg-emerald-300" />
                <CostBar label="간판" value={result.independent.breakdown.signage} maxValue={maxTotal} color="bg-emerald-200" />
                <CostBar label="보증금" value={result.independent.breakdown.deposit} maxValue={maxTotal} color="bg-slate-400" />
                <CostBar label="기타" value={result.independent.breakdown.misc} maxValue={maxTotal} color="bg-slate-300" />
              </div>

              {/* Equipment detail */}
              {result.independent.breakdown.equipment_detail?.length > 0 && (
                <div className="mt-4 rounded-xl bg-emerald-50/50 p-3">
                  <p className="mb-1 text-[10px] font-bold text-emerald-700">장비 상세</p>
                  <div className="space-y-0.5">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {result.independent.breakdown.equipment_detail.map((e: any, i: number) => (
                      <div key={i} className="flex justify-between text-[11px]">
                        <span className="text-emerald-800">{e.name}</span>
                        <span className="font-semibold text-emerald-900">{formatWon(e.cost)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Franchise breakdown */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <div className="mb-4 flex items-center gap-2">
                <Building2 className="h-5 w-5 text-blue-500" />
                <h3 className="text-sm font-bold text-slate-900">프랜차이즈 비용 구조</h3>
                <span className="ml-auto text-[10px] text-slate-400">공정거래위원회 데이터</span>
              </div>
              <div className="space-y-2">
                <CostBar label="가맹금" value={result.franchise.breakdown.franchise_fee} maxValue={maxTotal} color="bg-blue-500" />
                <CostBar label="교육비" value={result.franchise.breakdown.education_fee} maxValue={maxTotal} color="bg-blue-400" />
                <CostBar label="기타가입비" value={result.franchise.breakdown.other_fee} maxValue={maxTotal} color="bg-blue-300" />
                <CostBar label="인테리어" value={result.franchise.breakdown.interior} maxValue={maxTotal} color="bg-indigo-400" />
                <CostBar label="보증금" value={result.franchise.breakdown.deposit} maxValue={maxTotal} color="bg-slate-400" />
              </div>
            </div>

            {/* Monthly fixed cost */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-slate-200 bg-white p-4 text-center">
                <Banknote className="mx-auto h-5 w-5 text-emerald-500" />
                <p className="mt-1 text-[10px] text-slate-400">독립 월고정비</p>
                <p className="text-lg font-extrabold text-slate-900">
                  {formatWon(result.independent.monthly_fixed_cost)}
                </p>
                <p className="text-[10px] text-slate-400">로열티 없음</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4 text-center">
                <Banknote className="mx-auto h-5 w-5 text-blue-500" />
                <p className="mt-1 text-[10px] text-slate-400">프랜차이즈 월고정비</p>
                <p className="text-lg font-extrabold text-slate-900">
                  {formatWon(result.franchise.monthly_fixed_cost)}
                </p>
                <p className="text-[10px] text-slate-400">+ 로열티 별도</p>
              </div>
            </div>

            {/* AI Verdict */}
            {result.verdict && (
              <div className="rounded-2xl border border-blue-100 bg-blue-50/50 p-5">
                <div className="mb-2 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-blue-500" />
                  <h3 className="text-sm font-bold text-blue-900">AI 종합 추천</h3>
                </div>
                <p className="text-sm leading-relaxed text-blue-900/80">
                  {result.verdict}
                </p>
              </div>
            )}

            {/* CTA: Go to action plan */}
            <div className="flex flex-col items-center gap-3">
              <Link
                href={`/analyze/action?industry_code=${industryCode}&district_code=${districtCode}&budget_max=${budgetMax}`}
                className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-4 text-base font-bold text-white shadow-lg shadow-blue-500/25 transition hover:shadow-xl"
              >
                <FileText className="h-5 w-5" />
                다음 단계: AI 사업계획서 만들기
                <ArrowRight className="h-5 w-5" />
              </Link>
              <p className="text-[10px] text-slate-400">
                위 비교 결과를 포함한 AI 사업계획서를 자동으로 생성합니다
              </p>
            </div>
          </div>
        )}

        {loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
            <p className="mt-3 text-sm text-slate-500">비용을 비교하고 있습니다...</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default function CostComparePage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <CostCompareContent />
    </Suspense>
  );
}
