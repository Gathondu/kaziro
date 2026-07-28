"use client";

import {
  createJobConfig,
  disableJobConfig,
  listJobConfigs,
  listSchedulePresets,
  runJobConfig,
  updateJobConfig,
} from "@/lib/api/jobConfigs";
import {
  disableAccount,
  getCvFile,
  getProfile,
  putProfile,
  uploadCvPdf,
} from "@/lib/api/profile";
import type {
  JobConfigPayload,
  JobConfigResponse,
  ProfilePayload,
} from "@/lib/api/types";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  FileText,
  Eye,
  Pencil,
  Play,
  Plus,
  Power,
  Save,
  UserRound,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

export default function SettingsPage() {
  const token = useAuthStore((state) => state.token?.access_token ?? "");
  const logout = useAuthStore((state) => state.logout);
  const pushToast = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"searches" | "profile">("searches");
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [cvPreviewOpen, setCvPreviewOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<JobConfigResponse | null>(
    null,
  );
  const modalNameInput = useRef<HTMLInputElement>(null);
  const configs = useQuery({
    queryKey: ["job-configs"],
    queryFn: () => listJobConfigs(token),
    enabled: Boolean(token),
  });
  const schedulePresets = useQuery({
    queryKey: ["job-config-schedule-presets"],
    queryFn: () => listSchedulePresets(token),
    enabled: Boolean(token),
  });
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: () => getProfile(token),
    enabled: Boolean(token),
  });
  const cvPreview = useQuery({
    queryKey: ["profile-cv-file"],
    queryFn: () => getCvFile(token),
    enabled: Boolean(token) && cvPreviewOpen,
  });
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [scheduleCron, setScheduleCron] = useState("0 6 * * *");
  const [configIsActive, setConfigIsActive] = useState(true);
  const [pendingConfigIds, setPendingConfigIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [profileDraft, setProfileForm] = useState<ProfilePayload>();
  const profileForm: ProfilePayload = profileDraft ?? {
    full_name: profile.data?.full_name ?? "",
    professional_summary: profile.data?.professional_summary ?? "",
    skills: profile.data?.skills ?? [],
    experience_years: profile.data?.experience_years ?? null,
    domain: profile.data?.domain ?? "",
    values_statement: profile.data?.values_statement ?? "",
    linkedin_url: profile.data?.linkedin_url ?? "",
  };

  useEffect(() => {
    if (!configModalOpen) return;
    modalNameInput.current?.focus();
    function closeOnEscape(event: KeyboardEvent): void {
      if (event.key === "Escape") setConfigModalOpen(false);
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [configModalOpen]);

  useEffect(() => {
    if (!cvPreviewOpen) return;
    function closeOnEscape(event: KeyboardEvent): void {
      if (event.key === "Escape") setCvPreviewOpen(false);
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [cvPreviewOpen]);

  const saveConfig = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string | null;
      payload: JobConfigPayload;
    }) =>
      id
        ? updateJobConfig(token, id, payload)
        : createJobConfig(token, payload),
    onSuccess: (_config, variables) => {
      setConfigModalOpen(false);
      setEditingConfig(null);
      void queryClient.invalidateQueries({ queryKey: ["job-configs"] });
      pushToast(
        "success",
        variables.id
          ? "Search configuration updated."
          : "Search configuration created.",
      );
    },
    onError: (error: Error) => pushToast("error", error.message),
  });
  const configAction = useMutation({
    mutationFn: async ({
      id,
      action,
    }: {
      id: string;
      action: "run" | "disable";
    }) => {
      if (action === "run") await runJobConfig(token, id);
      else await disableJobConfig(token, id);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["job-configs"] });
      pushToast("success", "Search configuration updated.");
    },
    onError: (error: Error) => pushToast("error", error.message),
    onSettled: (_data, _error, variables) => {
      setPendingConfigIds((current) => {
        const next = new Set(current);
        next.delete(variables.id);
        return next;
      });
    },
  });
  const saveProfile = useMutation({
    mutationFn: () =>
      putProfile(token, {
        ...profileForm,
        full_name: profileForm.full_name.trim(),
        professional_summary: profileForm.professional_summary?.trim() || null,
        domain: profileForm.domain?.trim() || null,
        values_statement: profileForm.values_statement?.trim() || null,
        linkedin_url: profileForm.linkedin_url?.trim() || null,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["profile"] });
      pushToast("success", "Profile saved.");
    },
    onError: (error: Error) => pushToast("error", error.message),
  });
  const cvUpload = useMutation({
    mutationFn: (file: File) => uploadCvPdf(token, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["profile"] });
      pushToast("success", "Master CV updated.");
    },
    onError: (error: Error) => pushToast("error", error.message),
  });
  const deactivate = useMutation({
    mutationFn: () => disableAccount(token),
    onSuccess: () => {
      logout();
      window.location.assign("/");
    },
    onError: (error: Error) => pushToast("error", error.message),
  });

  function submitConfig(event: FormEvent): void {
    event.preventDefault();
    saveConfig.mutate({
      id: editingConfig?.id ?? null,
      payload: {
        name: name.trim() || null,
        keywords: keywords
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        location: location.trim() || null,
        remote_only: remoteOnly,
        salary_min: editingConfig?.salary_min ?? null,
        salary_max: editingConfig?.salary_max ?? null,
        employment_types: editingConfig?.employment_types ?? [],
        fetch_schedule_cron: scheduleCron,
        is_active: configIsActive,
      },
    });
  }

  function openCreateConfig(): void {
    setEditingConfig(null);
    setName("");
    setKeywords("");
    setLocation("");
    setRemoteOnly(false);
    setScheduleCron(
      schedulePresets.data?.[0]?.fetch_schedule_cron ?? "0 6 * * *",
    );
    setConfigIsActive(true);
    saveConfig.reset();
    setConfigModalOpen(true);
  }

  function openEditConfig(config: JobConfigResponse): void {
    setEditingConfig(config);
    setName(config.name ?? "");
    setKeywords(config.keywords.join(", "));
    setLocation(config.location ?? "");
    setRemoteOnly(config.remote_only);
    setScheduleCron(config.fetch_schedule_cron);
    setConfigIsActive(config.is_active);
    saveConfig.reset();
    setConfigModalOpen(true);
  }

  function triggerConfigAction(id: string, action: "run" | "disable"): void {
    setPendingConfigIds((current) => new Set(current).add(id));
    configAction.mutate({ id, action });
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <p className="text-sm font-medium text-primary">Preferences</p>
      <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
      <div className="tabs tabs-box mt-6 w-fit" role="tablist">
        <button
          className={`tab ${tab === "searches" ? "tab-active" : ""}`}
          onClick={() => setTab("searches")}
          role="tab"
        >
          Job searches
        </button>
        <button
          className={`tab ${tab === "profile" ? "tab-active" : ""}`}
          onClick={() => setTab("profile")}
          role="tab"
        >
          Profile & CV
        </button>
      </div>

      {tab === "searches" ? (
        <div className="mt-6">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">Job search configs</h2>
              <p className="mt-1 text-sm text-base-content/60">
                Manage when and how Kaziro searches for new opportunities.
              </p>
            </div>
            <button
              className="btn btn-primary gap-2"
              onClick={openCreateConfig}
              type="button"
            >
              <Plus className="size-4" aria-hidden="true" />
              Create config
            </button>
          </div>
          <section className="space-y-4">
            {configs.data?.map((config) => (
              <article
                className="flex flex-col gap-4 rounded-2xl border border-base-300 bg-base-100 p-5 sm:flex-row sm:items-center sm:justify-between"
                key={config.id}
              >
                <div className="min-w-0">
                  <div>
                    <h2 className="font-semibold">
                      {config.name || config.keywords.join(", ")}
                    </h2>
                    <p className="mt-1 text-sm text-base-content/60">
                      {config.location || "Any location"} ·{" "}
                      {schedulePresets.data?.find(
                        (preset) =>
                          preset.fetch_schedule_cron ===
                          config.fetch_schedule_cron,
                      )?.label ?? config.fetch_schedule_cron}
                    </p>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {config.keywords.map((keyword) => (
                      <span className="badge badge-ghost" key={keyword}>
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
                  <span
                    className={`badge ${config.is_active ? "badge-success badge-outline" : "badge-ghost"}`}
                  >
                    {config.is_active ? "Active" : "Disabled"}
                  </span>
                  <button
                    aria-label={`Edit ${config.name || "job search"} config`}
                    className="btn btn-ghost btn-sm"
                    disabled={pendingConfigIds.has(config.id)}
                    onClick={() => openEditConfig(config)}
                    type="button"
                  >
                    <Pencil className="size-4" aria-hidden="true" /> Edit
                  </button>
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={
                      !config.is_active || pendingConfigIds.has(config.id)
                    }
                    onClick={() => triggerConfigAction(config.id, "run")}
                    type="button"
                  >
                    <Play className="size-4" /> Run now
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    disabled={
                      !config.is_active || pendingConfigIds.has(config.id)
                    }
                    onClick={() => triggerConfigAction(config.id, "disable")}
                    type="button"
                  >
                    <Power className="size-4" /> Disable
                  </button>
                </div>
              </article>
            ))}
            {!configs.isPending && !configs.data?.length ? (
              <div className="rounded-2xl border border-dashed border-base-300 p-10 text-center text-sm text-base-content/60">
                No search configurations yet.
              </div>
            ) : null}
          </section>

          {configModalOpen ? (
            <div
              className="fixed inset-0 z-[70] grid place-items-center bg-black/60 p-4 backdrop-blur-sm"
              onMouseDown={(event) => {
                if (event.currentTarget === event.target)
                  setConfigModalOpen(false);
              }}
            >
              <section
                aria-labelledby="config-dialog-title"
                aria-modal="true"
                className="w-full max-w-lg rounded-2xl border border-base-300 bg-base-100 p-6 shadow-2xl"
                role="dialog"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2
                      className="text-xl font-semibold"
                      id="config-dialog-title"
                    >
                      {editingConfig ? "Edit job config" : "Create job config"}
                    </h2>
                    <p className="mt-1 text-sm text-base-content/60">
                      Define the roles Kaziro should find and when searches
                      should run.
                    </p>
                  </div>
                  <button
                    aria-label={`Close ${editingConfig ? "edit" : "create"} config dialog`}
                    className="btn btn-ghost btn-circle btn-sm"
                    onClick={() => setConfigModalOpen(false)}
                    type="button"
                  >
                    <X className="size-4" aria-hidden="true" />
                  </button>
                </div>

                <form className="mt-5" onSubmit={submitConfig}>
                  <label className="form-control">
                    <span className="label-text mb-1">Name</span>
                    <input
                      className="input input-bordered w-full"
                      onChange={(event) => setName(event.target.value)}
                      placeholder="Senior frontend roles"
                      ref={modalNameInput}
                      value={name}
                    />
                  </label>
                  <label className="form-control mt-4">
                    <span className="label-text mb-1">Keywords</span>
                    <input
                      className="input input-bordered w-full"
                      onChange={(event) => setKeywords(event.target.value)}
                      placeholder="React, TypeScript, design systems"
                      required
                      value={keywords}
                    />
                    <span className="mt-1 text-xs text-base-content/50">
                      Separate multiple keywords with commas.
                    </span>
                  </label>
                  <label className="form-control mt-4">
                    <span className="label-text mb-1">Location</span>
                    <input
                      className="input input-bordered w-full"
                      onChange={(event) => setLocation(event.target.value)}
                      placeholder="Nairobi or Europe"
                      value={location}
                    />
                  </label>
                  <label className="form-control mt-4">
                    <span className="label-text mb-1">Search schedule</span>
                    <select
                      className="select select-bordered w-full"
                      onChange={(event) => setScheduleCron(event.target.value)}
                      value={scheduleCron}
                    >
                      {(
                        schedulePresets.data ?? [
                          {
                            id: "daily",
                            label: "Once per day (06:00 UTC)",
                            fetch_schedule_cron: "0 6 * * *",
                          },
                          {
                            id: "weekly",
                            label: "Once per week (Monday 06:00 UTC)",
                            fetch_schedule_cron: "0 6 * * 1",
                          },
                        ]
                      ).map((preset) => (
                        <option
                          key={preset.id}
                          value={preset.fetch_schedule_cron}
                        >
                          {preset.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <div className="mt-4 flex flex-wrap gap-x-6 gap-y-3">
                    <label className="label w-fit cursor-pointer justify-start gap-3">
                      <input
                        checked={remoteOnly}
                        className="checkbox checkbox-primary"
                        onChange={(event) =>
                          setRemoteOnly(event.target.checked)
                        }
                        type="checkbox"
                      />
                      Remote only
                    </label>
                    <label className="label w-fit cursor-pointer justify-start gap-3">
                      <input
                        checked={configIsActive}
                        className="checkbox checkbox-primary"
                        onChange={(event) =>
                          setConfigIsActive(event.target.checked)
                        }
                        type="checkbox"
                      />
                      Active
                    </label>
                  </div>
                  {saveConfig.isError ? (
                    <div className="alert alert-error mt-4" role="alert">
                      {saveConfig.error.message}
                    </div>
                  ) : null}
                  <div className="mt-6 flex justify-end gap-3">
                    <button
                      className="btn btn-ghost"
                      disabled={saveConfig.isPending}
                      onClick={() => setConfigModalOpen(false)}
                      type="button"
                    >
                      Cancel
                    </button>
                    <button
                      className="btn btn-primary"
                      disabled={saveConfig.isPending}
                      type="submit"
                    >
                      {saveConfig.isPending
                        ? editingConfig
                          ? "Saving…"
                          : "Creating…"
                        : editingConfig
                          ? "Save changes"
                          : "Create config"}
                    </button>
                  </div>
                </form>
              </section>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <form
            className="rounded-2xl border border-base-300 bg-base-100 p-5"
            onSubmit={(event) => {
              event.preventDefault();
              saveProfile.mutate();
            }}
          >
            <div className="flex items-center gap-2">
              <UserRound className="size-5 text-primary" />
              <h2 className="font-semibold">Candidate profile</h2>
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="form-control">
                <span className="label-text mb-1">Full name</span>
                <input
                  className="input input-bordered"
                  maxLength={255}
                  required
                  value={profileForm.full_name}
                  onChange={(event) =>
                    setProfileForm({
                      ...profileForm,
                      full_name: event.target.value,
                    })
                  }
                />
              </label>
              <label className="form-control">
                <span className="label-text mb-1">Professional domain</span>
                <input
                  className="input input-bordered"
                  maxLength={100}
                  value={profileForm.domain ?? ""}
                  onChange={(event) =>
                    setProfileForm({
                      ...profileForm,
                      domain: event.target.value,
                    })
                  }
                />
              </label>
              <label className="form-control">
                <span className="label-text mb-1">Years of experience</span>
                <input
                  className="input input-bordered"
                  max={60}
                  min={0}
                  placeholder="e.g. 10"
                  type="number"
                  value={profileForm.experience_years ?? ""}
                  onChange={(event) =>
                    setProfileForm({
                      ...profileForm,
                      experience_years:
                        event.target.value === ""
                          ? null
                          : Number(event.target.value),
                    })
                  }
                />
              </label>
              <label className="form-control">
                <span className="label-text mb-1">LinkedIn profile</span>
                <input
                  className="input input-bordered"
                  placeholder="https://www.linkedin.com/in/your-profile"
                  type="url"
                  value={profileForm.linkedin_url ?? ""}
                  onChange={(event) =>
                    setProfileForm({
                      ...profileForm,
                      linkedin_url: event.target.value,
                    })
                  }
                />
              </label>
              <label className="form-control sm:col-span-2 flex justify-between">
                <span className="label-text mb-1">
                  Skills (comma separated)
                </span>
                <textarea
                  className="textarea textarea-bordered min-h-24"
                  value={profileForm.skills.join(", ")}
                  onChange={(event) =>
                    setProfileForm({
                      ...profileForm,
                      skills: event.target.value
                        .split(",")
                        .map((value) => value.trim())
                        .filter(Boolean),
                    })
                  }
                />
              </label>
              <label className="form-control sm:col-span-2 flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
                <span className="label-text sm:pt-2">Professional summary</span>
                <div className="flex w-full flex-col sm:max-w-md">
                  <textarea
                    className="textarea textarea-bordered min-h-72 w-full"
                    maxLength={4000}
                    value={profileForm.professional_summary ?? ""}
                    onChange={(event) =>
                      setProfileForm({
                        ...profileForm,
                        professional_summary: event.target.value,
                      })
                    }
                  />
                  <span className="mt-1 self-end text-right text-xs text-base-content/60">
                    {(profileForm.professional_summary ?? "").length}/4000
                  </span>
                </div>
              </label>
              <label className="form-control sm:col-span-2 flex justify-between">
                <span className="label-text mb-1">Values and preferences</span>
                <textarea
                  className="textarea textarea-bordered"
                  maxLength={2000}
                  value={profileForm.values_statement ?? ""}
                  onChange={(event) =>
                    setProfileForm({
                      ...profileForm,
                      values_statement: event.target.value,
                    })
                  }
                />
              </label>
            </div>
            <button
              className="btn btn-primary mt-5"
              disabled={saveProfile.isPending}
              type="submit"
            >
              <Save className="size-4" /> Save profile
            </button>
          </form>
          <aside className="space-y-6">
            <section className="rounded-2xl border border-base-300 bg-base-100 p-5">
              <div className="flex items-center gap-2">
                <FileText className="size-5 text-primary" />
                <h2 className="font-semibold">Master CV</h2>
              </div>
              {profile.data?.has_master_cv ? (
                <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
                  <p className="min-w-0 break-all text-sm text-base-content/60">
                    {profile.data.cv_original_filename ?? "master-cv.pdf"}
                  </p>
                  <button
                    className="btn btn-outline btn-sm shrink-0"
                    onClick={() => setCvPreviewOpen(true)}
                    type="button"
                  >
                    <Eye className="size-4" aria-hidden="true" />
                    View CV
                  </button>
                </div>
              ) : (
                <p className="mt-2 text-sm text-base-content/60">
                  Upload a PDF to tailor future applications.
                </p>
              )}
              <input
                className="file-input file-input-bordered mt-4 w-full"
                type="file"
                accept="application/pdf"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) cvUpload.mutate(file);
                }}
              />
            </section>
            <section className="rounded-2xl border border-error/30 bg-error/5 p-5">
              <h2 className="font-semibold text-error">Disable account</h2>
              <p className="mt-2 text-sm">
                This signs you out and prevents future access until an
                administrator restores the account.
              </p>
              <button
                className="btn btn-error btn-outline btn-sm mt-4"
                disabled={deactivate.isPending}
                onClick={() => {
                  if (confirm("Disable your Kaziro account?"))
                    deactivate.mutate();
                }}
              >
                Disable account
              </button>
            </section>
          </aside>
        </div>
      )}
      {cvPreviewOpen ? (
        <div
          className="fixed inset-0 z-[80] grid place-items-center bg-black/60 p-4 backdrop-blur-sm"
          onMouseDown={(event) => {
            if (event.currentTarget === event.target) setCvPreviewOpen(false);
          }}
        >
          <section
            aria-labelledby="cv-preview-title"
            aria-modal="true"
            className="flex h-[85vh] w-full max-w-5xl flex-col rounded-2xl border border-base-300 bg-base-100 p-4 shadow-2xl sm:p-6"
            role="dialog"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h2 className="font-semibold" id="cv-preview-title">
                  Master CV
                </h2>
                <p className="mt-1 truncate text-sm text-base-content/60">
                  {profile.data?.cv_original_filename ?? "master-cv.pdf"}
                </p>
              </div>
              <button
                aria-label="Close CV preview"
                className="btn btn-ghost btn-circle btn-sm"
                onClick={() => setCvPreviewOpen(false)}
                type="button"
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </div>
            <div className="mt-4 min-h-0 flex-1 overflow-hidden rounded-xl border border-base-300 bg-base-200">
              {cvPreview.isPending ? (
                <div className="grid h-full place-items-center">
                  <span
                    aria-label="Loading CV preview"
                    className="loading loading-spinner text-primary"
                  />
                </div>
              ) : cvPreview.isError ? (
                <div className="grid h-full place-items-center p-6 text-center">
                  <div>
                    <p className="font-medium">Unable to load the CV.</p>
                    <p className="mt-1 text-sm text-base-content/60">
                      {cvPreview.error.message}
                    </p>
                  </div>
                </div>
              ) : cvPreview.data ? (
                <CvPreviewFrame
                  blob={cvPreview.data}
                  title={`CV preview: ${profile.data?.cv_original_filename ?? "master-cv.pdf"}`}
                />
              ) : null}
            </div>
          </section>
        </div>
      ) : null}
    </main>
  );
}

function CvPreviewFrame({ blob, title }: { blob: Blob; title: string }) {
  const frameRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const objectUrl = URL.createObjectURL(blob);
    const frame = frameRef.current;
    if (frame) frame.src = objectUrl;
    return () => URL.revokeObjectURL(objectUrl);
  }, [blob]);

  return (
    <iframe className="h-full w-full bg-white" ref={frameRef} title={title} />
  );
}
