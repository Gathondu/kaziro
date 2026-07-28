"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download, Save, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import {
  deleteApplication,
  getApplication,
  updateApplicationDocs,
  updateApplicationNotes,
  updateApplicationStatus,
} from "@/lib/api/applications";
import { downloadAuthenticatedFile } from "@/lib/api/client";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";

const statuses = [
  "draft",
  "sent",
  "interviewing",
  "offered",
  "rejected",
  "withdrawn",
];

export default function ApplicationDetailPage() {
  const id = String(useParams().id);
  const router = useRouter();
  const token = useAuthStore((state) => state.token?.access_token ?? "");
  const pushToast = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const application = useQuery({
    queryKey: ["applications", id],
    queryFn: () => getApplication(token, id),
    enabled: Boolean(token),
  });
  const [notesDraft, setNotes] = useState<string>();
  const [cvDraft, setCv] = useState<string>();
  const [letterDraft, setLetter] = useState<string>();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["applications"] });
    void queryClient.invalidateQueries({ queryKey: ["applications", id] });
  };
  const save = useMutation({
    mutationFn: async () => {
      await updateApplicationDocs(token, id, cv, letter);
      return updateApplicationNotes(token, id, notes);
    },
    onSuccess: () => {
      refresh();
      pushToast("success", "Application saved.");
    },
    onError: (error: Error) => pushToast("error", error.message),
  });
  const transition = useMutation({
    mutationFn: (status: string) => updateApplicationStatus(token, id, status),
    onSuccess: () => {
      refresh();
      pushToast("success", "Status updated.");
    },
    onError: (error: Error) => pushToast("error", error.message),
  });
  const remove = useMutation({
    mutationFn: () => deleteApplication(token, id),
    onSuccess: () => {
      pushToast("success", "Application deleted.");
      router.push("/applications");
    },
    onError: (error: Error) => pushToast("error", error.message),
  });

  if (application.isPending)
    return (
      <main className="grid min-h-[70vh] place-items-center">
        <span className="loading loading-spinner text-primary" />
      </main>
    );
  if (application.isError)
    return (
      <main className="p-6">
        <div className="alert alert-error">{application.error.message}</div>
      </main>
    );
  const item = application.data;
  const notes = notesDraft ?? item.notes;
  const cv = cvDraft ?? item.application_doc.tailored_cv_text;
  const letter = letterDraft ?? item.application_doc.cover_letter_text;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <Link className="btn btn-ghost btn-sm -ml-2" href="/applications">
        <ArrowLeft className="size-4" /> Back to board
      </Link>
      <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">{item.job_posting.title}</h1>
          <p className="mt-1 text-base-content/65">
            {item.job_posting.company_name}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            className="select select-bordered select-sm"
            aria-label="Application status"
            value={item.status}
            onChange={(event) => transition.mutate(event.target.value)}
          >
            {statuses.map((status) => (
              <option value={status} key={status}>
                {status[0].toUpperCase() + status.slice(1)}
              </option>
            ))}
          </select>
          <button
            className="btn btn-outline btn-sm"
            onClick={() =>
              void downloadAuthenticatedFile(
                `/api/v1/applications/${id}/cv.pdf`,
                token,
                "tailored-cv.pdf",
              )
            }
          >
            <Download className="size-4" /> CV
          </button>
          <button
            className="btn btn-outline btn-sm"
            onClick={() =>
              void downloadAuthenticatedFile(
                `/api/v1/applications/${id}/cover-letter.pdf`,
                token,
                "cover-letter.pdf",
              )
            }
          >
            <Download className="size-4" /> Letter
          </button>
          <button
            className="btn btn-primary btn-sm"
            disabled={save.isPending}
            onClick={() => save.mutate()}
          >
            <Save className="size-4" /> Save
          </button>
          <button
            className="btn btn-ghost btn-sm text-error"
            disabled={remove.isPending}
            onClick={() => {
              if (confirm("Delete this application?")) remove.mutate();
            }}
          >
            <Trash2 className="size-4" /> Delete
          </button>
        </div>
      </div>
      <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_1fr]">
        <section className="space-y-5">
          <label className="form-control">
            <span className="label-text mb-2 font-semibold">Tailored CV</span>
            <textarea
              className="textarea textarea-bordered min-h-96 font-mono text-sm leading-6"
              value={cv}
              onChange={(event) => setCv(event.target.value)}
            />
          </label>
          <label className="form-control">
            <span className="label-text mb-2 font-semibold">Cover letter</span>
            <textarea
              className="textarea textarea-bordered min-h-96 text-sm leading-6"
              value={letter}
              onChange={(event) => setLetter(event.target.value)}
            />
          </label>
        </section>
        <aside className="space-y-5">
          <label className="form-control rounded-2xl border border-base-300 bg-base-100 p-5">
            <span className="label-text mb-2 font-semibold">Private notes</span>
            <textarea
              className="textarea textarea-bordered min-h-36"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Interview details, contacts, follow-ups…"
            />
          </label>
          <section className="rounded-2xl border border-base-300 bg-base-100 p-5">
            <h2 className="font-semibold">Timeline</h2>
            <ol className="mt-5 space-y-5 border-l border-base-300 pl-5">
              {item.events?.map((event) => (
                <li className="relative" key={event.id}>
                  <span className="absolute -left-[1.55rem] top-1 size-2 rounded-full bg-primary" />
                  <p className="text-sm font-semibold">
                    {event.event_type.replaceAll("_", " ")}
                  </p>
                  <p className="text-xs text-base-content/55">
                    {new Date(event.event_date).toLocaleString()}
                  </p>
                  {event.notes ? (
                    <p className="mt-1 text-sm">{event.notes}</p>
                  ) : null}
                </li>
              ))}
            </ol>
          </section>
        </aside>
      </div>
    </main>
  );
}
