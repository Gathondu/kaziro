"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowLeft, Download, Save } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  createApplication,
  updateApplicationDocs,
} from "@/lib/api/applications";
import { downloadAuthenticatedFile } from "@/lib/api/client";
import { getJob } from "@/lib/api/jobs";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";

export default function ApplyPage() {
  const jobId = String(useParams().id);
  const router = useRouter();
  const token = useAuthStore((state) => state.token?.access_token ?? "");
  const pushToast = useToastStore((state) => state.push);
  const job = useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => getJob(token, jobId),
    enabled: Boolean(token),
  });
  const [cvDraft, setCv] = useState<string>();
  const [letterDraft, setLetter] = useState<string>();
  const cv =
    cvDraft ?? job.data?.evaluation?.application_doc?.tailored_cv_text ?? "";
  const letter =
    letterDraft ??
    job.data?.evaluation?.application_doc?.cover_letter_text ??
    "";
  const create = useMutation({
    mutationFn: async () => {
      const application = await createApplication(token, jobId);
      return updateApplicationDocs(token, application.id, cv, letter);
    },
    onSuccess: (application) => {
      pushToast("success", "Application added to your board.");
      router.push(`/applications/${application.id}`);
    },
    onError: (error: Error) => pushToast("error", error.message),
  });

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link className="btn btn-ghost btn-sm -ml-2" href={`/jobs/${jobId}`}>
        <ArrowLeft className="size-4" /> Back to job
      </Link>
      <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">Application documents</h1>
          <p className="mt-1 text-base-content/65">
            {job.data?.title ?? "Loading…"} · {job.data?.company_name}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="btn btn-outline btn-sm"
            onClick={() =>
              void downloadAuthenticatedFile(
                `/api/v1/jobs/${jobId}/cv.pdf`,
                token,
                "tailored-cv.pdf",
              )
            }
          >
            <Download className="size-4" /> CV PDF
          </button>
          <button
            className="btn btn-outline btn-sm"
            onClick={() =>
              void downloadAuthenticatedFile(
                `/api/v1/jobs/${jobId}/cover-letter.pdf`,
                token,
                "cover-letter.pdf",
              )
            }
          >
            <Download className="size-4" /> Letter PDF
          </button>
          <button
            className="btn btn-primary btn-sm"
            disabled={create.isPending || !cv || !letter}
            onClick={() => create.mutate()}
          >
            <Save className="size-4" /> Add to board
          </button>
        </div>
      </div>
      <div className="mt-6 grid gap-5 lg:grid-cols-2">
        <label className="form-control">
          <span className="label-text mb-2 font-semibold">
            Tailored CV preview
          </span>
          <textarea
            className="textarea textarea-bordered min-h-[65vh] font-mono text-sm leading-6"
            value={cv}
            onChange={(event) => setCv(event.target.value)}
          />
        </label>
        <label className="form-control">
          <span className="label-text mb-2 font-semibold">
            Cover letter preview
          </span>
          <textarea
            className="textarea textarea-bordered min-h-[65vh] text-sm leading-6"
            value={letter}
            onChange={(event) => setLetter(event.target.value)}
          />
        </label>
      </div>
      <p className="mt-3 text-xs text-base-content/55">
        Add this application to your board to save edits and track its progress.
      </p>
    </main>
  );
}
