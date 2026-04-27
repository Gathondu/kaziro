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
		<p class="mb-2 text-center text-xs font-semibold uppercase tracking-widest text-primary">
			Why Kaziro
		</p>
		<h2
			id="why-heading"
			class="mb-12 text-center text-3xl font-bold tracking-tight text-base-content sm:text-4xl"
		>
			A focused toolkit for serious applicants
		</h2>
		<div class="grid gap-6 lg:grid-cols-3">
			{#each reasons as item, i (item.title)}
				{@const Icon = item.icon}
				<div
					class="relative overflow-hidden rounded-2xl border border-base-content/20 bg-gradient-to-br from-base-100 to-base-200 p-8 shadow-md ring-1 ring-base-content/10"
				>
					<span
						class="text-primary/18 absolute right-6 top-6 text-5xl font-black leading-none"
						aria-hidden="true"
					>
						{String(i + 1).padStart(2, '0')}
					</span>
					<div
						class="relative mb-5 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/25 text-primary ring-1 ring-primary/40"
					>
						<Icon class="h-6 w-6" aria-hidden="true" />
					</div>
					<h3 class="relative mb-2 text-xl font-bold text-base-content">{item.title}</h3>
					<p class="relative text-sm leading-relaxed text-base-content/90">{item.body}</p>
				</div>
			{/each}
		</div>
	</div>
</section>
