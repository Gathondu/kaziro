<script lang="ts">
	/**
	 * Theme-aware top fade only (uses `base-content` alpha). Avoids a fixed cream radial on dark
	 * mode, which sat on top of the step discs and read like a white haze.
	 */
	const sectionVeilClass =
		'pointer-events-none absolute inset-0 bg-gradient-to-b from-base-content/[0.06] via-transparent to-transparent';
</script>

<section
	class="border-base-content/15 bg-base-200 relative border-y px-4 py-16 sm:py-24"
	aria-labelledby="how-heading"
>
	<div class={sectionVeilClass} aria-hidden="true"></div>
	<div class="relative mx-auto max-w-5xl">
		<p class="text-primary mb-2 text-center text-xs font-semibold tracking-widest uppercase">
			Simple flow
		</p>
		<h2
			id="how-heading"
			class="text-base-content mb-12 text-center text-3xl font-bold tracking-tight sm:text-4xl"
		>
			Three steps to momentum
		</h2>
		<div class="grid gap-6 md:grid-cols-3">
			<div
				class="shadow-marketing-card border-base-content/20 bg-base-100 ring-base-content/10 rounded-2xl border p-8 text-center ring-1"
			>
				<span class="landing-step-disc mx-auto mb-4">1</span>
				<h3 class="text-base-content mb-2 text-lg font-bold">Create your profile</h3>
				<p class="text-base-content/90 text-sm leading-relaxed">
					Add your experience, skills, and job preferences so evaluations are grounded in you.
				</p>
			</div>
			<div
				class="shadow-marketing-card border-base-content/20 bg-base-100 ring-base-content/10 rounded-2xl border p-8 text-center ring-1"
			>
				<span class="landing-step-disc mx-auto mb-4">2</span>
				<h3 class="text-base-content mb-2 text-lg font-bold">Discover &amp; review</h3>
				<p class="text-base-content/90 text-sm leading-relaxed">
					See surfaced roles with fit summaries and company context before you invest time.
				</p>
			</div>
			<div
				class="shadow-marketing-card border-base-content/20 bg-base-100 ring-base-content/10 rounded-2xl border p-8 text-center ring-1"
			>
				<span class="landing-step-disc mx-auto mb-4">3</span>
				<h3 class="text-base-content mb-2 text-lg font-bold">Apply with polish</h3>
				<p class="text-base-content/90 text-sm leading-relaxed">
					Generate tailored documents when you are ready, then send with confidence.
				</p>
			</div>
		</div>
	</div>
</section>
