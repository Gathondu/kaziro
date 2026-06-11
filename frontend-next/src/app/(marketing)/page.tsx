import Link from "next/link";
import { ArrowRight, BriefcaseBusiness } from "lucide-react";

export default function MarketingHome() {
  return (
    <main className="min-h-screen bg-base-100">
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col justify-center px-6 py-16">
        <div className="max-w-3xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-box border border-base-300 px-3 py-2 text-sm text-base-content/70">
            <BriefcaseBusiness className="size-4" aria-hidden="true" />
            Parallel Next.js migration scaffold
          </div>
          <h1 className="text-5xl font-semibold tracking-normal text-base-content sm:text-6xl">
            Kaziro
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-base-content/70">
            AI-powered job recommendations, fit evaluation, company research, and tailored
            application documents.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link className="btn btn-primary" href="/dashboard">
              Open dashboard
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>
            <Link className="btn btn-ghost" href="/login">
              Sign in
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
