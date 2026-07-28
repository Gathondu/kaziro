"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bell,
  BriefcaseBusiness,
  UserRoundCheck,
} from "lucide-react";
import { listJobs } from "@/lib/api/jobs";
import { listApplications } from "@/lib/api/applications";
import { listNotifications } from "@/lib/api/notifications";
import { getProfile } from "@/lib/api/profile";
import { useAuthStore } from "@/lib/stores/auth";

export default function DashboardPage() {
  const token = useAuthStore((state) => state.token?.access_token ?? null);
  const user = useAuthStore((state) => state.user);
  const notifications = useQuery({
    queryKey: ["notifications", "all"],
    queryFn: () => listNotifications(token ?? "", false),
    enabled: Boolean(token),
  });
  const profile = useQuery({
    queryKey: ["profile"],
    queryFn: () => getProfile(token ?? ""),
    enabled: Boolean(token),
    retry: 1,
  });
  const jobs = useQuery({
    queryKey: ["jobs", "dashboard"],
    queryFn: () => listJobs(token ?? ""),
    enabled: Boolean(token),
  });
  const applications = useQuery({
    queryKey: ["applications"],
    queryFn: () => listApplications(token ?? ""),
    enabled: Boolean(token),
  });

  const metrics = [
    {
      label: "Good-fit jobs",
      value:
        jobs.data?.filter(
          (job) => job.evaluation?.final_classification === "GOOD_FIT",
        ).length ?? 0,
      icon: BriefcaseBusiness,
    },
    {
      label: "Unread updates",
      value: notifications.data?.unread_count ?? 0,
      icon: Bell,
    },
    {
      label: "Applications",
      value: applications.data?.length ?? 0,
      icon: Activity,
    },
    {
      label: "Profile",
      value: profile.data ? "Ready" : "Pending",
      icon: UserRoundCheck,
    },
  ];
  const recent = notifications.data?.items.slice(0, 5) ?? [];

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <div className="mb-8">
        <p className="text-sm font-medium text-primary">Welcome back</p>
        <h1 className="mt-1 text-3xl font-semibold uppercase tracking-tight">
          {user?.username || "Kaziro dashboard"}
        </h1>
        <p className="mt-2 text-base-content/70">
          Your profile, job searches, and notification stream are synced with
          the Django backend.
        </p>
      </div>
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <article
            className="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-marketing-card"
            key={metric.label}
          >
            <metric.icon
              className="mb-4 size-5 text-primary"
              aria-hidden="true"
            />
            <p className="text-sm text-base-content/60">{metric.label}</p>
            <p className="mt-1 text-3xl font-semibold">{metric.value}</p>
          </article>
        ))}
      </section>
      <section className="mt-8 rounded-2xl border border-base-300 bg-base-100 p-5 shadow-marketing-card">
        <div className="mb-4 flex items-center gap-2">
          <Activity className="size-5 text-primary" aria-hidden="true" />
          <h2 className="font-semibold">Recent activity</h2>
        </div>
        {notifications.isPending ? (
          <p className="text-sm text-base-content/60" aria-live="polite">
            Loading activity...
          </p>
        ) : recent.length > 0 ? (
          <div className="space-y-3">
            {recent.map((item) => (
              <article className="rounded-xl bg-base-200 p-3" key={item.id}>
                <p className="text-sm font-semibold">{item.title}</p>
                <p className="mt-1 text-sm text-base-content/70">{item.body}</p>
              </article>
            ))}
          </div>
        ) : (
          <p className="text-sm text-base-content/60">
            No activity yet. Your first job search will add updates here.
          </p>
        )}
      </section>
    </main>
  );
}
