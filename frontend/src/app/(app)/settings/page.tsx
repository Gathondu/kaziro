"use client";

import {
  createJobConfig,
  disableJobConfig,
  listJobConfigs,
  runJobConfig,
} from "@/lib/api/jobConfigs";
import {
  disableAccount,
  getProfile,
  putProfile,
  uploadCvPdf,
} from "@/lib/api/profile";
import type { ProfilePayload } from "@/lib/api/types";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Play, Plus, Power, Save, UserRound, X } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

export default function SettingsPage() {
  const token = useAuthStore((state) => state.token?.access_token ?? "");
  const logout = useAuthStore((state) => state.logout);
  const pushToast = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"searches" | "profile">("searches");
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const modalNameInput = useRef<HTMLInputElement>(null);
  const configs = useQuery({
    queryKey: ["job-configs"],
    queryFn: () => listJobConfigs(token),
    enabled: Boolean(token),
  });
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: () => getProfile(token),
    enabled: Boolean(token),
  });
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const [location, setLocation] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(false);
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

  const create = useMutation({
    mutationFn: () =>
      createJobConfig(token, {
        name: name || null,
        keywords: keywords
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        location: location || null,
        remote_only: remoteOnly,
        employment_types: [],
        fetch_schedule_cron: "0 6 * * *",
        is_active: true,
      }),
    onSuccess: () => {
      setName("");
      setKeywords("");
      setLocation("");
      setRemoteOnly(false);
      setConfigModalOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["job-configs"] });
      pushToast("success", "Search configuration created.");
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
  });
  const saveProfile = useMutation({
    mutationFn: () => putProfile(token, profileForm),
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
    create.mutate();
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
              onClick={() => setConfigModalOpen(true)}
              type="button"
            >
              <Plus className="size-4" aria-hidden="true" />
              Create config
            </button>
          </div>
          <section className="space-y-4">
            {configs.data?.map((config) => (
              <article
                className="rounded-2xl border border-base-300 bg-base-100 p-5"
                key={config.id}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="font-semibold">
                      {config.name || config.keywords.join(", ")}
                    </h2>
                    <p className="mt-1 text-sm text-base-content/60">
                      {config.location || "Any location"} ·{" "}
                      {config.fetch_schedule_cron}
                    </p>
                  </div>
                  <span
                    className={`badge ${config.is_active ? "badge-success badge-outline" : "badge-ghost"}`}
                  >
                    {config.is_active ? "Active" : "Disabled"}
                  </span>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {config.keywords.map((keyword) => (
                    <span className="badge badge-ghost" key={keyword}>
                      {keyword}
                    </span>
                  ))}
                </div>
                <div className="mt-4 flex gap-2">
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={!config.is_active || configAction.isPending}
                    onClick={() =>
                      configAction.mutate({ id: config.id, action: "run" })
                    }
                  >
                    <Play className="size-4" /> Run now
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    disabled={!config.is_active || configAction.isPending}
                    onClick={() =>
                      configAction.mutate({ id: config.id, action: "disable" })
                    }
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
                aria-labelledby="create-config-title"
                aria-modal="true"
                className="w-full max-w-lg rounded-2xl border border-base-300 bg-base-100 p-6 shadow-2xl"
                role="dialog"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2
                      className="text-xl font-semibold"
                      id="create-config-title"
                    >
                      Create job config
                    </h2>
                    <p className="mt-1 text-sm text-base-content/60">
                      Define the roles Kaziro should find for you.
                    </p>
                  </div>
                  <button
                    aria-label="Close create config dialog"
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
                  <label className="label mt-4 w-fit cursor-pointer justify-start gap-3">
                    <input
                      checked={remoteOnly}
                      className="checkbox checkbox-primary"
                      onChange={(event) => setRemoteOnly(event.target.checked)}
                      type="checkbox"
                    />
                    Remote only
                  </label>
                  {create.isError ? (
                    <div className="alert alert-error mt-4" role="alert">
                      {create.error.message}
                    </div>
                  ) : null}
                  <div className="mt-6 flex justify-end gap-3">
                    <button
                      className="btn btn-ghost"
                      disabled={create.isPending}
                      onClick={() => setConfigModalOpen(false)}
                      type="button"
                    >
                      Cancel
                    </button>
                    <button
                      className="btn btn-primary"
                      disabled={create.isPending}
                      type="submit"
                    >
                      {create.isPending ? "Creating…" : "Create config"}
                    </button>
                  </div>
                </form>
              </section>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_.75fr]">
          <section className="rounded-2xl border border-base-300 bg-base-100 p-5">
            <div className="flex items-center gap-2">
              <UserRound className="size-5 text-primary" />
              <h2 className="font-semibold">Candidate profile</h2>
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="form-control">
                <span className="label-text mb-1">Full name</span>
                <input
                  className="input input-bordered"
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
                  value={profileForm.domain ?? ""}
                  onChange={(event) =>
                    setProfileForm({
                      ...profileForm,
                      domain: event.target.value,
                    })
                  }
                />
              </label>
              <label className="form-control sm:col-span-2 flex justify-between">
                <span className="label-text mb-1">
                  Skills (comma separated)
                </span>
                <input
                  className="input input-bordered"
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
              <label className="form-control sm:col-span-2 flex justify-between">
                <span className="label-text mb-1">Professional summary</span>
                <textarea
                  className="textarea textarea-bordered min-h-32"
                  value={profileForm.professional_summary ?? ""}
                  onChange={(event) =>
                    setProfileForm({
                      ...profileForm,
                      professional_summary: event.target.value,
                    })
                  }
                />
              </label>
              <label className="form-control sm:col-span-2 flex justify-between">
                <span className="label-text mb-1">Values and preferences</span>
                <textarea
                  className="textarea textarea-bordered"
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
              onClick={() => saveProfile.mutate()}
            >
              <Save className="size-4" /> Save profile
            </button>
          </section>
          <aside className="space-y-6">
            <section className="rounded-2xl border border-base-300 bg-base-100 p-5">
              <div className="flex items-center gap-2">
                <FileText className="size-5 text-primary" />
                <h2 className="font-semibold">Master CV</h2>
              </div>
              <p className="mt-2 text-sm text-base-content/60">
                {profile.data?.has_master_cv
                  ? "A master CV is available."
                  : "Upload a PDF to tailor future applications."}
              </p>
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
    </main>
  );
}
