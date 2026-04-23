<script lang="ts">
	import StatusTimeline from '$lib/components/applications/StatusTimeline.svelte';
	import { useApplicationFromRoute } from '$lib/hooks/useApplication';

	const appQ = useApplicationFromRoute();
</script>

<svelte:head>
	<title>Application — Kaziro</title>
</svelte:head>

{#if $appQ.isPending}
	<p class="text-sm text-base-content/60">Loading…</p>
{:else if $appQ.isError}
	<p class="text-sm text-error">Application not found.</p>
{:else if $appQ.data}
	<h1 class="mb-2 text-2xl font-semibold">{$appQ.data.job_posting?.title ?? 'Application'}</h1>
	<p class="mb-6 text-sm text-base-content/70">Status: <strong>{$appQ.data.status}</strong></p>
	<section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
		<h2 class="mb-3 text-base font-semibold">Timeline</h2>
		<StatusTimeline events={$appQ.data.events} />
	</section>
{/if}
