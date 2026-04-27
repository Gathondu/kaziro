<script lang="ts">
	/**
	 * Theme-aware top fade only (uses `base-content` alpha). Avoids a fixed cream radial on dark
	 * mode, which sat on top of the step discs and read like a white haze.
	 */
	const sectionVeilClass =
		'pointer-events-none absolute inset-0 bg-gradient-to-b from-base-content/[0.06] via-transparent to-transparent';
</script>

<section
	class="relative border-y border-base-content/15 bg-base-200 px-4 py-16 sm:py-24"
	aria-labelledby="how-heading"
>
	<div class={sectionVeilClass} aria-hidden="true"></div>
	<div class="relative mx-auto max-w-5xl">
		<p class="mb-2 text-center text-xs font-semibold uppercase tracking-widest text-primary">
			Simple flow
		</p>
		<h2
			id="how-heading"
			class="mb-12 text-center text-3xl font-bold tracking-tight text-base-content sm:text-4xl"
		>
			Three steps to momentum
		</h2>
		<div class="grid gap-6 md:grid-cols-3">
			<div
				class="shadow-marketing-card rounded-2xl border border-base-content/20 bg-base-100 p-8 text-center ring-1 ring-base-content/10"
			>
				<span class="landing-step-disc mx-auto mb-4">1</span>
				<h3 class="mb-2 text-lg font-bold text-base-content">Create your profile</h3>
				<p class="text-sm leading-relaxed text-base-content/90">
					Add your experience, skills, and job preferences so evaluations are grounded in you.
				</p>
			</div>
			<div
				class="shadow-marketing-card rounded-2xl border border-base-content/20 bg-base-100 p-8 text-center ring-1 ring-base-content/10"
			>
				<span class="landing-step-disc mx-auto mb-4">2</span>
				<h3 class="mb-2 text-lg font-bold text-base-content">Discover &amp; review</h3>
				<p class="text-sm leading-relaxed text-base-content/90">
					See surfaced roles with fit summaries and company context before you invest time.
				</p>
			</div>
			<div
				class="shadow-marketing-card rounded-2xl border border-base-content/20 bg-base-100 p-8 text-center ring-1 ring-base-content/10"
			>
				<span class="landing-step-disc mx-auto mb-4">3</span>
				<h3 class="mb-2 text-lg font-bold text-base-content">Apply with polish</h3>
				<p class="text-sm leading-relaxed text-base-content/90">
					Generate tailored documents when you are ready, then send with confidence.
				</p>
			</div>
		</div>
	</div>
</section>
