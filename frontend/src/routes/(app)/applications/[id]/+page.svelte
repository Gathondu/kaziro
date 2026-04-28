<script lang="ts">
	import StatusTimeline from '$lib/components/applications/StatusTimeline.svelte';
	import { useApplicationFromRoute } from '$lib/hooks/useApplication';

	const appQ = useApplicationFromRoute();
</script>

<svelte:head>
	<title>Application — Kaziro</title>
</svelte:head>

{#if $appQ.isPending}
	<p class="text-base-content/60 text-sm">Loading…</p>
{:else if $appQ.isError}
	<p class="text-error text-sm">Application not found.</p>
{:else if $appQ.data}
	<h1 class="mb-2 text-2xl font-semibold">{$appQ.data.job_posting?.title ?? 'Application'}</h1>
	<p class="text-base-content/70 mb-6 text-sm">Status: <strong>{$appQ.data.status}</strong></p>
	<section class="border-base-300 bg-base-100 rounded-2xl border p-5 shadow-sm">
		<h2 class="mb-3 text-base font-semibold">Timeline</h2>
		<StatusTimeline events={$appQ.data.events} />
	</section>
{/if}
