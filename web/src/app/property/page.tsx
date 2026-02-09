"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { AnalyzeStepper } from "@/components/AnalyzeStepper";
import {
  MapPin,
  Loader2,
  Building2,
  Phone,
  ExternalLink,
  Sparkles,
  ArrowRight,
  Banknote,
  Navigation,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

interface Listing {
  name: string;
  address: string;
  category: string;
  phone: string;
  link: string;
  source: string;
}

interface Realtor {
  name: string;
  address: string;
  phone: string;
  distance: number;
  place_url: string;
}

function formatWon(value: number): string {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}억원`;
  if (value >= 10_000) return `${Math.round(value / 10_000).toLocaleString()}만원`;
  return `${value.toLocaleString()}원`;
}

function PropertyContent() {
  const searchParams = useSearchParams();
  const districtCode = searchParams?.get("district_code") || "";
  const industryCode = searchParams?.get("industry_code") || "CS100010";

  const [listings, setListings] = useState<Listing[]>([]);
  const [realtors, setRealtors] = useState<Realtor[]>([]);
  const [districtName, setDistrictName] = useState("");
  const [estimatedRent, setEstimatedRent] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!districtCode) {
      setError("상권 코드가 필요합니다.");
      setLoading(false);
      return;
    }
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(
          `${API_BASE}/property/listings?district_code=${districtCode}&industry_code=${industryCode}`,
        );
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        const data = await res.json();
        setListings(data.listings || []);
        setRealtors(data.realtors || []);
        setDistrictName(data.district_name || "");
        setEstimatedRent(data.estimated_rent || 0);
      } catch {
        setError("매물 정보를 불러올 수 없습니다.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [districtCode, industryCode]);

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
            href={`/analyze/report?industry_code=${industryCode}`}
            className="text-sm font-medium text-slate-500 hover:text-slate-700"
          >
            리포트로 돌아가기
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-20 pt-8 sm:px-6">
        <AnalyzeStepper currentStep={3} className="mb-8" />

        <div className="mb-8 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
            <Building2 className="h-3.5 w-3.5" />
            Step 3
          </span>
          <h1 className="mt-3 text-2xl font-extrabold text-slate-900 sm:text-3xl">
            매물 탐색
          </h1>
          {districtName && (
            <p className="mt-1 text-sm text-slate-500">
              {districtName} 인근 상가 매물 및 부동산 중개소
            </p>
          )}
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
            <p className="mt-3 text-sm text-slate-500">매물 정보를 검색하고 있습니다...</p>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-center">
            <p className="text-sm text-rose-600">{error}</p>
            <Link
              href="/analyze"
              className="mt-3 inline-block text-sm font-semibold text-blue-600"
            >
              분석 페이지로 이동
            </Link>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Estimated rent card */}
            {estimatedRent > 0 && (
              <div className="rounded-2xl border border-blue-100 bg-blue-50/50 p-5">
                <div className="flex items-center gap-2">
                  <Banknote className="h-5 w-5 text-blue-500" />
                  <h3 className="text-sm font-bold text-blue-900">SpotPick 추정 임대료</h3>
                </div>
                <p className="mt-2 text-2xl font-extrabold text-blue-700">
                  {formatWon(estimatedRent)}
                  <span className="text-sm font-medium text-blue-400">/월</span>
                </p>
                <p className="mt-1 text-[10px] text-blue-500">
                  KREI 외식업체경영실태조사 + 상권 퍼센타일 기반 추정치
                </p>
              </div>
            )}

            {/* Listings */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6">
              <div className="mb-4 flex items-center gap-2">
                <Building2 className="h-5 w-5 text-emerald-500" />
                <h2 className="text-sm font-bold text-slate-900">
                  상가 매물 · 임대 정보
                </h2>
                <span className="ml-auto rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                  {listings.length}건
                </span>
              </div>

              {listings.length > 0 ? (
                <div className="space-y-3">
                  {listings.map((l, i) => (
                    <div
                      key={i}
                      className="rounded-xl border border-slate-100 bg-slate-50/30 p-4 transition hover:border-slate-200"
                    >
                      <div className="flex items-start justify-between">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-bold text-slate-900">{l.name}</p>
                          <p className="mt-0.5 text-xs text-slate-500">{l.address}</p>
                          {l.category && (
                            <span className="mt-1 inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                              {l.category}
                            </span>
                          )}
                        </div>
                        <div className="flex shrink-0 gap-2">
                          {l.phone && (
                            <a
                              href={`tel:${l.phone}`}
                              className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 transition hover:bg-emerald-100"
                            >
                              <Phone className="h-3.5 w-3.5" />
                            </a>
                          )}
                          {l.link && (
                            <a
                              href={l.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600 transition hover:bg-blue-100"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                            </a>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl bg-slate-50 py-8 text-center">
                  <Building2 className="mx-auto h-8 w-8 text-slate-300" />
                  <p className="mt-2 text-sm text-slate-500">
                    검색된 매물이 없습니다. 아래 부동산 중개소에 직접 문의하세요.
                  </p>
                </div>
              )}
            </div>

            {/* Realtors */}
            {realtors.length > 0 && (
              <div className="rounded-2xl border border-slate-200 bg-white p-6">
                <div className="mb-4 flex items-center gap-2">
                  <Navigation className="h-5 w-5 text-violet-500" />
                  <h2 className="text-sm font-bold text-slate-900">
                    인근 부동산 중개소
                  </h2>
                  <span className="ml-auto rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-bold text-violet-700">
                    {realtors.length}곳
                  </span>
                </div>

                <div className="space-y-2">
                  {realtors.map((r, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/30 p-3"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-slate-900">{r.name}</p>
                        <p className="text-[10px] text-slate-500">
                          {r.address} · {r.distance}m
                        </p>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        {r.phone && (
                          <a
                            href={`tel:${r.phone}`}
                            className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-50 text-violet-600 transition hover:bg-violet-100"
                          >
                            <Phone className="h-3.5 w-3.5" />
                          </a>
                        )}
                        {r.place_url && (
                          <a
                            href={r.place_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600 transition hover:bg-blue-100"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* CTA: Go to cost compare */}
            <div className="flex flex-col items-center gap-3">
              <Link
                href={`/cost-compare?industry_code=${industryCode}&district_code=${districtCode}&monthly_rent=${estimatedRent}`}
                className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-4 text-base font-bold text-white shadow-lg shadow-blue-500/25 transition hover:shadow-xl"
              >
                <Sparkles className="h-5 w-5" />
                비용 비교하기
                <ArrowRight className="h-5 w-5" />
              </Link>
              <p className="text-[10px] text-slate-400">
                프랜차이즈 vs 독립창업 총 비용을 비교해보세요
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function PropertyPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <PropertyContent />
    </Suspense>
  );
}
