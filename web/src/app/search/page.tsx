"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import SearchMode from "@/components/SearchMode";
import { ONBOARDING_CONTEXT_KEY } from "@/lib/onboarding-utils";

export default function SearchPage() {
  const router = useRouter();
  const [initialSearchParams, setInitialSearchParams] = useState<{
    budgetMin: number;
    budgetMax: number;
    district?: string;
  } | undefined>(undefined);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(ONBOARDING_CONTEXT_KEY);
      if (raw) {
        const ctx = JSON.parse(raw);
        setInitialSearchParams({
          budgetMin: ctx.budget_min ?? 2000000,
          budgetMax: ctx.budget_max ?? 5000000,
          district: ctx.district || undefined,
        });
      }
    } catch { /* ignore */ }
    setReady(true);
  }, []);

  if (!ready) return null;

  return (
    <SearchMode
      initialSearchParams={initialSearchParams}
      onSwitchToChat={() => router.push("/chat")}
    />
  );
}
