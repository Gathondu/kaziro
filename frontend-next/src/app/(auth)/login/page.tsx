import Link from "next/link";

export default function LoginPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-base-200 px-6 py-12">
      <section className="w-full max-w-sm rounded-box border border-base-300 bg-base-100 p-6 shadow-sm">
        <h1 className="text-2xl font-semibold">Sign in</h1>
        <p className="mt-2 text-sm text-base-content/70">
          Django-owned JWT auth will be wired in a later migration slice.
        </p>
        <form className="mt-6 space-y-4">
          <label className="form-control">
            <span className="label-text">Email</span>
            <input className="input input-bordered" name="email" type="email" />
          </label>
          <label className="form-control">
            <span className="label-text">Password</span>
            <input className="input input-bordered" name="password" type="password" />
          </label>
          <button className="btn btn-primary w-full" disabled type="button">
            Auth scaffold only
          </button>
        </form>
        <Link className="link mt-6 inline-block text-sm" href="/">
          Back to Kaziro
        </Link>
      </section>
    </main>
  );
}
