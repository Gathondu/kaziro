"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";

export function ConfirmEmailPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const confirmEmail = useAuthStore((state) => state.confirmEmail);
  const pushToast = useToastStore((state) => state.push);
  const token = searchParams.get("token");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const didRun = useRef(false);

  useEffect(() => {
    if (didRun.current) {
      return;
    }
    didRun.current = true;
    if (!token) {
      return;
    }
    void (async () => {
      try {
        await confirmEmail(token);
        pushToast("success", "Email confirmed. Welcome to Kaziro.");
        router.replace("/onboarding");
      } catch (error) {
        setErrorMessage(error instanceof Error ? error.message : "Could not confirm your email.");
      }
    })();
  }, [confirmEmail, pushToast, router, token]);

  const failureMessage = !token
    ? "This confirmation link is missing its token."
    : errorMessage;
  const isChecking = failureMessage === null;

  return (
    <>
      <h1 className="mb-3 text-xl font-semibold">
        {isChecking ? "Confirming email" : "Confirmation failed"}
      </h1>
      <p className="text-sm leading-relaxed text-base-content/75">
        {isChecking ? "Confirming your Kaziro account..." : failureMessage}
      </p>
      {isChecking ? (
        <span className="loading loading-spinner mt-6 text-primary" aria-label="Confirming" />
      ) : (
        <Link className="btn btn-primary mt-6 w-full" href="/login">
          Back to log in
        </Link>
      )}
    </>
  );
}
