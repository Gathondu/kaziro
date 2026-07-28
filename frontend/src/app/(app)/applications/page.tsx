"use client";

import { useQuery } from "@tanstack/react-query";
import { Send } from "lucide-react";
import Link from "next/link";
import { listApplications } from "@/lib/api/applications";
import { useAuthStore } from "@/lib/stores/auth";

const columns = [
  ["draft", "Draft"],
  ["sent", "Sent"],
  ["interviewing", "Interviewing"],
  ["offered", "Offered"],
  ["rejected", "Rejected"],
  ["withdrawn", "Withdrawn"],
] as const;

export default function ApplicationsPage() {
  const token = useAuthStore((state) => state.token?.access_token ?? "");
  const applications = useQuery({
    queryKey: ["applications"],
    queryFn: () => listApplications(token),
    enabled: Boolean(token),
  });

  return (
    <main className="px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-7xl">
        <p className="text-sm font-medium text-primary">Application tracker</p>
        <h1 className="text-3xl font-semibold tracking-tight">Your board</h1>
        <p className="mt-1 text-base-content/65">
          Track every application from draft through offer.
        </p>
      </div>
      {applications.isPending ? (
        <div className="grid min-h-72 place-items-center">
          <span className="loading loading-spinner text-primary" />
        </div>
      ) : applications.isError ? (
        <div className="alert alert-error mx-auto mt-6 max-w-7xl">
          {applications.error.message}
        </div>
      ) : applications.data.length === 0 ? (
        <div className="mx-auto mt-8 max-w-2xl rounded-2xl border border-dashed border-base-300 bg-base-100 p-12 text-center">
          <Send className="mx-auto size-8 text-primary" />
          <h2 className="mt-3 font-semibold">Your board is empty</h2>
          <p className="mt-1 text-sm text-base-content/60">
            Open a good-fit job and prepare its application.
          </p>
          <Link className="btn btn-primary btn-sm mt-5" href="/jobs">
            Browse jobs
          </Link>
        </div>
      ) : (
        <section className="scroll-region mx-auto mt-7 flex max-w-full gap-4 overflow-x-auto pb-4">
          {columns.map(([status, label]) => {
            const items = applications.data.filter(
              (item) => item.status === status,
            );
            return (
              <div
                className="min-w-72 flex-1 rounded-2xl bg-base-300/45 p-3"
                key={status}
              >
                <div className="mb-3 flex items-center justify-between px-1">
                  <h2 className="text-sm font-semibold">{label}</h2>
                  <span className="badge badge-sm">{items.length}</span>
                </div>
                <div className="space-y-3">
                  {items.map((application) => (
                    <Link
                      className="block rounded-xl border border-base-300 bg-base-100 p-4 shadow-sm hover:border-primary"
                      href={`/applications/${application.id}`}
                      key={application.id}
                    >
                      <p className="font-semibold">
                        {application.job_posting.title}
                      </p>
                      <p className="mt-1 text-sm text-base-content/65">
                        {application.job_posting.company_name}
                      </p>
                      <div className="mt-3 flex justify-between text-xs text-base-content/55">
                        <span>
                          {application.evaluation.overall_score.toFixed(1)} fit
                        </span>
                        <span>
                          {new Date(
                            application.updated_at,
                          ).toLocaleDateString()}
                        </span>
                      </div>
                    </Link>
                  ))}
                  {items.length === 0 ? (
                    <p className="py-8 text-center text-xs text-base-content/45">
                      No applications
                    </p>
                  ) : null}
                </div>
              </div>
            );
          })}
        </section>
      )}
    </main>
  );
}
