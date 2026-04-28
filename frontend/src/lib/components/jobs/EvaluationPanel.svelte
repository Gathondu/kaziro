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

	type ProgressTone = 'success' | 'warning' | 'error';

	type ScoreBar = {
		id: string;
		label: string;
		raw: number;
		normalized: number;
		tone: ProgressTone;
	};

	type ScoreGroup = {
		id: string;
		label: string;
		bars: ScoreBar[];
	};

	function titleize(value: string): string {
		return value.replaceAll('_', ' ').replace(/\b\w/g, (match) => match.toUpperCase());
	}

	function parseNumericEntries(value: unknown): [string, number][] {
		if (!value || typeof value !== 'object' || Array.isArray(value)) {
			return [];
		}
		return Object.entries(value).flatMap(([key, raw]) => {
			if (typeof raw !== 'number' || !Number.isFinite(raw)) {
				return [];
			}
			return [[key, raw] as [string, number]];
		});
	}

	function normalizeScore(value: number): number {
		const scaled = value <= 1 ? value * 10 : value;
		return Math.max(0, Math.min(10, scaled));
	}

	function toneFor(normalized: number): ProgressTone {
		if (normalized >= 8) return 'success';
		if (normalized >= 6) return 'warning';
		return 'error';
	}

	function progressClass(tone: ProgressTone): string {
		return tone === 'success'
			? 'progress-success'
			: tone === 'warning'
				? 'progress-warning'
				: 'progress-error';
	}

	function toBars(entries: [string, number][], groupId: string): ScoreBar[] {
		return entries.map(([metric, raw]) => {
			const normalized = normalizeScore(raw);
			return {
				id: `${groupId}-${metric}`,
				label: titleize(metric),
				raw,
				normalized,
				tone: toneFor(normalized)
			};
		});
	}

	function buildScoreGroups(scores: Record<string, unknown>): ScoreGroup[] {
		const groups: ScoreGroup[] = [];
		const topLevel = Object.entries(scores);
		const directNumeric = topLevel.flatMap(([key, raw]) =>
			typeof raw === 'number' && Number.isFinite(raw) ? [[key, raw] as [string, number]] : []
		);
		if (directNumeric.length > 0) {
			groups.push({
				id: 'scores',
				label: 'Scores',
				bars: toBars(directNumeric, 'scores')
			});
		}
		for (const [groupKey, raw] of topLevel) {
			const nested = parseNumericEntries(raw);
			if (nested.length === 0) continue;
			groups.push({
				id: groupKey,
				label: titleize(groupKey),
				bars: toBars(nested, groupKey)
			});
		}
		return groups;
	}

	const scoreGroups = $derived(buildScoreGroups(evaluation.dimension_scores));
</script>

<section
	class="border-base-300 bg-base-100 space-y-4 rounded-2xl border p-5 shadow-sm"
	aria-label="Evaluation"
>
	<div class="flex flex-wrap items-center justify-between gap-2">
		<h2 class="text-lg font-semibold">Why this match</h2>
		<Badge variant={badgeVariant}>
			{#if evaluation.final_classification === 'REJECT' && evaluation.rejection_source === 'user'}
				Rejected (by you)
			{:else}
				{evaluation.final_classification}
			{/if}
		</Badge>
	</div>
	<p class="text-base-content/70 text-sm">
		Overall score: <span class="font-semibold tabular-nums"
			>{evaluation.overall_score.toFixed(2)}</span
		>
	</p>
	<div>
		<h3 class="mb-2 text-sm font-semibold">Dimension scores</h3>
		{#if scoreGroups.length === 0}
			<p class="bg-base-200 text-base-content/70 rounded-xl p-3 text-sm">
				No dimension scores yet.
			</p>
		{:else}
			<div class="grid gap-2 sm:grid-cols-2">
				{#each scoreGroups as group (group.id)}
					<div class="bg-base-200 rounded-xl p-3 text-sm">
						<p class="text-base-content/80 mb-2 font-semibold">{group.label}</p>
						<ul class="space-y-2">
							{#each group.bars as bar (bar.id)}
								<li>
									<div class="mb-1 flex items-center justify-between gap-2">
										<span class="truncate font-medium">{bar.label}</span>
										<span class="text-base-content/80 shrink-0 tabular-nums">{bar.raw}</span>
									</div>
									<progress
										class="progress h-1.5 w-full {progressClass(bar.tone)}"
										value={bar.normalized}
										max="10"
										aria-label="{bar.label} score {bar.raw}"
									></progress>
								</li>
							{/each}
						</ul>
					</div>
				{/each}
			</div>
		{/if}
	</div>
	<div>
		<h3 class="mb-2 text-sm font-semibold">Judge rationale</h3>
		<p class="bg-base-200 rounded-xl p-3 text-sm leading-relaxed">{evaluation.final_feedback}</p>
	</div>
</section>
