<script lang="ts">
	/** Light veil only — kept subtle so terracotta badges stay vivid on white cards */
	const sectionVeilClass =
		'pointer-events-none absolute inset-0 bg-[radial-gradient(95%_72%_at_50%_-8%,rgba(245,237,230,0.2)_0%,rgba(245,237,230,0.06)_38%,transparent_62%)]';

	/** BR diagonal (to-br) + restrained highlight so orange reads as the hero, not the gloss */
	const stepBadgeClass =
		'mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-primary via-[#c45f3f] to-primary-focus text-lg font-bold text-primary-content ' +
		'shadow-[inset_0_1px_0_rgba(255,255,255,0.12),inset_0_-12px_20px_-14px_rgba(48,26,18,0.28),0_10px_28px_-8px_rgba(201,106,74,0.55)]';
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
				class="rounded-2xl border border-base-content/20 bg-base-100 p-8 text-center shadow-lg ring-1 ring-base-content/10"
			>
				<span class={stepBadgeClass}>1</span>
				<h3 class="mb-2 text-lg font-bold text-base-content">Create your profile</h3>
				<p class="text-sm leading-relaxed text-base-content/90">
					Add your experience, skills, and job preferences so evaluations are grounded in you.
				</p>
			</div>
			<div
				class="rounded-2xl border border-base-content/20 bg-base-100 p-8 text-center shadow-lg ring-1 ring-base-content/10"
			>
				<span class={stepBadgeClass}>2</span>
				<h3 class="mb-2 text-lg font-bold text-base-content">Discover &amp; review</h3>
				<p class="text-sm leading-relaxed text-base-content/90">
					See surfaced roles with fit summaries and company context before you invest time.
				</p>
			</div>
			<div
				class="rounded-2xl border border-base-content/20 bg-base-100 p-8 text-center shadow-lg ring-1 ring-base-content/10"
			>
				<span class={stepBadgeClass}>3</span>
				<h3 class="mb-2 text-lg font-bold text-base-content">Apply with polish</h3>
				<p class="text-sm leading-relaxed text-base-content/90">
					Generate tailored documents when you are ready, then send with confidence.
				</p>
			</div>
		</div>
	</div>
</section>
