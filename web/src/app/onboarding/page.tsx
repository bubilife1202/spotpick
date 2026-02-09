"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Onboarding, OnboardingData } from "@/components/Onboarding";
import {
  ONBOARDING_DONE_KEY,
  ONBOARDING_CONTEXT_KEY,
} from "@/lib/onboarding-utils";
import { useJourneyStore } from "@/lib/journey-store";

export default function OnboardingPage() {
  const router = useRouter();

  // Redirect to new /analyze flow
  useEffect(() => {
    router.replace("/analyze");
  }, [router]);

  const completeOnboarding = (data: OnboardingData) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ONBOARDING_DONE_KEY, "true");
      if (data.industryCode) {
        window.localStorage.setItem("builder_curation_industry_code", data.industryCode);
      }
      // Save budget range in 만원 units
      window.localStorage.setItem("builder_curation_budget_min", String(data.budgetMin));
      window.localStorage.setItem("builder_curation_budget_max", String(data.budgetMax));
      // Legacy rent keys (cleared)
      window.localStorage.removeItem("builder_curation_rent_min");
      window.localStorage.removeItem("builder_curation_rent_max");
      // Save districts as comma-separated
      window.localStorage.setItem("builder_curation_districts", data.districts.join(","));
      window.localStorage.setItem(
        ONBOARDING_CONTEXT_KEY,
        JSON.stringify({
          districts: data.districts,
          budget_min: data.budgetMin,
          budget_max: data.budgetMax,
          industry_code: data.industryCode || "CS100010",
        })
      );
    }
    // Sync with journey store
    const store = useJourneyStore.getState();
    if (data.industryCode) store.setIndustry(data.industryCode);
    store.setBudget(data.budgetMax || data.budgetMin || 5000);
    store.setDistricts(data.districts);
    store.setStep(2);
    router.push(store.goToFranchise());
  };

  const handleSkip = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ONBOARDING_DONE_KEY, "true");
      window.localStorage.removeItem(ONBOARDING_CONTEXT_KEY);
    }
    useJourneyStore.getState().setStep(3);
    router.push("/results");
  };

  return <Onboarding onComplete={completeOnboarding} onSkip={handleSkip} />;
}
