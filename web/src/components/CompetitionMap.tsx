"use client";

import { Store, MapPin } from "lucide-react";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function CompetitionMap({ data, loading }: { data: any; loading: boolean }) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <div className="mb-4 flex items-center gap-2">
          <div className="h-5 w-5 animate-pulse rounded bg-slate-200" />
          <h3 className="text-sm font-bold text-slate-400">LOCALDATA 경쟁 지도</h3>
        </div>
        <div className="h-32 w-full animate-pulse rounded bg-slate-200" />
      </div>
    );
  }

  if (!data) return null;

  const stores = data.stores || [];
  const typeDistribution = data.type_distribution || {};
  const totalNearby = data.total_nearby || 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6">
      <div className="mb-4 flex items-center gap-2">
        <Store className="h-5 w-5 text-violet-500" />
        <h3 className="text-sm font-bold text-slate-900">LOCALDATA 경쟁 현황</h3>
        <span className="rounded-full bg-violet-50 px-2 py-0.5 text-[10px] font-bold text-violet-700">
          반경 500m
        </span>
      </div>

      {/* Type distribution */}
      {Object.keys(typeDistribution).length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-[10px] font-semibold text-slate-400">업종 분포 (총 {totalNearby}개)</p>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(typeDistribution)
              .slice(0, 8)
              .map(([type, count]) => (
                <span
                  key={type}
                  className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium text-slate-600"
                >
                  {type} <span className="font-bold">{String(count)}</span>
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Store list */}
      {stores.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-semibold text-slate-400">주변 점포</p>
          {stores.slice(0, 8).map(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (s: any, i: number) => (
              <div
                key={i}
                className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50/50 px-3 py-1.5"
              >
                <div className="flex items-center gap-2">
                  <MapPin className="h-3 w-3 text-slate-400" />
                  <div>
                    <p className="text-xs font-medium text-slate-900">{s.name}</p>
                    <p className="text-[10px] text-slate-400">{s.type}</p>
                  </div>
                </div>
                <span className="text-[10px] font-medium text-slate-500">
                  {s.distance_m}m
                </span>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
}
