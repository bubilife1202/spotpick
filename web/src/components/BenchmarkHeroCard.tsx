import { ExternalLink, MapPin, MessageSquare, Star, Store, Users } from "lucide-react";

interface BenchmarkHeroCardProps {
  benchmarkStore: {
    name: string;
    category: string;
    subCategory?: string;
    address: string;
    placeUrl?: string;
    rating?: number;
    reviewCount?: number;
  };
  topDistrict: {
    district_name: string;
    scorecard_total: number;
    store_count: number;
    survival_rate: number;
    foot_traffic_total: number;
    estimated_rent?: number;
  };
  similarityScore?: number;
}

function formatTraffic(value: number): string {
  if (value >= 10_000) return `${Math.round(value / 10_000).toLocaleString()}만`;
  return value.toLocaleString();
}

function getCompetitionLevel(storeCount: number): string {
  if (storeCount >= 80) return "높음";
  if (storeCount >= 40) return "보통";
  return "낮음";
}

function getRentLevel(estimatedRent?: number): string {
  if (!estimatedRent || estimatedRent <= 0) return "데이터 없음";
  if (estimatedRent >= 3_500_000) return "높음";
  if (estimatedRent >= 2_000_000) return "보통";
  return "낮음";
}

function getKeyAdvantage(score: number, survivalRate: number, storeCount: number): string {
  if (score >= 75) return "AI 종합 점수가 높아 초기 리스크가 낮습니다";
  if (survivalRate >= 0.7) return "동종 업종 생존율이 높아 운영 안정성이 좋습니다";
  if (storeCount >= 50) return "점포 밀집 지역으로 검증된 수요가 확인됩니다";
  return "균형 잡힌 지표로 테스트 진입에 유리합니다";
}

export function BenchmarkHeroCard({ benchmarkStore, topDistrict, similarityScore }: BenchmarkHeroCardProps) {
  const competitionLevel = getCompetitionLevel(topDistrict.store_count);
  const rentLevel = getRentLevel(topDistrict.estimated_rent);
  const keyAdvantage = getKeyAdvantage(
    topDistrict.scorecard_total,
    topDistrict.survival_rate,
    topDistrict.store_count,
  );

  return (
    <section className="overflow-hidden rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50 p-5 shadow-lg sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-2">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-blue-700">Benchmark Snapshot</p>
        {similarityScore != null && (
          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-bold text-amber-800">
            유사도 {similarityScore}%
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 items-stretch gap-3 md:grid-cols-[1fr_auto_1fr] md:gap-4">
        <article className="rounded-xl border border-blue-100 bg-white/85 p-4">
          <div className="mb-3 flex items-center gap-2 text-blue-700">
            <Store className="h-4 w-4" />
            <p className="text-xs font-bold uppercase tracking-wider">벤치마크 매장</p>
          </div>
          <p className="text-base font-extrabold text-slate-900">{benchmarkStore.name}</p>
          <p className="mt-1 text-xs font-medium text-slate-600">
            {benchmarkStore.subCategory || benchmarkStore.category}
          </p>
          <div className="mt-2 flex items-start gap-1.5 text-xs text-slate-500">
            <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span>{benchmarkStore.address}</span>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {benchmarkStore.rating != null && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-700">
                <Star className="h-3 w-3" />
                평점 {benchmarkStore.rating.toFixed(1)}
              </span>
            )}
            {benchmarkStore.reviewCount != null && (
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-700">
                <MessageSquare className="h-3 w-3" />
                리뷰 {benchmarkStore.reviewCount.toLocaleString()}개
              </span>
            )}
            {benchmarkStore.placeUrl && (
              <a
                href={benchmarkStore.placeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-1 text-[11px] font-semibold text-blue-700 transition hover:bg-blue-200"
              >
                지도 보기 <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </article>

        <div className="flex items-center justify-center py-1 md:py-0">
          <div className="rounded-full border border-orange-200 bg-orange-100 px-4 py-1.5 text-sm font-black tracking-wider text-orange-700 shadow-sm">
            VS
          </div>
        </div>

        <article className="rounded-xl border border-indigo-100 bg-white/85 p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-indigo-600">추천 상권 #1</p>
          <p className="mt-1 text-base font-extrabold text-slate-900">{topDistrict.district_name}</p>

          <div className="mt-3 grid grid-cols-3 gap-2">
            <div className="rounded-lg bg-indigo-50 p-2 text-center">
              <p className="text-[10px] text-indigo-500">AI 점수</p>
              <p className="text-sm font-extrabold text-indigo-800">{topDistrict.scorecard_total}</p>
            </div>
            <div className="rounded-lg bg-emerald-50 p-2 text-center">
              <p className="text-[10px] text-emerald-500">점포 수</p>
              <p className="text-sm font-extrabold text-emerald-800">{topDistrict.store_count}개</p>
            </div>
            <div className="rounded-lg bg-cyan-50 p-2 text-center">
              <p className="text-[10px] text-cyan-500">생존율</p>
              <p className="text-sm font-extrabold text-cyan-800">{(topDistrict.survival_rate * 100).toFixed(0)}%</p>
            </div>
          </div>

          <p className="mt-3 rounded-lg bg-indigo-50/70 px-3 py-2 text-xs font-medium text-indigo-800">
            핵심 강점: {keyAdvantage}
          </p>
        </article>
      </div>

      <div className="mt-4 rounded-xl border border-blue-100 bg-white/85 p-4">
        <p className="mb-2 text-xs font-bold uppercase tracking-wider text-blue-700">빠른 지표 비교</p>
        <div className="grid grid-cols-[96px_1fr_1fr] gap-2 text-xs sm:grid-cols-[120px_1fr_1fr] sm:text-sm">
          <p className="font-semibold text-slate-500">지표</p>
          <p className="font-semibold text-slate-700">벤치마크 상권</p>
          <p className="font-semibold text-slate-700">추천 상권</p>

          <p className="text-slate-500">경쟁 밀도</p>
          <p className="text-slate-700">실운영 매장 존재</p>
          <p className="font-semibold text-slate-900">{competitionLevel} ({topDistrict.store_count}개)</p>

          <p className="text-slate-500">유동인구</p>
          <p className="text-slate-700">실제 방문 수요 검증</p>
          <p className="inline-flex items-center gap-1 font-semibold text-slate-900">
            <Users className="h-3.5 w-3.5 text-cyan-600" />
            {topDistrict.foot_traffic_total > 0 ? `${formatTraffic(topDistrict.foot_traffic_total)}명` : "데이터 없음"}
          </p>

          <p className="text-slate-500">임대료 수준</p>
          <p className="text-slate-700">운영 가능한 임차권 확보</p>
          <p className="font-semibold text-slate-900">{rentLevel}</p>
        </div>
      </div>
    </section>
  );
}
