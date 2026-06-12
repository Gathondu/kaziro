"use client";

import { ChevronLeft } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo } from "react";
import {
  ONBOARDING_PATHS,
  ONBOARDING_STEPS,
  pathForStep,
  progressForStep,
  type OnboardingStep,
  useOnboardingStore,
} from "@/lib/stores/onboarding";
import { useAuthStore } from "@/lib/stores/auth";

export default function OnboardingLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const loadSession = useAuthStore((state) => state.loadSession);
  const authHydrated = useAuthStore((state) => state.hydrated);
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const hydrateOnboarding = useOnboardingStore((state) => state.hydrate);
  const onboardingHydrated = useOnboardingStore((state) => state.hydrated);

  const currentStep = useMemo(() => stepFromPath(pathname), [pathname]);
  const progress = currentStep ? progressForStep(currentStep) : null;
  const currentIndex = currentStep ? ONBOARDING_STEPS.indexOf(currentStep) : -1;
  const showBack = currentIndex > 0;

  useEffect(() => {
    void loadSession();
    hydrateOnboarding();
  }, [hydrateOnboarding, loadSession]);

  useEffect(() => {
    if (!authHydrated) {
      return;
    }
    if (!user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [authHydrated, pathname, router, user]);

  function goBack(): void {
    if (currentIndex <= 0) {
      return;
    }
    router.push(pathForStep(ONBOARDING_STEPS[currentIndex - 1]));
  }

  if (!authHydrated || !onboardingHydrated || !user || !token) {
    return (
      <main className="grid min-h-screen place-items-center bg-base-200 px-4">
        <span className="loading loading-spinner text-primary" aria-label="Loading" />
      </main>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-base-200">
      <header className="shrink-0 border-b border-base-300 bg-base-100/90 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-xl items-center justify-center px-4 py-3">
          {progress ? (
            <span className="text-xs font-medium tabular-nums text-base-content/70">
              Step {progress.current} of {progress.total}
            </span>
          ) : null}
        </div>
        {progress ? (
          <div className="h-1 w-full bg-base-300" aria-hidden="true">
            <div
              className="h-full bg-primary transition-[width] duration-300 ease-out"
              style={{ width: `${Math.round((progress.current / progress.total) * 100)}%` }}
            />
          </div>
        ) : null}
      </header>
      <main className="flex flex-1 flex-col items-stretch px-4 py-10 sm:items-center sm:py-16">
        <div className="w-full max-w-xl sm:mx-auto">
          {showBack ? (
            <button
              className="btn btn-ghost btn-sm mb-4 -ml-2 gap-1 px-2 font-normal text-base-content/80 hover:text-base-content"
              onClick={goBack}
              type="button"
            >
              <ChevronLeft className="size-4 shrink-0" aria-hidden="true" />
              Back
            </button>
          ) : null}
          {children}
        </div>
      </main>
    </div>
  );
}

function stepFromPath(pathname: string): OnboardingStep | null {
  const entry = Object.entries(ONBOARDING_PATHS).find(([, path]) => path === pathname);
  return entry ? (entry[0] as OnboardingStep) : null;
}
