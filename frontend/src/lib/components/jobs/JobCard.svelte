<script lang="ts">
	import Badge from '$lib/components/ui/Badge.svelte';
	import type { JobPosting } from '$lib/types/jobs';
	import type { Classification } from '$lib/types/enums';

	const {
		job,
		classification
	}: {
		job: JobPosting;
		classification?: Classification | null;
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
	href="/jobs/{job.id}"
	class="block rounded-2xl border border-base-300 bg-base-100 p-4 shadow-sm transition-shadow hover:shadow-md"
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
</a>
