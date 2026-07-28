"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { z } from "zod";
import { inputClass } from "@/components/forms/fields";
import { ApiError } from "@/lib/api/types";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";

const loginSchema = z.object({
  identifier: z.string().refine(
    (value) => {
      const isEmail = z.email().safeParse(value.trim()).success;
      const isUsername = value.trim().length >= 3;

      return isEmail || isUsername;
    },
    {
      message: "Please enter a valid username or email address.",
    },
  ),
  password: z.string().min(1, "Enter your password."),
});

type LoginFields = z.infer<typeof loginSchema>;

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuthStore((state) => state.login);
  const resendConfirmation = useAuthStore((state) => state.resendConfirmation);
  const pushToast = useToastStore((state) => state.push);
  const [fields, setFields] = useState<LoginFields>({
    identifier: "",
    password: "",
  });
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<keyof LoginFields, string>>
  >({});
  const [formError, setFormError] = useState<string | null>(null);
  const [needsConfirmation, setNeedsConfirmation] = useState(false);
  const [pending, setPending] = useState(false);
  const [resending, setResending] = useState(false);

  async function submit(
    event: React.SubmitEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setFieldErrors({});
    setFormError(null);
    setNeedsConfirmation(false);
    const parsed = loginSchema.safeParse(fields);
    if (!parsed.success) {
      setFieldErrors(errorsFor(parsed.error));
      return;
    }
    setPending(true);
    try {
      await login(parsed.data);
      router.replace(searchParams.get("next") || "/dashboard");
    } catch (error) {
      if (error instanceof ApiError && error.code === "email_not_confirmed") {
        setNeedsConfirmation(true);
      }
      setFormError(
        error instanceof Error ? error.message : "Could not sign in.",
      );
    } finally {
      setPending(false);
    }
  }

  async function resend(): Promise<void> {
    setResending(true);
    try {
      await resendConfirmation(fields.identifier);
      pushToast("success", "Confirmation email sent.");
    } catch (error) {
      pushToast(
        "error",
        error instanceof Error ? error.message : "Could not send email.",
      );
    } finally {
      setResending(false);
    }
  }

  return (
    <>
      <h1 className="mb-4 text-xl font-semibold">Log in</h1>
      <form className="space-y-4" onSubmit={submit}>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Username or Email</span>
          <input
            autoComplete="identifier"
            className={inputClass(Boolean(fieldErrors.identifier))}
            onChange={(event) =>
              setFields({ ...fields, identifier: event.target.value })
            }
            value={fields.identifier}
          />
          {fieldErrors.identifier ? (
            <span className="text-xs text-error">{fieldErrors.identifier}</span>
          ) : null}
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Password</span>
          <input
            autoComplete="current-password"
            className={inputClass(Boolean(fieldErrors.password))}
            onChange={(event) =>
              setFields({ ...fields, password: event.target.value })
            }
            type="password"
            value={fields.password}
          />
          {fieldErrors.password ? (
            <span className="text-xs text-error">{fieldErrors.password}</span>
          ) : null}
        </label>
        <div className="flex justify-end">
          <Link className="link link-primary text-sm" href="/forgot-password">
            Forgot password?
          </Link>
        </div>
        {formError ? (
          <div className="space-y-2" role="alert">
            <p className="text-sm text-error">{formError}</p>
            {needsConfirmation &&
            z.email().safeParse(fields.identifier.trim()).success ? (
              <button
                className="btn btn-ghost btn-sm px-0 text-primary"
                disabled={resending || fields.identifier.trim().length === 0}
                onClick={resend}
                type="button"
              >
                {resending ? "Sending..." : "Resend confirmation email"}
              </button>
            ) : null}
          </div>
        ) : null}
        <button
          className="btn btn-primary h-11 w-full"
          disabled={pending}
          type="submit"
        >
          {pending ? "Signing in..." : "Sign in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-base-content/70">
        <Link
          className="font-medium underline-offset-4 hover:underline"
          href="/signup"
        >
          Create an account
        </Link>
      </p>
    </>
  );
}

function errorsFor(
  error: z.ZodError<LoginFields>,
): Partial<Record<keyof LoginFields, string>> {
  const next: Partial<Record<keyof LoginFields, string>> = {};
  for (const issue of error.issues) {
    const key = issue.path[0];
    if (key === "identifier" || key === "password") {
      next[key] = issue.message;
    }
  }
  return next;
}
