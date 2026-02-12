"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

type Competitor = {
  name: string;
  address: string;
  distance: number;
  category: string;
};

type NearbyCompetitionResponse = {
  keyword: string;
  count: number;
  competitors: Competitor[];
};

type CompetitorCountCardProps = {
  keyword: string;
  x: string;
  y: string;
  districtName: string;
};

function getCountBadgeClass(count: number): string {
  if (count <= 2) return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (count <= 5) return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-rose-200 bg-rose-50 text-rose-700";
}

export function CompetitorCountCard({ keyword, x, y, districtName }: CompetitorCountCardProps) {
  const [data, setData] = useState<NearbyCompetitionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const requestUrl = useMemo(() => {
    const params = new URLSearchParams({
      keyword,
      x,
      y,
      radius: "1000",
    });
    return `${API_BASE}/competition/nearby?${params.toString()}`;
  }, [keyword, x, y]);

  useEffect(() => {
    if (!keyword || !x || !y) return;

    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(requestUrl);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as NearbyCompetitionResponse;
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "unknown error");
          setData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();

    return () => {
      cancelled = true;
    };
  }, [keyword, x, y, requestUrl]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <Users className="h-4 w-4 text-slate-700" />
        <p className="text-sm font-bold text-slate-900">B3-1. 세부 업종 경쟁 카운트</p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          주변 경쟁 매장을 찾는 중...
        </div>
      )}

      {!loading && error && (
        <p className="text-sm text-slate-500">
          실시간 경쟁 매장을 불러오지 못했습니다.
        </p>
      )}

      {!loading && !error && data && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-slate-800">
              이 상권({districtName})에 {data.keyword} {data.count}개
            </p>
            <span
              className={cn(
                "rounded-full border px-2 py-0.5 text-xs font-bold",
                getCountBadgeClass(data.count),
              )}
            >
              {data.count <= 2 ? "경쟁 낮음" : data.count <= 5 ? "경쟁 보통" : "경쟁 높음"}
            </span>
          </div>

          {data.count === 0 ? (
            <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              이 상권 반경 1km 내 {data.keyword}가 없습니다 - 경쟁이 적은 블루오션!
            </p>
          ) : (
            <>
              <p className="text-sm text-slate-600">
                {data.competitors.slice(0, 2).map((c) => c.name).join(", ")}
                {data.count > 2 ? ` 외 ${data.count - 2}곳` : ""}
              </p>
              <ul className="space-y-2">
                {data.competitors.slice(0, 5).map((competitor) => (
                  <li
                    key={`${competitor.name}-${competitor.address}-${competitor.distance}`}
                    className="rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-800">{competitor.name}</p>
                      <span className="text-xs font-medium text-slate-500">{competitor.distance}m</span>
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">{competitor.address}</p>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
