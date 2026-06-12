export function OnboardingStepFrame({
  children,
  description,
  title,
}: {
  children: React.ReactNode;
  description: string;
  title: string;
}) {
  return (
    <section className="rounded-2xl border border-base-300 bg-base-100 p-6 shadow-marketing-card">
      <h1 className="mb-2 text-xl font-semibold">{title}</h1>
      <p className="mb-6 text-sm leading-relaxed text-base-content/70">{description}</p>
      {children}
    </section>
  );
}
