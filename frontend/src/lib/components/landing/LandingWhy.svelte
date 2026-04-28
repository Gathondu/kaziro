<script lang="ts">
	import { Shield, Sparkles, Zap } from 'lucide-svelte';

	const reasons = [
		{
			icon: Shield,
			title: 'Scoped to you',
			body: 'Your data and evaluations stay tied to your account — structured signals, not a black box.'
		},
		{
			icon: Zap,
			title: 'Pipeline in the background',
			body: 'Fetching and analysis run asynchronously so the UI stays responsive while work completes.'
		},
		{
			icon: Sparkles,
			title: 'Honest fit framing',
			body: 'Clear summaries help you spend energy on roles that actually align with your goals.'
		}
	] as const;
</script>

<section class="relative px-4 py-16 sm:py-24" aria-labelledby="why-heading">
	<div class="mx-auto max-w-6xl">
		<p class="text-primary mb-2 text-center text-xs font-semibold tracking-widest uppercase">
			Why Kaziro
		</p>
		<h2
			id="why-heading"
			class="text-base-content mb-12 text-center text-3xl font-bold tracking-tight sm:text-4xl"
		>
			A focused toolkit for serious applicants
		</h2>
		<div class="grid gap-6 lg:grid-cols-3">
			{#each reasons as item, i (item.title)}
				{@const Icon = item.icon}
				<div
					class="shadow-marketing-card border-base-content/20 from-base-100 to-base-200 ring-base-content/10 relative overflow-hidden rounded-2xl border bg-gradient-to-br p-8 ring-1"
				>
					<span
						class="text-primary/18 absolute top-6 right-6 text-5xl leading-none font-black"
						aria-hidden="true"
					>
						{String(i + 1).padStart(2, '0')}
					</span>
					<div class="landing-icon-well landing-icon-well--sm relative mb-5">
						<Icon class="h-6 w-6" aria-hidden="true" />
					</div>
					<h3 class="text-base-content relative mb-2 text-xl font-bold">{item.title}</h3>
					<p class="text-base-content/90 relative text-sm leading-relaxed">{item.body}</p>
				</div>
			{/each}
		</div>
	</div>
</section>
