import { Activity, FileText, SearchCheck } from "lucide-react";

const metrics = [
  { label: "Tracked jobs", value: "0", icon: SearchCheck },
  { label: "Applications", value: "0", icon: FileText },
  { label: "Pipeline events", value: "0", icon: Activity },
];

export default function DashboardPage() {
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold">Dashboard</h1>
        <p className="mt-2 text-base-content/70">
          Placeholder shell for the Next.js app migration.
        </p>
      </div>
      <section className="grid gap-4 md:grid-cols-3">
        {metrics.map((metric) => (
          <article
            className="rounded-box border border-base-300 bg-base-100 p-5 shadow-sm"
            key={metric.label}
          >
            <metric.icon className="mb-4 size-5 text-primary" aria-hidden="true" />
            <p className="text-sm text-base-content/60">{metric.label}</p>
            <p className="mt-1 text-3xl font-semibold">{metric.value}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
