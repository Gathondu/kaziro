import Link from "next/link";

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <Link className="text-xl font-bold text-primary" href="/">
        Kaziro
      </Link>
      <h1 className="mt-10 text-4xl font-semibold">Privacy</h1>
      <div className="prose mt-8 max-w-none">
        <p>
          Kaziro processes the profile, CV, job, and application information you
          provide to evaluate roles and prepare application materials.
        </p>
        <h2>How information is used</h2>
        <p>
          Your data is used to provide your private workspace, match roles,
          research employers from public sources, generate documents, and notify
          you about processing outcomes. User-owned records are isolated by
          account.
        </p>
        <h2>Company research</h2>
        <p>
          Company research is collected from public websites through the
          dedicated Scrapper service. Source evidence and retrieval details are
          retained so generated summaries can be verified.
        </p>
        <h2>Your choices</h2>
        <p>
          You can update your profile, replace your CV, delete applications, or
          disable your account from Settings.
        </p>
      </div>
    </main>
  );
}
