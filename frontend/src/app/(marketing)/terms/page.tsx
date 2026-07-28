import Link from "next/link";

export default function TermsPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <Link className="text-xl font-bold text-primary" href="/">
        Kaziro
      </Link>
      <h1 className="mt-10 text-4xl font-semibold">Terms</h1>
      <div className="prose mt-8 max-w-none">
        <p>
          Kaziro assists with job discovery, evaluation, research, and
          preparation. You remain responsible for reviewing every application
          and deciding whether and where to submit it.
        </p>
        <h2>Generated content</h2>
        <p>
          AI-generated evaluations and documents can contain errors. Verify
          company claims, dates, qualifications, and application materials
          before use.
        </p>
        <h2>Acceptable use</h2>
        <p>
          Do not use Kaziro to access restricted systems, misrepresent
          qualifications, or violate job-site terms. Imported URLs must be
          lawful public HTTP or HTTPS resources.
        </p>
        <h2>Availability</h2>
        <p>
          Provider and public website availability can affect job fetching and
          research. Kaziro records failures where possible but cannot guarantee
          third-party availability.
        </p>
      </div>
    </main>
  );
}
