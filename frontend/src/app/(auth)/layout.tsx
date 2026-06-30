import Link from "next/link";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-base-200 px-4 py-10">
      <section className="w-full max-w-md rounded-2xl border border-base-300 bg-base-100 p-6 shadow-sm">
        <Link
          className="mb-6 inline-block text-xl font-bold tracking-tight text-primary"
          href="/"
        >
          Kaziro
        </Link>
        {children}
      </section>
    </main>
  );
}
