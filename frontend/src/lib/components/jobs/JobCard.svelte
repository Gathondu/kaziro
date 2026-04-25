<script lang="ts">
	import Badge from '$lib/components/ui/Badge.svelte';
	import type { JobPosting } from '$lib/types/jobs';
	import type { Classification } from '$lib/types/enums';

	const {
		job,
		classification,
		detailHref = `/jobs/${job.id}`
	}: {
		job: JobPosting;
		classification?: Classification | null;
		detailHref?: string;
	} = $props();

	const badgeVariant = $derived(
		classification === 'GOOD_FIT'
			? 'success'
			: classification === 'MAYBE'
				? 'warning'
				: classification === 'REJECT'
					? 'error'
					: 'neutral'
	);
</script>

<a
	href={detailHref}
	class="group relative z-0 block overflow-hidden rounded-2xl bg-base-300 transition-transform duration-200 hover:z-20 hover:-translate-y-0.5 hover:scale-[1.01]"
>
	<span
		class="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl opacity-0 transition-opacity duration-300 group-hover:opacity-100"
	>
		<span
			class="absolute -inset-28 animate-spin blur-lg"
			style="background: conic-gradient(from 0deg, transparent 0deg, transparent 185deg, oklch(var(--p) / 0.72) 235deg, oklch(var(--p) / 1) 275deg, oklch(var(--s) / 1) 315deg, oklch(var(--a) / 1) 345deg, oklch(var(--a) / 0.72) 360deg); animation-duration: 3.4s;"
		></span>
		<span
			class="absolute -inset-24 animate-spin"
			style="background: conic-gradient(from 0deg, transparent 0deg, transparent 195deg, oklch(var(--p) / 0.8) 245deg, oklch(var(--p) / 1) 285deg, oklch(var(--s) / 1) 320deg, oklch(var(--a) / 1) 348deg, oklch(var(--a) / 0.8) 360deg); animation-duration: 3.4s;"
		></span>
	</span>
	<span
		class="relative z-10 block m-0.5 rounded-2xl border border-base-300 bg-base-100 p-4 shadow-sm transition-shadow duration-200 group-hover:shadow-md"
	>
		<div class="flex flex-wrap items-start justify-between gap-2">
			<div>
				<h3 class="font-semibold">{job.title}</h3>
				<p class="text-sm text-base-content/70">{job.company_name}</p>
			</div>
			{#if classification}
				<Badge variant={badgeVariant}>{classification}</Badge>
			{/if}
		</div>
		{#if job.location}
			<p class="mt-2 text-xs text-base-content/60">
				{job.location}{job.remote_flag ? ' · Remote' : ''}
			</p>
		{/if}
	</span>
</a>
