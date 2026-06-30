"use client";

import { FileText } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { OnboardingStepFrame } from "@/components/onboarding/OnboardingStepFrame";
import { pathForStep, useOnboardingStore } from "@/lib/stores/onboarding";

export function OnboardingCvStep() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const cvFile = useOnboardingStore((state) => state.cvFile);
  const setCvFile = useOnboardingStore((state) => state.setCvFile);
  const setStep = useOnboardingStore((state) => state.setStep);
  const [previewUrl, setPreviewUrl] = useState<string | null>(() =>
    cvFile ? URL.createObjectURL(cvFile) : null,
  );
  const previewUrlRef = useRef(previewUrl);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (previewUrlRef.current) {
        URL.revokeObjectURL(previewUrlRef.current);
      }
    };
  }, []);

  function pickFile(file: File | undefined): void {
    setError(null);
    if (!file) {
      setCvFile(null);
      replacePreviewUrl(null);
      return;
    }
    if (!isPdf(file)) {
      setCvFile(null);
      replacePreviewUrl(null);
      setError("Please choose a PDF file.");
      return;
    }
    setCvFile(file);
    replacePreviewUrl(URL.createObjectURL(file));
  }

  function replacePreviewUrl(nextUrl: string | null): void {
    revokeUrl(previewUrlRef.current);
    previewUrlRef.current = nextUrl;
    setPreviewUrl(nextUrl);
  }

  function next(): void {
    if (!cvFile) {
      setError("Select a PDF to continue.");
      return;
    }
    setStep("config");
    router.push(pathForStep("config"));
  }

  return (
    <OnboardingStepFrame
      title="Upload your CV"
      description="We extract text for embeddings and keep the PDF in secure storage."
    >
      <div className="space-y-5">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">PDF file</span>
          <input
            ref={inputRef}
            accept="application/pdf"
            className="hidden"
            onChange={(event) => pickFile(event.target.files?.[0])}
            type="file"
          />
          <div className="flex flex-wrap items-center gap-3">
            <button
              className="btn btn-outline"
              onClick={() => inputRef.current?.click()}
              type="button"
            >
              Choose file
            </button>
            <span
              className="min-w-0 flex-1 truncate text-sm text-base-content/70"
              title={cvFile?.name ?? "No file chosen"}
            >
              {cvFile?.name ?? "No file chosen"}
            </span>
          </div>
        </label>
        {error ? (
          <p className="text-sm text-error" role="alert">
            {error}
          </p>
        ) : null}
        {previewUrl ? (
          <div className="overflow-hidden rounded-2xl border border-base-300 bg-base-200">
            <iframe
              className="h-96 w-full"
              src={`${previewUrl}#page=1&view=FitH`}
              title="CV preview"
            />
          </div>
        ) : (
          <div className="flex min-h-56 flex-col items-center justify-center rounded-2xl border border-dashed border-base-300 bg-base-200 p-6 text-center">
            <FileText className="mb-3 size-8 text-primary" aria-hidden="true" />
            <p className="text-sm text-base-content/70">
              Your PDF preview will appear here.
            </p>
          </div>
        )}
        <button
          className="btn btn-primary h-11 w-full"
          disabled={!cvFile}
          onClick={next}
          type="button"
        >
          Next
        </button>
      </div>
    </OnboardingStepFrame>
  );
}

function isPdf(file: File): boolean {
  return (
    file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
  );
}

function revokeUrl(url: string | null): void {
  if (url) {
    URL.revokeObjectURL(url);
  }
}
