"use client";

import Link from "next/link";
import { useState } from "react";
import { z } from "zod";
import { inputClass } from "@/components/forms/fields";
import { useAuthStore } from "@/lib/stores/auth";
import { useToastStore } from "@/lib/stores/toast";

const signupSchema = z
  .object({
    username: z
      .string()
      .trim()
      .min(3, "Enter your desired username.")
      .max(20, "Username must be at most 20 characters."),
    email: z.email("Enter a valid email."),
    password: z.string().min(8, "Use at least 8 characters."),
    confirm: z.string().min(8, "Confirm your password."),
  })
  .refine((value) => value.password === value.confirm, {
    message: "Passwords do not match.",
    path: ["confirm"],
  });

type SignupFields = z.infer<typeof signupSchema>;

export function SignupForm() {
  const signup = useAuthStore((state) => state.signup);
  const resendConfirmation = useAuthStore((state) => state.resendConfirmation);
  const pushToast = useToastStore((state) => state.push);
  const [fields, setFields] = useState<SignupFields>({
    username: "",
    email: "",
    password: "",
    confirm: "",
  });
  const [fieldErrors, setFieldErrors] = useState<
    Partial<Record<keyof SignupFields, string>>
  >({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [resending, setResending] = useState(false);

  async function submit(
    event: React.SubmitEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setFieldErrors({});
    setFormError(null);
    const parsed = signupSchema.safeParse(fields);
    if (!parsed.success) {
      setFieldErrors(errorsFor(parsed.error));
      return;
    }
    setPending(true);
    try {
      await signup({
        email: parsed.data.email,
        password: parsed.data.password,
        username: parsed.data.username,
      });
      setSubmittedEmail(parsed.data.email);
    } catch (error) {
      setFormError(
        error instanceof Error
          ? error.message
          : "Could not create your account.",
      );
    } finally {
      setPending(false);
    }
  }

  async function resend(): Promise<void> {
    if (!submittedEmail) {
      return;
    }
    setResending(true);
    try {
      await resendConfirmation(submittedEmail);
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

  if (submittedEmail) {
    return (
      <>
        <h1 className="mb-3 text-xl font-semibold">Check your inbox</h1>
        <p className="text-sm leading-relaxed text-base-content/75">
          Confirm your email to activate your Kaziro account, then continue
          onboarding.
        </p>
        <button
          className="btn btn-primary mt-6 w-full"
          disabled={resending}
          onClick={resend}
          type="button"
        >
          {resending ? "Sending..." : "Resend confirmation email"}
        </button>
        <Link className="link mt-4 inline-block text-sm" href="/login">
          Back to log in
        </Link>
      </>
    );
  }

  return (
    <>
      <h1 className="mb-4 text-xl font-semibold">Create your account</h1>
      <form className="space-y-4" onSubmit={submit}>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Username</span>
          <input
            autoComplete="username"
            className={inputClass(Boolean(fieldErrors.username))}
            onChange={(event) =>
              setFields({ ...fields, username: event.target.value })
            }
            value={fields.username}
          />
          {fieldErrors.username ? (
            <span className="text-xs text-error">{fieldErrors.username}</span>
          ) : null}
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Email</span>
          <input
            autoComplete="email"
            className={inputClass(Boolean(fieldErrors.email))}
            onChange={(event) =>
              setFields({ ...fields, email: event.target.value })
            }
            type="email"
            value={fields.email}
          />
          {fieldErrors.email ? (
            <span className="text-xs text-error">{fieldErrors.email}</span>
          ) : null}
        </label>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Password</span>
          <input
            autoComplete="new-password"
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
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Confirm password</span>
          <input
            autoComplete="new-password"
            className={inputClass(Boolean(fieldErrors.confirm))}
            onChange={(event) =>
              setFields({ ...fields, confirm: event.target.value })
            }
            type="password"
            value={fields.confirm}
          />
          {fieldErrors.confirm ? (
            <span className="text-xs text-error">{fieldErrors.confirm}</span>
          ) : null}
        </label>
        {formError ? (
          <p className="text-sm text-error" role="alert">
            {formError}
          </p>
        ) : null}
        <button
          className="btn btn-primary h-11 w-full"
          disabled={pending}
          type="submit"
        >
          {pending ? "Creating..." : "Sign up"}
        </button>
      </form>
      <p className="mt-4 text-sm">
        <Link
          className="font-medium underline-offset-4 hover:underline"
          href="/login"
        >
          Already have an account?
        </Link>
      </p>
    </>
  );
}

function errorsFor(
  error: z.ZodError<SignupFields>,
): Partial<Record<keyof SignupFields, string>> {
  const next: Partial<Record<keyof SignupFields, string>> = {};
  for (const issue of error.issues) {
    const key = issue.path[0];
    if (
      key === "username" ||
      key === "email" ||
      key === "password" ||
      key === "confirm"
    ) {
      next[key] = issue.message;
    }
  }
  return next;
}
