"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ExternalLink,
  FileText,
  RefreshCw,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { JobDocumentsModal } from "@/components/jobs/JobDocumentsModal";
import {
  getJob,
  markJobNotInterested,
  regenerateDocuments,
  triggerJobEvaluation,
} from "@/lib/api/jobs";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";

export default function JobDetailPage() {
  const id = String(useParams().id);
  const token = useAuthStore((state) => state.token?.access_token ?? "");
  const pushToast = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const [documentsOpen, setDocumentsOpen] = useState(false);
  const job = useQuery({
    queryKey: ["jobs", id],
    queryFn: () => getJob(token, id),
    enabled: Boolean(token && id),
  });
  const action = useMutation({
    mutationFn: async (kind: "evaluate" | "generate" | "dismiss") => {
      if (kind === "evaluate") await triggerJobEvaluation(token, id);
      else if (kind === "generate") await regenerateDocuments(token, id);
      else await markJobNotInterested(token, id);
      return kind;
    },
    onSuccess: (kind) => {
      const message =
        kind === "generate"
          ? "Document generation queued. You will be notified when it is ready."
          : kind === "evaluate"
            ? "Evaluation queued. You will be notified when it is ready."
            : "Job marked as not interested.";
      pushToast("success", message);
      void queryClient.invalidateQueries({ queryKey: ["jobs", id] });
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (error: Error) => pushToast("error", error.message),
  });

  if (job.isPending) {
    return (
      <main className="grid min-h-[70vh] place-items-center">
        <span className="loading loading-spinner text-primary" />
      </main>
    );
  }
  if (job.isError) {
    return (
      <main className="mx-auto max-w-5xl p-6">
        <div className="alert alert-error">{job.error.message}</div>
      </main>
    );
  }

  const item = job.data;
  const evaluation = item.evaluation;
  const research = item.company_summary;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link className="btn btn-ghost btn-sm -ml-2 mb-4" href="/jobs">
        <ArrowLeft className="size-4" /> Back to jobs
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <h1 className="text-3xl font-semibold">{item.title}</h1>
          <p className="mt-1 text-lg text-base-content/65">
            {item.company_name} · {item.location}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {item.application_url ? (
            <a
              className="btn btn-outline btn-sm"
              href={item.application_url}
              rel="noreferrer"
              target="_blank"
            >
              Original listing <ExternalLink className="size-4" />
            </a>
          ) : null}
          <button
            className="btn btn-ghost btn-sm"
            disabled={action.isPending}
            onClick={() => action.mutate("dismiss")}
          >
            <X className="size-4" /> Not interested
          </button>
          {evaluation ? (
            <button
              className="btn btn-outline btn-sm"
              disabled={action.isPending}
              onClick={() => action.mutate("evaluate")}
            >
              <RefreshCw className="size-4" /> Re-run evaluation
            </button>
          ) : (
            <button
              className="btn btn-primary btn-sm"
              disabled={action.isPending}
              onClick={() => action.mutate("evaluate")}
            >
              Evaluate now
            </button>
          )}
          {evaluation?.final_classification === "good_fit" ? (
            evaluation.application_doc ? (
              <>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setDocumentsOpen(true)}
                  type="button"
                >
                  <FileText className="size-4" /> View documents
                </button>
                <Link
                  className="btn btn-primary btn-sm"
                  href={`/jobs/${id}/apply`}
                >
                  Prepare application <Send className="size-4" />
                </Link>
              </>
            ) : (
              <button
                className="btn btn-primary btn-sm"
                disabled={action.isPending}
                onClick={() => action.mutate("generate")}
                type="button"
              >
                {action.isPending ? (
                  <span className="loading loading-spinner loading-xs" />
                ) : (
                  <Sparkles className="size-4" />
                )}
                Generate documents
              </button>
            )
          ) : null}
        </div>
      </div>

      <div className="mt-7 grid gap-6 lg:grid-cols-[1.2fr_.8fr]">
        <div className="space-y-6">
          <section className="rounded-2xl border border-base-300 bg-base-100 p-6">
            <h2 className="text-lg font-semibold">Role description</h2>
            <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-base-content/80">
              {item.description}
            </p>
            {item.requirements.length ? (
              <ul className="mt-5 list-inside list-disc space-y-2 text-sm">
                {item.requirements.map((requirement) => (
                  <li key={requirement}>{requirement}</li>
                ))}
              </ul>
            ) : null}
          </section>
          {research ? (
            <section className="rounded-2xl border border-base-300 bg-base-100 p-6">
              <h2 className="text-lg font-semibold">Company research</h2>
              <p className="mt-3 text-sm leading-7">{research.ai_summary}</p>
              <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                {[
                  ["Mission", research.mission],
                  ["Values", research.values],
                  ["Culture", research.culture],
                  ["Technology", research.tech_stack],
                  ["Company size", research.team_size_approx],
                  ["Recent developments", research.recent_news],
                ].map(([label, value]) => (
                  <div className="rounded-xl bg-base-200 p-4" key={label}>
                    <dt className="text-xs font-semibold uppercase tracking-wide text-primary">
                      {label}
                    </dt>
                    <dd className="mt-1 text-sm">{value}</dd>
                  </div>
                ))}
              </dl>
              {research.source_urls.length ? (
                <div className="mt-5">
                  <h3 className="text-sm font-semibold">Sources</h3>
                  <ul className="mt-2 space-y-1 text-sm">
                    {research.source_urls.map((url) => (
                      <li key={url}>
                        <a
                          className="link link-primary break-all"
                          href={url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          {url}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>
          ) : null}
        </div>
        <aside>
          <section className="sticky top-24 rounded-2xl border border-base-300 bg-base-100 p-6">
            <h2 className="text-lg font-semibold">Fit evaluation</h2>
            {evaluation ? (
              <>
                <div className="mt-4 flex items-center gap-3">
                  <div
                    className="radial-progress text-primary"
                    style={
                      {
                        "--value": evaluation.overall_score * 10,
                      } as React.CSSProperties
                    }
                    role="progressbar"
                  >
                    {evaluation.overall_score.toFixed(1)}
                  </div>
                  <div>
                    <p className="font-semibold">
                      {evaluation.final_classification.replaceAll("_", " ")}
                    </p>
                    <p className="text-xs text-base-content/55">out of 10</p>
                  </div>
                </div>
                <p className="mt-5 text-sm leading-6">
                  {evaluation.final_feedback}
                </p>
                <div className="mt-5 space-y-2">
                  {Object.entries(evaluation.dimension_scores).map(
                    ([key, value]) => (
                      <div
                        className="flex justify-between rounded-lg bg-base-200 px-3 py-2 text-sm"
                        key={key}
                      >
                        <span>{key.replaceAll("_", " ")}</span>
                        <span className="font-semibold">{String(value)}</span>
                      </div>
                    ),
                  )}
                </div>
              </>
            ) : (
              <p className="mt-3 text-sm text-base-content/60">
                Evaluation is pending.
              </p>
            )}
          </section>
        </aside>
      </div>
      {evaluation?.application_doc ? (
        <JobDocumentsModal
          applicationDocument={evaluation.application_doc}
          jobId={id}
          onClose={() => setDocumentsOpen(false)}
          open={documentsOpen}
        />
      ) : null}
    </main>
  );
}
