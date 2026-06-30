"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { pathForStep, useOnboardingStore } from "@/lib/stores/onboarding";

export default function OnboardingPage() {
  const router = useRouter();
  const draft = useOnboardingStore((state) => state.draft);
  const hydrated = useOnboardingStore((state) => state.hydrated);

  useEffect(() => {
    if (hydrated) {
      router.replace(pathForStep(draft.step));
    }
  }, [draft.step, hydrated, router]);

  return (
    <span
      className="loading loading-spinner text-primary"
      aria-label="Loading"
    />
  );
}
