"use client";

import { useMutation } from "@tanstack/react-query";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { forgotPassword } from "@/lib/api/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const request = useMutation({ mutationFn: () => forgotPassword(email) });
  function submit(event: FormEvent): void {
    event.preventDefault();
    request.mutate();
  }
  return (
    <main className="w-full max-w-md rounded-2xl border border-base-300 bg-base-100 p-7 shadow-marketing-card">
      <Link className="text-xl font-bold text-primary" href="/">
        Kaziro
      </Link>
      <h1 className="mt-6 text-2xl font-semibold">Reset your password</h1>
      <p className="mt-2 text-sm text-base-content/65">
        We’ll email you a secure reset link if the account exists.
      </p>
      {request.isSuccess ? (
        <div className="alert alert-success mt-5" role="status">
          {request.data.message}
        </div>
      ) : (
        <form className="mt-5" onSubmit={submit}>
          <label className="form-control">
            <span className="label-text mb-1">Email address</span>
            <input
              className="input input-bordered"
              required
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
            />
          </label>
          {request.isError ? (
            <div className="alert alert-error mt-4" role="alert">
              {request.error.message}
            </div>
          ) : null}
          <button
            className="btn btn-primary mt-5 w-full"
            disabled={request.isPending}
            type="submit"
          >
            {request.isPending ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
      <Link
        className="link link-primary mt-5 block text-center text-sm"
        href="/login"
      >
        Back to sign in
      </Link>
    </main>
  );
}
