"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, type SubmitEvent } from "react";
import { inputClass } from "@/components/forms/fields";
import { OnboardingStepFrame } from "@/components/onboarding/OnboardingStepFrame";
import {
  createJobConfig,
  listSchedulePresets,
  runJobConfig,
} from "@/lib/api/jobConfigs";
import { putProfile, uploadCvPdf } from "@/lib/api/profile";
import {
  DEFAULT_FETCH_CRON,
  fieldErrorsFor,
  jobConfigFormSchema,
  jobConfigPayloadFromFields,
  profilePayloadFromDraft,
  sanitizeIntegerInput,
  type JobConfigFormFields,
} from "@/lib/forms/onboarding";
import { useAuthStore } from "@/lib/stores/auth";
import { useOnboardingStore } from "@/lib/stores/onboarding";
import { useToastStore } from "@/lib/stores/toast";

const CONFIG_ERROR_FIELDS = [
  "name",
  "keywordsText",
  "location",
  "salaryMinInput",
  "salaryMaxInput",
  "fetch_schedule_cron",
] as const;

const FALLBACK_SCHEDULES = [
  { id: "daily", label: "Daily", fetch_schedule_cron: DEFAULT_FETCH_CRON },
  { id: "weekly", label: "Weekly", fetch_schedule_cron: "0 6 * * 1" },
];

export function OnboardingConfigStep() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const token = useAuthStore((state) => state.token?.access_token ?? null);
  const draft = useOnboardingStore((state) => state.draft);
  const cvFile = useOnboardingStore((state) => state.cvFile);
  const clearOnboarding = useOnboardingStore((state) => state.clear);
  const pushToast = useToastStore((state) => state.push);
  const [fields, setFields] = useState<JobConfigFormFields>({
    name: "",
    keywordsText: "",
    location: "",
    remote_only: false,
    salaryMinInput: "",
    salaryMaxInput: "",
    fetch_schedule_cron: DEFAULT_FETCH_CRON,
  });
  const [fieldErrors, setFieldErrors] =
    useState<Partial<Record<(typeof CONFIG_ERROR_FIELDS)[number], string>>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const schedules = useQuery({
    queryKey: ["job-configs", "schedule-presets"],
    queryFn: () => listSchedulePresets(token ?? ""),
    enabled: Boolean(token),
  });

  const finishSetup = useMutation({
    mutationFn: async () => {
      if (!token) {
        throw new Error("Your session has expired. Log in again to finish setup.");
      }
      if (!cvFile) {
        throw new Error("Use Back to choose your CV before finishing setup.");
      }
      const profile = profilePayloadFromDraft(draft.profile);
      if (!profile.ok) {
        throw new Error(profile.message);
      }
      await putProfile(token, profile.payload);
      await uploadCvPdf(token, cvFile);
      const config = await createJobConfig(token, jobConfigPayloadFromFields(fields));
      await runJobConfig(token, config.id);
      return config;
    },
    onSuccess: () => {
      clearOnboarding();
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
      pushToast("success", "Setup complete. Your first search is queued.");
      router.replace("/dashboard");
    },
    onError: (error) => {
      setFormError(error instanceof Error ? error.message : "Could not finish setup.");
    },
  });

  function submit(event: SubmitEvent<HTMLFormElement>): void {
    event.preventDefault();
    setFormError(null);
    setFieldErrors({});
    const parsed = jobConfigFormSchema.safeParse(fields);
    if (!parsed.success) {
      setFieldErrors(fieldErrorsFor(parsed.error, CONFIG_ERROR_FIELDS));
      return;
    }
    finishSetup.mutate();
  }

  function updateField<TKey extends keyof JobConfigFormFields>(
    key: TKey,
    value: JobConfigFormFields[TKey],
  ): void {
    setFieldErrors((current) => ({ ...current, [key]: undefined }));
    setFormError(null);
    setFields((current) => ({ ...current, [key]: value }));
  }

  const scheduleOptions = schedules.data?.length ? schedules.data : FALLBACK_SCHEDULES;

  return (
    <OnboardingStepFrame
      title="First job search"
      description="We will enqueue your first pipeline run so evaluations can start flowing in."
    >
      <form className="space-y-4" onSubmit={submit}>
        {formError ? (
          <p className="text-sm text-error" role="alert">
            {formError}
          </p>
        ) : null}
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Config name (optional)</span>
          <input
            className={inputClass(Boolean(fieldErrors.name))}
            onChange={(event) => updateField("name", event.target.value)}
            value={fields.name}
          />
          {fieldErrors.name ? <span className="text-xs text-error">{fieldErrors.name}</span> : null}
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Keywords (comma-separated)</span>
          <input
            className={inputClass(Boolean(fieldErrors.keywordsText))}
            onChange={(event) => updateField("keywordsText", event.target.value)}
            value={fields.keywordsText}
          />
          {fieldErrors.keywordsText ? (
            <span className="text-xs text-error">{fieldErrors.keywordsText}</span>
          ) : null}
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Location</span>
          <input
            className={inputClass(Boolean(fieldErrors.location))}
            onChange={(event) => updateField("location", event.target.value)}
            value={fields.location}
          />
          {fieldErrors.location ? (
            <span className="text-xs text-error">{fieldErrors.location}</span>
          ) : null}
        </label>
        <label className="flex w-full items-start gap-3 rounded-xl border border-base-300 bg-base-200 px-3 py-2.5">
          <input
            checked={fields.remote_only}
            className="checkbox checkbox-primary checkbox-sm mt-0.5"
            onChange={(event) => updateField("remote_only", event.target.checked)}
            type="checkbox"
          />
          <span className="space-y-0.5">
            <span className="block text-sm font-medium">Remote only</span>
            <span className="block text-xs text-base-content/70">
              Only include jobs that are fully remote.
            </span>
          </span>
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Salary min</span>
            <input
              className={inputClass(Boolean(fieldErrors.salaryMinInput))}
              inputMode="numeric"
              maxLength={9}
              onChange={(event) =>
                updateField("salaryMinInput", sanitizeIntegerInput(event.target.value, 999999999, 9))
              }
              pattern="[0-9]*"
              value={fields.salaryMinInput}
            />
            {fieldErrors.salaryMinInput ? (
              <span className="text-xs text-error">{fieldErrors.salaryMinInput}</span>
            ) : null}
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium">Salary max</span>
            <input
              className={inputClass(Boolean(fieldErrors.salaryMaxInput))}
              inputMode="numeric"
              maxLength={9}
              onChange={(event) =>
                updateField("salaryMaxInput", sanitizeIntegerInput(event.target.value, 999999999, 9))
              }
              pattern="[0-9]*"
              value={fields.salaryMaxInput}
            />
            {fieldErrors.salaryMaxInput ? (
              <span className="text-xs text-error">{fieldErrors.salaryMaxInput}</span>
            ) : null}
          </label>
        </div>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Fetch schedule</span>
          <select
            className={inputClass(Boolean(fieldErrors.fetch_schedule_cron))}
            disabled={schedules.isPending && !schedules.data}
            onChange={(event) => updateField("fetch_schedule_cron", event.target.value)}
            value={fields.fetch_schedule_cron}
          >
            {scheduleOptions.map((preset) => (
              <option key={preset.id} value={preset.fetch_schedule_cron}>
                {preset.label}
              </option>
            ))}
          </select>
          {fieldErrors.fetch_schedule_cron ? (
            <span className="text-xs text-error">{fieldErrors.fetch_schedule_cron}</span>
          ) : null}
          {schedules.isError ? (
            <span className="text-xs text-warning">Using default schedules for now.</span>
          ) : null}
        </label>
        <button className="btn btn-primary h-11 w-full" disabled={finishSetup.isPending} type="submit">
          {finishSetup.isPending ? "Finishing..." : "Finish setup"}
        </button>
      </form>
    </OnboardingStepFrame>
  );
}
