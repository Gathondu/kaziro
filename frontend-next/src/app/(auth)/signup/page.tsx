import Link from "next/link";

export default function SignupPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-base-200 px-6 py-12">
      <section className="w-full max-w-sm rounded-box border border-base-300 bg-base-100 p-6 shadow-sm">
        <h1 className="text-2xl font-semibold">Create account</h1>
        <p className="mt-2 text-sm text-base-content/70">
          Account creation will move here when the Django auth slice lands.
        </p>
        <Link className="btn btn-primary mt-6 w-full" href="/login">
          Continue to sign in
        </Link>
      </section>
    </main>
  );
}
