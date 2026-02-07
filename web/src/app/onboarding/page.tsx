"use client";

import { useRouter } from "next/navigation";
import { Onboarding, OnboardingData } from "@/components/Onboarding";
import {
  ONBOARDING_DONE_KEY,
  ONBOARDING_CONTEXT_KEY,
  rentDefaultsFromOnboarding,
  buildAutoQuery,
} from "@/lib/onboarding-utils";

export default function OnboardingPage() {
  const router = useRouter();

  const completeOnboarding = (data: OnboardingData) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ONBOARDING_DONE_KEY, "1");
      if (data.industryCode) {
        window.localStorage.setItem("builder_curation_industry_code", data.industryCode);
      }
      const { budgetMin, budgetMax } = rentDefaultsFromOnboarding(data.budget);
      window.localStorage.setItem(
        ONBOARDING_CONTEXT_KEY,
        JSON.stringify({
          district: data.district,
          budget_min: budgetMin,
          budget_max: budgetMax,
          cafe_type: data.cafeType,
          target: data.target,
          industry_code: data.industryCode || "CS100010",
        })
      );
      // Store initial query for the chat page to pick up
      window.localStorage.setItem(
        "builder_curation_initial_query",
        buildAutoQuery(data)
      );
    }
    router.push("/chat");
  };

  const handleSkip = () => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ONBOARDING_DONE_KEY, "1");
      window.localStorage.removeItem(ONBOARDING_CONTEXT_KEY);
    }
    router.push("/chat");
  };

  return <Onboarding onComplete={completeOnboarding} onSkip={handleSkip} />;
}
