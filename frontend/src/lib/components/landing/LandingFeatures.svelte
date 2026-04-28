<script lang="ts">
	import { Briefcase, Building2, FileText, Sparkles } from 'lucide-svelte';

	const features = [
		{
			icon: Briefcase,
			title: 'Fresh roles on your radar',
			body: 'Jobs surface from your search preferences so you are not endlessly refreshing the same boards.'
		},
		{
			icon: Sparkles,
			title: 'Clear fit, not guesswork',
			body: 'Each posting gets a structured evaluation against your profile so you can prioritise with confidence.'
		},
		{
			icon: Building2,
			title: 'Company context in one place',
			body: 'Brief research on the employer helps you tailor tone and talk credibly in interviews and letters.'
		},
		{
			icon: FileText,
			title: 'Documents that match the brief',
			body: 'Draft a tailored CV and cover letter aligned to the posting, then refine before you apply.'
		}
	] as const;
</script>

<section class="relative px-4 py-16 sm:py-24" aria-labelledby="features-heading">
	<div
		class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent"
		aria-hidden="true"
	></div>
	<div class="relative mx-auto max-w-6xl">
		<p class="mb-2 text-center text-xs font-semibold uppercase tracking-widest text-primary">
			What you get
		</p>
		<h2
			id="features-heading"
			class="mb-12 text-center text-3xl font-bold tracking-tight text-base-content sm:text-4xl"
		>
			Built around your search
		</h2>
		<div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
			{#each features as item (item.title)}
				{@const Icon = item.icon}
				<div
					class="shadow-marketing-card group relative overflow-hidden rounded-2xl border border-base-content/10 bg-gradient-to-br from-base-100 via-base-100 to-base-200/80 p-6 ring-1 ring-base-content/5 transition motion-safe:hover:-translate-y-1"
				>
					<div
						class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent opacity-0 transition group-hover:opacity-100 motion-reduce:group-hover:opacity-0"
						aria-hidden="true"
					></div>
					<div class="landing-icon-well mb-4">
						<Icon class="h-7 w-7" aria-hidden="true" />
					</div>
					<h3 class="mb-2 text-lg font-bold text-base-content">{item.title}</h3>
					<p class="text-sm leading-relaxed text-base-content/90">{item.body}</p>
				</div>
			{/each}
		</div>
	</div>
</section>
