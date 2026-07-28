"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BriefcaseBusiness, MapPin, Plus, Search } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { importJobUrl, listJobs } from "@/lib/api/jobs";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";

export default function JobsPage() {
  const token = useAuthStore((state) => state.token?.access_token ?? "");
  const pushToast = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const [keyword, setKeyword] = useState("");
  const [classification, setClassification] = useState("");
  const [remoteOnly, setRemoteOnly] = useState(false);
  const [importUrl, setImportUrl] = useState("");
  const jobs = useQuery({
    queryKey: ["jobs", keyword, classification, remoteOnly],
    queryFn: () =>
      listJobs(token, {
        keyword: keyword || undefined,
        classification: classification ? [classification] : undefined,
        remoteOnly: remoteOnly || undefined,
      }),
    enabled: Boolean(token),
  });
  const importer = useMutation({
    mutationFn: () => importJobUrl(token, importUrl),
    onSuccess: (result) => {
      setImportUrl("");
      pushToast(
        "success",
        result.duplicate
          ? "This job is already in your workspace."
          : "Job imported. Evaluation has started.",
      );
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (error: Error) => pushToast("error", error.message),
  });

  function submitImport(event: FormEvent): void {
    event.preventDefault();
    importer.mutate();
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-primary">Opportunity inbox</p>
          <h1 className="text-3xl font-semibold tracking-tight">Jobs</h1>
          <p className="mt-1 text-base-content/65">
            Review jobs found by approved providers or import one directly.
          </p>
        </div>
        <form className="join w-full max-w-xl" onSubmit={submitImport}>
          <label className="input join-item flex flex-1 items-center gap-2">
            <Plus className="size-4" />
            <span className="sr-only">Job URL</span>
            <input
              required
              type="url"
              value={importUrl}
              onChange={(event) => setImportUrl(event.target.value)}
              placeholder="Paste a job URL"
            />
          </label>
          <button
            className="btn btn-primary join-item"
            disabled={importer.isPending}
            type="submit"
          >
            {importer.isPending ? "Importing…" : "Import"}
          </button>
        </form>
      </div>

      <section className="mt-7 flex flex-wrap gap-3 rounded-2xl border border-base-300 bg-base-100 p-4">
        <label className="input flex min-w-56 flex-1 items-center gap-2">
          <Search className="size-4" />
          <span className="sr-only">Search jobs</span>
          <input
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="Title, company, or keyword"
          />
        </label>
        <select
          className="select"
          aria-label="Classification"
          value={classification}
          onChange={(event) => setClassification(event.target.value)}
        >
          <option value="">All classifications</option>
          <option value="GOOD_FIT">Good fit</option>
          <option value="MAYBE">Maybe</option>
          <option value="NOT_A_FIT">Not a fit</option>
          <option value="NOT_INTERESTED">Not interested</option>
        </select>
        <label className="label cursor-pointer gap-2 rounded-xl border border-base-300 px-4">
          <input
            className="checkbox checkbox-primary checkbox-sm"
            checked={remoteOnly}
            onChange={(event) => setRemoteOnly(event.target.checked)}
            type="checkbox"
          />
          Remote only
        </label>
      </section>

      {jobs.isPending ? (
        <div className="grid min-h-72 place-items-center">
          <span className="loading loading-spinner text-primary" />
        </div>
      ) : jobs.isError ? (
        <div className="alert alert-error mt-6" role="alert">
          {jobs.error.message}
        </div>
      ) : jobs.data.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-dashed border-base-300 bg-base-100 p-12 text-center">
          <BriefcaseBusiness className="mx-auto size-8 text-primary" />
          <h2 className="mt-3 font-semibold">No matching jobs yet</h2>
          <p className="mt-1 text-sm text-base-content/60">
            Run a search configuration or paste a job URL above.
          </p>
        </div>
      ) : (
        <section className="mt-6 grid gap-4 md:grid-cols-2">
          {jobs.data.map((job) => (
            <Link
              className="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-marketing-card transition hover:-translate-y-0.5"
              href={`/jobs/${job.id}`}
              key={job.id}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-semibold">{job.title}</h2>
                  <p className="text-sm text-base-content/65">
                    {job.company_name}
                  </p>
                </div>
                {job.evaluation ? (
                  <span className="badge badge-primary badge-outline">
                    {job.evaluation.overall_score.toFixed(1)}
                  </span>
                ) : (
                  <span className="badge badge-ghost">Evaluating</span>
                )}
              </div>
              <div className="mt-4 flex flex-wrap gap-2 text-xs">
                <span className="badge badge-ghost gap-1">
                  <MapPin className="size-3" />
                  {job.location || "Location not specified"}
                </span>
                {job.remote_flag ? (
                  <span className="badge badge-success badge-outline">
                    Remote
                  </span>
                ) : null}
                <span className="badge badge-ghost">
                  {job.evaluation?.final_classification.replaceAll("_", " ") ??
                    "Pending"}
                </span>
              </div>
            </Link>
          ))}
        </section>
      )}
    </main>
  );
}
