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

<section class="mx-auto max-w-6xl px-4 py-16 sm:py-20" aria-labelledby="features-heading">
	<h2
		id="features-heading"
		class="mb-10 text-center text-2xl font-semibold text-base-content sm:text-3xl"
	>
		What Kaziro does for you
	</h2>
	<div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
		{#each features as item (item.title)}
			{@const Icon = item.icon}
			<div class="card border border-base-300/80 bg-base-100 shadow-sm">
				<div class="card-body gap-3 p-6">
					<div
						class="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary"
					>
						<Icon class="h-6 w-6" aria-hidden="true" />
					</div>
					<h3 class="card-title text-lg">{item.title}</h3>
					<p class="text-sm leading-relaxed text-base-content/75">{item.body}</p>
				</div>
			</div>
		{/each}
	</div>
</section>
