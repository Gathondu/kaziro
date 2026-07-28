"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Clipboard,
  Download,
  FileText,
  RefreshCw,
  Save,
  Send,
  X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createApplication } from "@/lib/api/applications";
import { downloadAuthenticatedFile } from "@/lib/api/client";
import { regenerateDocuments, updateJobDocuments } from "@/lib/api/jobs";
import type { ApplicationDocText } from "@/lib/api/types";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";

type DocumentTab = "cover_letter" | "cv";

type JobDocumentsModalProps = {
  applicationDocument: ApplicationDocText;
  applicationId?: string | null;
  jobId: string;
  onClose: () => void;
  open: boolean;
};

export function JobDocumentsModal({
  applicationDocument,
  applicationId = null,
  jobId,
  onClose,
  open,
}: JobDocumentsModalProps) {
  const token = useAuthStore((state) => state.token?.access_token ?? "");
  const pushToast = useToastStore((state) => state.push);
  const queryClient = useQueryClient();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<DocumentTab>("cover_letter");
  const [cvDraft, setCvDraft] = useState(applicationDocument.tailored_cv_text);
  const [letterDraft, setLetterDraft] = useState(
    applicationDocument.cover_letter_text,
  );

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose, open]);

  const regenerate = useMutation({
    mutationFn: (part: DocumentTab) => regenerateDocuments(token, jobId, part),
    onSuccess: () => {
      pushToast(
        "success",
        "Document regeneration queued. You will be notified when it is ready.",
      );
      void queryClient.invalidateQueries({ queryKey: ["jobs", jobId] });
    },
    onError: (error: Error) => pushToast("error", error.message),
  });
  const save = useMutation({
    mutationFn: () => updateJobDocuments(token, jobId, cvDraft, letterDraft),
    onSuccess: () => {
      pushToast("success", "Document changes saved.");
      void queryClient.invalidateQueries({ queryKey: ["jobs", jobId] });
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (error: Error) => pushToast("error", error.message),
  });
  const addToBoard = useMutation({
    mutationFn: async () => {
      await updateJobDocuments(token, jobId, cvDraft, letterDraft);
      return createApplication(token, jobId);
    },
    onSuccess: (application) => {
      pushToast("success", "Application added to your board.");
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
      void queryClient.invalidateQueries({ queryKey: ["applications"] });
      onClose();
      router.push(`/applications/${application.id}`);
    },
    onError: (error: Error) => pushToast("error", error.message),
  });

  if (!open) return null;

  const isCoverLetter = activeTab === "cover_letter";
  const text = isCoverLetter ? letterDraft : cvDraft;
  const pdfAvailable = isCoverLetter
    ? applicationDocument.cover_letter_pdf_available
    : applicationDocument.cv_pdf_available;
  const downloadPath = isCoverLetter
    ? `/api/v1/jobs/${jobId}/cover-letter.pdf`
    : `/api/v1/jobs/${jobId}/cv.pdf`;
  const filename = isCoverLetter ? "cover-letter.pdf" : "tailored-cv.pdf";

  const copyDocument = async () => {
    try {
      await navigator.clipboard.writeText(text);
      pushToast("success", "Document copied to the clipboard.");
    } catch {
      pushToast("error", "Could not copy the document.");
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/65 p-4"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target) onClose();
      }}
    >
      <section
        aria-labelledby="job-documents-title"
        aria-modal="true"
        className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-base-300 bg-base-100 shadow-2xl"
        role="dialog"
      >
        <header className="flex items-center justify-between border-b border-base-300 px-5 py-4">
          <div>
            <h2
              className="flex items-center gap-2 text-lg font-semibold"
              id="job-documents-title"
            >
              <FileText className="size-5 text-primary" />
              Application documents
            </h2>
            <p className="mt-1 text-xs text-base-content/60">
              Review and edit the generated content before using it.
            </p>
          </div>
          <button
            aria-label="Close application documents"
            className="btn btn-ghost btn-sm btn-square"
            onClick={onClose}
            type="button"
          >
            <X className="size-5" />
          </button>
        </header>

        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-base-300 px-5 py-3">
          <div
            aria-label="Document type"
            className="tabs tabs-box"
            role="tablist"
          >
            <button
              aria-selected={isCoverLetter}
              className={`tab ${isCoverLetter ? "tab-active" : ""}`}
              onClick={() => setActiveTab("cover_letter")}
              role="tab"
              type="button"
            >
              Cover letter
            </button>
            <button
              aria-selected={!isCoverLetter}
              className={`tab ${!isCoverLetter ? "tab-active" : ""}`}
              onClick={() => setActiveTab("cv")}
              role="tab"
              type="button"
            >
              Tailored CV
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => void copyDocument()}
              type="button"
            >
              <Clipboard className="size-4" /> Copy
            </button>
            <button
              className="btn btn-outline btn-sm"
              disabled={!pdfAvailable}
              onClick={() =>
                void downloadAuthenticatedFile(downloadPath, token, filename)
              }
              type="button"
            >
              <Download className="size-4" /> Download PDF
            </button>
            <button
              className="btn btn-outline btn-sm"
              disabled={regenerate.isPending}
              onClick={() => regenerate.mutate(activeTab)}
              type="button"
            >
              {regenerate.isPending ? (
                <span className="loading loading-spinner loading-xs" />
              ) : (
                <RefreshCw className="size-4" />
              )}
              Regenerate
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-hidden p-5">
          <label className="sr-only" htmlFor="generated-document">
            {isCoverLetter ? "Generated cover letter" : "Generated tailored CV"}
          </label>
          <textarea
            className="textarea textarea-bordered h-[55vh] w-full resize-none whitespace-pre-wrap font-sans text-sm leading-6"
            id="generated-document"
            onChange={(event) =>
              isCoverLetter
                ? setLetterDraft(event.target.value)
                : setCvDraft(event.target.value)
            }
            value={text}
          />
        </div>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-base-300 px-5 py-4">
          <p className="text-xs text-base-content/60">
            Changes update both the editable content and downloadable PDFs.
          </p>
          <div className="flex flex-wrap gap-2">
            <button
              className="btn btn-outline btn-sm"
              disabled={save.isPending || addToBoard.isPending}
              onClick={() => save.mutate()}
              type="button"
            >
              {save.isPending ? (
                <span className="loading loading-spinner loading-xs" />
              ) : (
                <Save className="size-4" />
              )}
              Save changes
            </button>
            {applicationId ? (
              <button
                className="btn btn-primary btn-sm"
                onClick={() => {
                  onClose();
                  router.push(`/applications/${applicationId}`);
                }}
                type="button"
              >
                View on board <Send className="size-4" />
              </button>
            ) : (
              <button
                className="btn btn-primary btn-sm"
                disabled={save.isPending || addToBoard.isPending}
                onClick={() => addToBoard.mutate()}
                type="button"
              >
                {addToBoard.isPending ? (
                  <span className="loading loading-spinner loading-xs" />
                ) : (
                  <Send className="size-4" />
                )}
                Add to board
              </button>
            )}
          </div>
        </footer>
      </section>
    </div>
  );
}
