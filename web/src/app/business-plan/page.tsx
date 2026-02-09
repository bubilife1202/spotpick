"use client";

import { useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

/**
 * Legacy /business-plan page — redirects to /analyze/action
 * preserving all query params (industry_code, district_code, budget, area_pyeong).
 */
function RedirectInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const params = new URLSearchParams();
    const industryCode = searchParams?.get("industry_code");
    const districtCode = searchParams?.get("district_code");
    const budget = searchParams?.get("budget");
    const areaPyeong = searchParams?.get("area_pyeong");

    if (industryCode) params.set("industry_code", industryCode);
    if (districtCode) params.set("district_code", districtCode);
    if (budget) params.set("budget", budget);
    if (areaPyeong) params.set("area_pyeong", areaPyeong);

    const qs = params.toString();
    router.replace(`/analyze/action${qs ? `?${qs}` : ""}`);
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
    </div>
  );
}

export default function BusinessPlanPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <RedirectInner />
    </Suspense>
  );
}
