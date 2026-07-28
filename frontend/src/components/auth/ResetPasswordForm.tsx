"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { resetPassword } from "@/lib/api/auth";

export function ResetPasswordForm({ token }: { token: string }) {
  const [password, setPassword] = useState("");
  const reset = useMutation({
    mutationFn: () => resetPassword(token, password),
  });
  function submit(event: FormEvent): void {
    event.preventDefault();
    reset.mutate();
  }
  return (
    <main className="w-full max-w-md rounded-2xl border border-base-300 bg-base-100 p-7 shadow-marketing-card">
      <Link className="text-xl font-bold text-primary" href="/">
        Kaziro
      </Link>
      <h1 className="mt-6 text-2xl font-semibold">Choose a new password</h1>
      {!token ? (
        <div className="alert alert-error mt-5">
          This reset link is invalid.
        </div>
      ) : reset.isSuccess ? (
        <div className="mt-5">
          <div className="alert alert-success">{reset.data.message}</div>
          <Link className="btn btn-primary mt-4 w-full" href="/login">
            Sign in
          </Link>
        </div>
      ) : (
        <form className="mt-5" onSubmit={submit}>
          <label className="form-control">
            <span className="label-text mb-1">New password</span>
            <input
              className="input input-bordered"
              required
              minLength={8}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
            />
          </label>
          {reset.isError ? (
            <div className="alert alert-error mt-4">{reset.error.message}</div>
          ) : null}
          <button
            className="btn btn-primary mt-5 w-full"
            disabled={reset.isPending}
            type="submit"
          >
            Update password
          </button>
        </form>
      )}
    </main>
  );
}
