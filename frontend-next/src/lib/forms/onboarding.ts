import { z } from "zod";
import type { JobConfigPayload, ProfilePayload } from "@/lib/api/types";
import type {
  OnboardingProfileDraft,
  OnboardingStep,
} from "@/lib/stores/onboarding";

export const DEFAULT_FETCH_CRON = "0 6 * * *";
export const DOMAIN_MAX_LENGTH = 100;
export const EXPERIENCE_YEARS_MAX = 60;
export type ProfileOnboardingStep = Exclude<OnboardingStep, "cv" | "config">;
export type ProfileDraftField = keyof OnboardingProfileDraft;

export const onboardingSchemas = {
  "about-you": z.object({
    full_name: z.string().trim().min(1, "Name is required").max(255),
  }),
  summary: z.object({
    professional_summary: z.string().max(4000).optional().or(z.literal("")),
  }),
  domain: z.object({
    domain: z
      .string()
      .max(DOMAIN_MAX_LENGTH, "Domain must be at most 100 characters")
      .optional()
      .or(z.literal("")),
  }),
  experience: z.object({
    experience_years: z.coerce
      .number()
      .int()
      .min(0)
      .max(EXPERIENCE_YEARS_MAX)
      .optional()
      .nullable(),
  }),
  skills: z.object({
    skillsText: z.string().optional(),
  }),
};

export type JobConfigFormFields = {
  name: string;
  keywordsText: string;
  location: string;
  remote_only: boolean;
  salaryMinInput: string;
  salaryMaxInput: string;
  fetch_schedule_cron: string;
};

export const jobConfigFormSchema = z
  .object({
    name: z.string().trim().max(255, "Name must be at most 255 characters"),
    keywordsText: z.string().trim().min(1, "Add at least one keyword"),
    location: z
      .string()
      .trim()
      .max(255, "Location must be at most 255 characters"),
    remote_only: z.boolean(),
    salaryMinInput: z.string().regex(/^\d*$/, "Use whole numbers only"),
    salaryMaxInput: z.string().regex(/^\d*$/, "Use whole numbers only"),
    fetch_schedule_cron: z.string().trim().min(1, "Choose a fetch schedule"),
  })
  .refine(
    (fields) => {
      const min = optionalNumber(fields.salaryMinInput);
      const max = optionalNumber(fields.salaryMaxInput);
      return min === null || max === null || min <= max;
    },
    { message: "Min salary cannot exceed max", path: ["salaryMaxInput"] },
  );

export function fieldErrorsFor<TField extends string>(
  error: z.ZodError,
  fields: readonly TField[],
): Partial<Record<TField, string>> {
  const next: Partial<Record<TField, string>> = {};
  for (const issue of error.issues) {
    const key = issue.path[0];
    if (typeof key === "string" && fields.includes(key as TField)) {
      next[key as TField] = issue.message;
    }
  }
  return next;
}

export function validateProfileStep(
  step: ProfileOnboardingStep,
  rawValue: string,
):
  | { ok: true; patch: OnboardingProfileDraft }
  | { ok: false; message: string } {
  if (step === "about-you") {
    const parsed = onboardingSchemas["about-you"].safeParse({
      full_name: rawValue,
    });
    return parsed.success
      ? { ok: true, patch: { full_name: parsed.data.full_name } }
      : {
          ok: false,
          message: parsed.error.issues[0]?.message ?? "Enter your name.",
        };
  }
  if (step === "summary") {
    const parsed = onboardingSchemas.summary.safeParse({
      professional_summary: rawValue,
    });
    const text = parsed.success ? parsed.data.professional_summary?.trim() : "";
    return parsed.success
      ? { ok: true, patch: { professional_summary: text || undefined } }
      : {
          ok: false,
          message: parsed.error.issues[0]?.message ?? "Check your summary.",
        };
  }
  if (step === "domain") {
    const parsed = onboardingSchemas.domain.safeParse({ domain: rawValue });
    const text = parsed.success ? parsed.data.domain?.trim() : "";
    return parsed.success
      ? { ok: true, patch: { domain: text || undefined } }
      : {
          ok: false,
          message: parsed.error.issues[0]?.message ?? "Check your domain.",
        };
  }
  if (step === "experience") {
    const parsed = onboardingSchemas.experience.safeParse({
      experience_years: rawValue.trim() === "" ? null : rawValue,
    });
    return parsed.success
      ? {
          ok: true,
          patch: {
            experience_years: parsed.data.experience_years ?? undefined,
          },
        }
      : {
          ok: false,
          message: parsed.error.issues[0]?.message ?? "Check your experience.",
        };
  }
  const parsed = onboardingSchemas.skills.safeParse({ skillsText: rawValue });
  const text = parsed.success ? parsed.data.skillsText?.trim() : "";
  return parsed.success
    ? { ok: true, patch: { skillsText: text || undefined } }
    : {
        ok: false,
        message: parsed.error.issues[0]?.message ?? "Check your skills.",
      };
}

export function sanitizeIntegerInput(
  raw: string,
  max: number,
  maxDigits: number,
): string {
  const digits = raw.replace(/\D/g, "").slice(0, maxDigits);
  if (!digits) {
    return "";
  }
  const parsed = Number.parseInt(digits, 10);
  if (Number.isNaN(parsed)) {
    return "";
  }
  return String(Math.min(max, Math.max(0, parsed)));
}

export function commaList(text: string | undefined): string[] {
  return (text ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}

export function profilePayloadFromDraft(
  draft: OnboardingProfileDraft,
): { ok: true; payload: ProfilePayload } | { ok: false; message: string } {
  const fullName = draft.full_name?.trim();
  if (!fullName) {
    return {
      ok: false,
      message: "Your profile needs a name before setup can finish.",
    };
  }

  return {
    ok: true,
    payload: {
      full_name: fullName,
      professional_summary: emptyToNull(draft.professional_summary),
      skills: commaList(draft.skillsText),
      experience_years: draft.experience_years ?? null,
      domain: emptyToNull(draft.domain),
      values_statement: null,
      linkedin_url: null,
    },
  };
}

export function jobConfigPayloadFromFields(
  fields: JobConfigFormFields,
): JobConfigPayload {
  const parsed = jobConfigFormSchema.parse(fields);
  return {
    name: emptyToNull(parsed.name),
    keywords: commaList(parsed.keywordsText),
    location: emptyToNull(parsed.location),
    remote_only: parsed.remote_only,
    salary_min: optionalNumber(parsed.salaryMinInput),
    salary_max: optionalNumber(parsed.salaryMaxInput),
    employment_types: [],
    fetch_schedule_cron: parsed.fetch_schedule_cron,
    is_active: true,
  };
}

function optionalNumber(value: string): number | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : Number.parseInt(trimmed, 10);
}

function emptyToNull(value: string | undefined): string | null {
  const trimmed = value?.trim() ?? "";
  return trimmed === "" ? null : trimmed;
}
