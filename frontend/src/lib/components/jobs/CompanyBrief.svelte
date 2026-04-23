<script lang="ts">
	import type { JobPosting } from '$lib/types/jobs';

	const { job }: { job: JobPosting } = $props();

	const excerpt = $derived(
		job.description.length > 600 ? `${job.description.slice(0, 600)}…` : job.description
	);
</script>

<section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm" aria-label="Company">
	<h2 class="mb-3 text-lg font-semibold">About the company</h2>
	<p class="text-base font-medium">{job.company_name}</p>
	{#if job.company_website}
		<a
			class="link link-primary text-sm font-medium"
			href={job.company_website}
			target="_blank"
			rel="noreferrer">{job.company_website}</a
		>
	{/if}
	<p class="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-base-content/80">{excerpt}</p>
	<p class="mt-3 text-xs text-base-content/50">
		Structured research briefs appear after the research stage runs; this panel always shows the job
		posting context.
	</p>
</section>
