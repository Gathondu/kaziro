"use client";

import { create } from "zustand";

export type OnboardingStep =
  | "about-you"
  | "summary"
  | "domain"
  | "experience"
  | "skills"
  | "cv"
  | "config";

export type OnboardingProfileDraft = {
  full_name?: string;
  professional_summary?: string;
  domain?: string;
  experience_years?: number | null;
  skillsText?: string;
};

export type OnboardingDraft = {
  step: OnboardingStep;
  profile: OnboardingProfileDraft;
};

type OnboardingState = {
  hydrated: boolean;
  draft: OnboardingDraft;
  cvFile: File | null;
  hydrate: () => void;
  setStep: (step: OnboardingStep) => void;
  updateProfile: (profile: OnboardingProfileDraft, step: OnboardingStep) => void;
  setCvFile: (file: File | null) => void;
  clear: () => void;
};

const DRAFT_KEY = "kaziro.next.onboarding.v1";
const DEFAULT_DRAFT: OnboardingDraft = { step: "about-you", profile: {} };

export const ONBOARDING_PATHS: Record<OnboardingStep, string> = {
  "about-you": "/onboarding/about-you",
  summary: "/onboarding/summary",
  domain: "/onboarding/domain",
  experience: "/onboarding/experience",
  skills: "/onboarding/skills",
  cv: "/onboarding/cv",
  config: "/onboarding/config",
};

export const ONBOARDING_STEPS = Object.keys(ONBOARDING_PATHS) as OnboardingStep[];

export const useOnboardingStore = create<OnboardingState>((set, get) => ({
  hydrated: false,
  draft: DEFAULT_DRAFT,
  cvFile: null,
  hydrate: () => {
    const draft = readDraft();
    set({ hydrated: true, draft });
  },
  setStep: (step) => {
    const next = { ...get().draft, step };
    persistDraft(next);
    set({ draft: next });
  },
  updateProfile: (profile, step) => {
    const next = {
      step,
      profile: { ...get().draft.profile, ...profile },
    };
    persistDraft(next);
    set({ draft: next });
  },
  setCvFile: (file) => set({ cvFile: file }),
  clear: () => {
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(DRAFT_KEY);
    }
    set({ draft: DEFAULT_DRAFT, cvFile: null });
  },
}));

export function progressForStep(step: OnboardingStep): { current: number; total: number } {
  return {
    current: ONBOARDING_STEPS.indexOf(step) + 1,
    total: ONBOARDING_STEPS.length,
  };
}

export function pathForStep(step: OnboardingStep): string {
  return ONBOARDING_PATHS[step];
}

function persistDraft(draft: OnboardingDraft): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
}

function readDraft(): OnboardingDraft {
  if (typeof window === "undefined") {
    return DEFAULT_DRAFT;
  }
  const raw = window.sessionStorage.getItem(DRAFT_KEY);
  if (!raw) {
    return DEFAULT_DRAFT;
  }
  try {
    const parsed = JSON.parse(raw) as unknown;
    return isOnboardingDraft(parsed) ? parsed : DEFAULT_DRAFT;
  } catch {
    return DEFAULT_DRAFT;
  }
}

function isOnboardingDraft(value: unknown): value is OnboardingDraft {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.step === "string" &&
    ONBOARDING_STEPS.includes(record.step as OnboardingStep) &&
    typeof record.profile === "object" &&
    record.profile !== null
  );
}
