<script lang="ts">
	import Badge from '$lib/components/ui/Badge.svelte';
	import type { JobEvaluation } from '$lib/types/jobs';

	const { evaluation }: { evaluation: JobEvaluation } = $props();

	const badgeVariant = $derived(
		evaluation.final_classification === 'GOOD_FIT'
			? 'success'
			: evaluation.final_classification === 'MAYBE'
				? 'warning'
				: 'error'
	);

	function formatDimensions(scores: Record<string, unknown>): [string, string][] {
		return Object.entries(scores).map(([k, v]) => [
			k,
			typeof v === 'object' ? JSON.stringify(v) : String(v)
		]);
	}
</script>

<section
	class="space-y-4 rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm"
	aria-label="Evaluation"
>
	<div class="flex flex-wrap items-center justify-between gap-2">
		<h2 class="text-lg font-semibold">Why this match</h2>
		<Badge variant={badgeVariant}>{evaluation.final_classification}</Badge>
	</div>
	<p class="text-sm text-base-content/70">
		Overall score: <span class="font-semibold tabular-nums"
			>{evaluation.overall_score.toFixed(2)}</span
		>
	</p>
	<div>
		<h3 class="mb-2 text-sm font-semibold">Dimension scores</h3>
		<ul class="space-y-1 rounded-xl bg-base-200 p-3 text-sm">
			{#each formatDimensions(evaluation.dimension_scores) as [key, val] (key)}
				<li class="flex justify-between gap-2">
					<span class="font-medium capitalize">{key.replaceAll('_', ' ')}</span>
					<span class="text-right text-base-content/80">{val}</span>
				</li>
			{/each}
		</ul>
	</div>
	<div>
		<h3 class="mb-2 text-sm font-semibold">Judge rationale</h3>
		<p class="rounded-xl bg-base-200 p-3 text-sm leading-relaxed">{evaluation.final_feedback}</p>
	</div>
</section>
