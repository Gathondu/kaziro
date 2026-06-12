"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type SubmitEvent } from "react";
import { inputClass, textareaClass } from "@/components/forms/fields";
import { OnboardingStepFrame } from "@/components/onboarding/OnboardingStepFrame";
import {
  DOMAIN_MAX_LENGTH,
  EXPERIENCE_YEARS_MAX,
  profilePayloadFromDraft,
  sanitizeIntegerInput,
  validateProfileStep,
  type ProfileDraftField,
  type ProfileOnboardingStep,
} from "@/lib/forms/onboarding";
import {
  pathForStep,
  type OnboardingProfileDraft,
  type OnboardingStep,
  useOnboardingStore,
} from "@/lib/stores/onboarding";

type StepConfig = {
  title: string;
  description: string;
  label: string;
  field: ProfileDraftField;
  next: OnboardingStep;
  kind: "input" | "textarea" | "number";
  required?: boolean;
  autoComplete?: string;
  maxLength?: number;
  rows?: number;
};

const STEP_CONFIG: Record<ProfileOnboardingStep, StepConfig> = {
  "about-you": {
    title: "Tell us about yourself",
    description: "We use this to evaluate job fit and tailor documents.",
    label: "Name",
    field: "full_name",
    next: "summary",
    kind: "input",
    required: true,
    autoComplete: "name",
  },
  summary: {
    title: "Professional summary",
    description: "A short overview helps us tailor recommendations. Optional, so you can skip.",
    label: "Summary",
    field: "professional_summary",
    next: "domain",
    kind: "textarea",
    rows: 4,
  },
  domain: {
    title: "Your domain",
    description:
      "Your industry or problem space helps us match roles and language to your context.",
    label: "Domain",
    field: "domain",
    next: "experience",
    kind: "textarea",
    maxLength: DOMAIN_MAX_LENGTH,
    rows: 4,
  },
  experience: {
    title: "Years of experience",
    description: "Optional rough total years in roles relevant to your search.",
    label: "Years of experience",
    field: "experience_years",
    next: "skills",
    kind: "number",
  },
  skills: {
    title: "Skills",
    description:
      "Optional strengths as comma-separated keywords, such as TypeScript, Postgres, team leadership.",
    label: "Skills (comma-separated)",
    field: "skillsText",
    next: "cv",
    kind: "input",
    autoComplete: "off",
  },
};

export function OnboardingProfileStep({ step }: { step: ProfileOnboardingStep }) {
  const router = useRouter();
  const config = STEP_CONFIG[step];
  const draft = useOnboardingStore((state) => state.draft);
  const updateProfile = useOnboardingStore((state) => state.updateProfile);
  const [value, setValue] = useState(() => valueForField(draft.profile, config.field));
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (step !== "about-you" && !draft.profile.full_name?.trim()) {
      router.replace(pathForStep("about-you"));
    }
  }, [draft.profile.full_name, router, step]);

  const canSubmit = useMemo(
    () => !config.required || value.trim().length > 0,
    [config.required, value],
  );
  const primaryLabel = !config.required && value.trim().length === 0 ? "Skip" : "Next";

  function submit(event: SubmitEvent<HTMLFormElement>): void {
    event.preventDefault();
    setFieldError(null);
    setFormError(null);
    const result = validateProfileStep(step, value);
    if (!result.ok) {
      setFieldError(result.message);
      return;
    }
    const nextProfile = { ...draft.profile, ...result.patch };
    if (step === "skills") {
      const payload = profilePayloadFromDraft(nextProfile);
      if (!payload.ok) {
        setFormError(payload.message);
        return;
      }
    }
    updateProfile(result.patch, config.next);
    router.push(pathForStep(config.next));
  }

  function updateValue(next: string): void {
    setFieldError(null);
    setFormError(null);
    setValue(config.kind === "number" ? sanitizeIntegerInput(next, EXPERIENCE_YEARS_MAX, 2) : next);
  }

  return (
    <OnboardingStepFrame title={config.title} description={config.description}>
      <form className="space-y-4" onSubmit={submit}>
        {formError ? (
          <p className="text-sm text-error" role="alert">
            {formError}
          </p>
        ) : null}
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">{config.label}</span>
          {config.kind === "textarea" ? (
            <div className="relative">
              <textarea
                className={`${textareaClass(Boolean(fieldError))} ${config.maxLength ? "pr-14 pb-10" : ""}`}
                maxLength={config.maxLength}
                onChange={(event) => updateValue(event.target.value)}
                rows={config.rows}
                value={value}
              />
              {config.maxLength ? (
                <span className="pointer-events-none absolute bottom-3 right-3 text-xs tabular-nums text-base-content/60">
                  {value.length}/{config.maxLength}
                </span>
              ) : null}
            </div>
          ) : (
            <input
              autoComplete={config.autoComplete}
              className={inputClass(Boolean(fieldError))}
              inputMode={config.kind === "number" ? "numeric" : undefined}
              maxLength={config.kind === "number" ? 2 : undefined}
              onChange={(event) => updateValue(event.target.value)}
              pattern={config.kind === "number" ? "[0-9]*" : undefined}
              type={config.kind === "number" ? "text" : "text"}
              value={value}
            />
          )}
          {fieldError ? <span className="text-xs text-error">{fieldError}</span> : null}
        </label>
        <button className="btn btn-primary h-11 w-full" disabled={!canSubmit} type="submit">
          {primaryLabel}
        </button>
      </form>
    </OnboardingStepFrame>
  );
}

function valueForField(profile: OnboardingProfileDraft, field: ProfileDraftField): string {
  const value = profile[field];
  return typeof value === "number" ? String(value) : value ?? "";
}
