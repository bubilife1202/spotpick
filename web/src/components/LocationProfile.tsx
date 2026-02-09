"use client";

import { cn } from "@/lib/utils";
import {
  MapPin,
  GraduationCap,
  Car,
  Train,
  Bus,
  Users,
  AlertTriangle,
} from "lucide-react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function LocationProfile({ data, loading, districtName }: { data: any; loading: boolean; districtName?: string }) {
  if (loading) {
    return (
      <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="h-5 w-5 animate-pulse rounded bg-slate-200" />
          <h3 className="text-sm font-bold text-slate-400">입지 분석</h3>
        </div>
        <div className="space-y-3">
          <div className="h-4 w-3/4 animate-pulse rounded bg-slate-200" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-slate-200" />
          <div className="h-20 w-full animate-pulse rounded bg-slate-200" />
        </div>
      </div>
    );
  }

  if (!data) return null;

  const landUse = data.land_use || {};
  const school = data.school_proximity || {};
  const parking = data.parking || {};
  const subway = data.subway || {};
  const bus = data.bus || {};
  const pop = data.living_population || {};

  const headerName = districtName ? `B4. ${districtName} 입지 분석` : "B4. 입지 분석";

  return (
    <div className="h-full rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <MapPin className="h-5 w-5 text-teal-500" />
        <h3 className="text-sm font-bold text-slate-900">{headerName}</h3>
      </div>

      {/* Interpretation */}
      <div className="mb-4 rounded-lg bg-teal-50/50 p-3">
        <p className="text-xs leading-relaxed text-teal-800">
          이 상권의 유동인구, 배후인구, 교통접근성 등을 종합한 입지 정보입니다.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {/* Land Use */}
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
          <div className="mb-1 flex items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5 text-teal-500" />
            <p className="text-[10px] font-bold text-slate-500">용도지역</p>
          </div>
          <p className="text-sm font-semibold text-slate-900">
            {landUse.zone_name || "정보없음"}
          </p>
          <span
            className={cn(
              "mt-1 inline-block rounded-full px-2 py-0.5 text-[10px] font-bold",
              landUse.zone_category === "상업지역"
                ? "bg-emerald-50 text-emerald-700"
                : landUse.zone_category === "주거지역"
                  ? "bg-blue-50 text-blue-700"
                  : "bg-slate-100 text-slate-600",
            )}
          >
            {landUse.zone_category || "기타"}
          </span>
        </div>

        {/* School */}
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
          <div className="mb-1 flex items-center gap-1.5">
            <GraduationCap className="h-3.5 w-3.5 text-amber-500" />
            <p className="text-[10px] font-bold text-slate-500">학교 (200m)</p>
          </div>
          {school.in_restricted_zone ? (
            <div className="flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              <p className="text-sm font-semibold text-amber-700">
                정화구역 {school.count || 0}개교
              </p>
            </div>
          ) : (
            <p className="text-sm font-semibold text-emerald-700">정화구역 해당없음</p>
          )}
          {school.nearby_schools?.slice(0, 2).map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (s: any, i: number) => (
              <p key={i} className="text-[10px] text-slate-500">
                {s.name} ({s.distance_m}m)
              </p>
            ),
          )}
        </div>

        {/* Parking */}
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
          <div className="mb-1 flex items-center gap-1.5">
            <Car className="h-3.5 w-3.5 text-blue-500" />
            <p className="text-[10px] font-bold text-slate-500">공영주차장 (300m)</p>
          </div>
          <p className="text-sm font-semibold text-slate-900">
            {parking.total || 0}개소
          </p>
          {parking.parking_lots?.slice(0, 2).map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (p: any, i: number) => (
              <p key={i} className="text-[10px] text-slate-500">
                {p.name} ({p.distance_m}m, {p.capacity}면)
              </p>
            ),
          )}
        </div>

        {/* Subway */}
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
          <div className="mb-1 flex items-center gap-1.5">
            <Train className="h-3.5 w-3.5 text-purple-500" />
            <p className="text-[10px] font-bold text-slate-500">지하철</p>
          </div>
          {subway.station_name ? (
            <>
              <p className="text-sm font-semibold text-slate-900">
                {subway.station_name}역
              </p>
              <p className="text-[10px] text-slate-500">
                {subway.distance_m || 0}m / 일 {(subway.daily_passengers || 0).toLocaleString()}명
              </p>
            </>
          ) : (
            <p className="text-sm text-slate-500">정보없음</p>
          )}
        </div>

        {/* Bus */}
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
          <div className="mb-1 flex items-center gap-1.5">
            <Bus className="h-3.5 w-3.5 text-green-500" />
            <p className="text-[10px] font-bold text-slate-500">버스</p>
          </div>
          <p className="text-sm font-semibold text-slate-900">
            일 평균 {(bus.avg_daily_passengers || 0).toLocaleString()}명
          </p>
          <p className="text-[10px] text-slate-400">하루 평균 이 상권을 이용하는 버스 승객 수</p>
        </div>

        {/* Living Population */}
        <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3">
          <div className="mb-1 flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5 text-rose-500" />
            <p className="text-[10px] font-bold text-slate-500">생활인구 (배후인구)</p>
          </div>
          <p className="text-sm font-semibold text-slate-900">
            {(pop.total || 0).toLocaleString()}명
          </p>
          <p className="text-[10px] text-slate-400">이 상권 반경 내 거주하는 주민 수</p>
          {pop.male_ratio != null && (
            <p className="text-[10px] text-slate-500">
              남 {((pop.male_ratio || 0) * 100).toFixed(0)}% / 여{" "}
              {((pop.female_ratio || 0) * 100).toFixed(0)}%
            </p>
          )}
        </div>
      </div>

      <p className="mt-4 text-[10px] text-slate-400">출처: 서울시 생활인구 + 대중교통 데이터</p>
    </div>
  );
}
