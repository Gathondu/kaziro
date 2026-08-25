import Link from "next/link";
import {
  ArrowRight,
  Briefcase,
  Building2,
  FileText,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";

const features = [
  {
    icon: Briefcase,
    title: "Fresh roles on your radar",
    body: "Jobs surface from your search preferences so you are not endlessly refreshing the same boards.",
  },
  {
    icon: Sparkles,
    title: "Clear fit, not guesswork",
    body: "Each posting gets a structured evaluation against your profile so you can prioritise with confidence.",
  },
  {
    icon: Building2,
    title: "Company context in one place",
    body: "Brief research on the employer helps you tailor tone and talk credibly in interviews and letters.",
  },
  {
    icon: FileText,
    title: "Documents that match the brief",
    body: "Draft a tailored CV and cover letter aligned to the posting, then refine before you apply.",
  },
] as const;

const reasons = [
  {
    icon: Shield,
    title: "Scoped to you",
    body: "Your data and evaluations stay tied to your account with structured signals, not a black box.",
  },
  {
    icon: Zap,
    title: "Pipeline in the background",
    body: "Fetching and analysis run asynchronously so the interface stays responsive while work completes.",
  },
  {
    icon: Sparkles,
    title: "Honest fit framing",
    body: "Clear summaries help you spend energy on roles that actually align with your goals.",
  },
] as const;

export default function MarketingHome() {
  return (
    <div
      className="flex min-h-screen flex-col bg-base-100"
      data-marketing-surface
    >
      <Header />
      <main className="flex-1">
        <section className="border-b border-base-content/15 px-4 py-16 sm:py-24 lg:py-28">
          <div className="mx-auto max-w-6xl">
            <p className="mb-5 text-center text-xs font-semibold uppercase tracking-widest text-primary sm:text-sm">
              AI-assisted job search
            </p>
            <div className="shadow-marketing-hero mx-auto max-w-280 rounded-3xl border border-base-content/20 bg-base-100/75 px-6 py-14 text-center backdrop-blur-sm sm:px-12 sm:py-16 lg:px-20">
              <h1 className="text-5xl font-extralight tracking-tight text-base-content sm:text-6xl lg:text-7xl">
                Find your next role with
                <span className="block">
                  <span className="marketing-hero-clarity-word inline-block text-primary">
                    clarity
                  </span>
                </span>
              </h1>
              <p className="mx-auto mt-10 max-w-5xl text-lg leading-relaxed text-base-content/90 sm:text-xl">
                Kaziro surfaces roles that fit your profile, explains the match,
                adds company context, and helps you ship tailored applications —
                less noise, more momentum.
              </p>
              <div className="mx-auto mt-8 flex max-w-5xl flex-wrap justify-center gap-3 border-t border-base-content/10 pt-5">
                <Link className="landing-cta-primary" href="/signup">
                  Create account
                  <ArrowRight className="ml-2 size-4" aria-hidden="true" />
                </Link>
                <Link
                  className="btn rounded-2xl border-base-content/30 bg-base-100 px-8"
                  href="/login"
                >
                  Log in
                </Link>
              </div>
            </div>
          </div>
        </section>
        <FeatureSection />
        <WhySection />
        <HowItWorks />
      </main>
      <Footer />
    </div>
  );
}

function Header() {
  return (
    <header className="shadow-marketing-header sticky top-0 z-50 border-b border-base-content/15 bg-base-100/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-350 items-center justify-between gap-4 px-4 py-4">
        <Link
          className="text-xl font-bold tracking-tight text-primary"
          href="/"
        >
          Kaziro
        </Link>
        <nav className="flex flex-wrap items-center gap-2" aria-label="Main">
          <Link
            className="btn btn-ghost btn-sm rounded-xl font-medium"
            href="/login"
          >
            Log in
          </Link>
          <Link
            className="landing-cta-primary landing-cta-primary--sm font-medium"
            href="/signup"
          >
            Create account
          </Link>
        </nav>
      </div>
    </header>
  );
}

function FeatureSection() {
  return (
    <section
      className="relative px-4 py-16 sm:py-24"
      aria-labelledby="features-heading"
    >
      <div className="relative mx-auto max-w-6xl">
        <p className="mb-2 text-center text-xs font-semibold uppercase tracking-widest text-primary">
          What you get
        </p>
        <h2
          id="features-heading"
          className="mb-12 text-center text-3xl font-bold tracking-normal text-base-content sm:text-4xl"
        >
          Built around your search
        </h2>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((item) => (
            <article
              className="shadow-marketing-card group relative overflow-hidden rounded-2xl border border-base-content/10 bg-linear-to-br from-base-100 via-base-100 to-base-200/80 p-6 ring-1 ring-base-content/5 transition motion-safe:hover:-translate-y-1"
              key={item.title}
            >
              <div className="landing-icon-well mb-4">
                <item.icon className="size-7" aria-hidden="true" />
              </div>
              <h3 className="mb-2 text-lg font-bold text-base-content">
                {item.title}
              </h3>
              <p className="text-sm leading-relaxed text-base-content/90">
                {item.body}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function WhySection() {
  return (
    <section
      className="relative px-4 py-16 sm:py-24"
      aria-labelledby="why-heading"
    >
      <div className="mx-auto max-w-6xl">
        <p className="mb-2 text-center text-xs font-semibold uppercase tracking-widest text-primary">
          Why Kaziro
        </p>
        <h2
          id="why-heading"
          className="mb-12 text-center text-3xl font-bold tracking-normal text-base-content sm:text-4xl"
        >
          A focused toolkit for serious applicants
        </h2>
        <div className="grid gap-6 lg:grid-cols-3">
          {reasons.map((item, index) => (
            <article
              className="shadow-marketing-card relative overflow-hidden rounded-2xl border border-base-content/20 bg-linear-to-br from-base-100 to-base-200 p-8 ring-1 ring-base-content/10"
              key={item.title}
            >
              <span
                className="absolute right-6 top-6 text-5xl font-black leading-none text-info/20"
                aria-hidden="true"
              >
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="landing-icon-well landing-icon-well--sm relative mb-5">
                <item.icon className="size-6" aria-hidden="true" />
              </div>
              <h3 className="relative mb-2 text-xl font-bold text-base-content">
                {item.title}
              </h3>
              <p className="relative text-sm leading-relaxed text-base-content/90">
                {item.body}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <section
      className="relative border-y border-base-content/15 bg-base-200 px-4 py-16 sm:py-24"
      aria-labelledby="how-heading"
    >
      <div className="relative mx-auto max-w-5xl">
        <p className="mb-2 text-center text-xs font-semibold uppercase tracking-widest text-primary">
          Simple flow
        </p>
        <h2
          id="how-heading"
          className="mb-12 text-center text-3xl font-bold tracking-normal text-base-content sm:text-4xl"
        >
          Three steps to momentum
        </h2>
        <div className="grid gap-6 md:grid-cols-3">
          {[
            [
              "1",
              "Create your profile",
              "Add your experience, skills, and job preferences.",
            ],
            [
              "2",
              "Discover and review",
              "See surfaced roles with fit summaries and context.",
            ],
            [
              "3",
              "Apply with polish",
              "Generate tailored documents when you are ready.",
            ],
          ].map(([step, title, body]) => (
            <article
              className="shadow-marketing-card rounded-2xl border border-base-content/20 bg-base-100 p-8 text-center ring-1 ring-base-content/10"
              key={step}
            >
              <span className="landing-step-disc mx-auto mb-4">{step}</span>
              <h3 className="mb-2 text-lg font-bold text-base-content">
                {title}
              </h3>
              <p className="text-sm leading-relaxed text-base-content/90">
                {body}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-base-content/20 bg-linear-to-b from-base-200 to-base-300/40 px-4 py-12">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-base-content">Kaziro</p>
          <p className="mt-1 text-sm text-base-content/85">
            © {year} Kaziro. All rights reserved.
          </p>
        </div>
        <nav
          className="flex flex-wrap gap-x-8 gap-y-2 text-sm font-medium"
          aria-label="Footer"
        >
          <Link className="link-hover link text-base-content" href="/login">
            Log in
          </Link>
          <Link className="link-hover link text-primary" href="/signup">
            Create account
          </Link>
        </nav>
      </div>
    </footer>
  );
}
