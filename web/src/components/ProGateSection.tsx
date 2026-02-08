"use client";

import { type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { isFeatureAvailable, type PremiumFeature } from "@/lib/premium";
import { Crown } from "lucide-react";

interface ProGateSectionProps {
  feature: PremiumFeature;
  children: ReactNode;
  freePreview?: ReactNode;
  className?: string;
}

export function ProGateSection({
  feature,
  children,
  freePreview,
  className,
}: ProGateSectionProps) {
  const available = isFeatureAvailable(feature);

  if (available) {
    return <>{children}</>;
  }

  return (
    <div className={cn("relative", className)}>
      {/* Free preview content (if provided) */}
      {freePreview && <div className="mb-2">{freePreview}</div>}

      {/* Blurred premium content */}
      <div className="relative overflow-hidden rounded-xl">
        <div className="pointer-events-none select-none blur-sm">{children}</div>

        {/* Overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-center rounded-xl bg-white/70 backdrop-blur-[2px]">
          <div className="flex flex-col items-center gap-2 rounded-2xl bg-white px-6 py-4 shadow-lg">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600">
              <Crown className="h-5 w-5 text-white" />
            </div>
            <p className="text-sm font-bold text-slate-900">Pro 전용 기능</p>
            <p className="text-center text-xs text-slate-500">
              4,900원으로 전체 리포트를 확인하세요
            </p>
            <button className="mt-1 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition hover:shadow-md">
              Pro 업그레이드
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
