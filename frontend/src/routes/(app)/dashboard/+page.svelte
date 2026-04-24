<script lang="ts">
	import ActivityFeed from '$lib/components/dashboard/ActivityFeed.svelte';
	import KpiTile from '$lib/components/dashboard/KpiTile.svelte';
	import { useDashboard } from '$lib/hooks/useDashboard';

	const dashboard = useDashboard();
</script>

<svelte:head>
	<title>Dashboard — Kaziro</title>
</svelte:head>

{#if $dashboard.isPending}
	<p class="text-sm text-base-content/60" aria-live="polite">Loading dashboard…</p>
{:else if $dashboard.isError}
	<p class="text-sm text-error">Could not load dashboard.</p>
{:else if $dashboard.data}
	<div class="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
		<KpiTile
			label="Jobs (sample)"
			value={$dashboard.data.jobsSample}
			hint="Up to 100 in this window"
		/>
		<KpiTile label="Good fits (sample)" value={$dashboard.data.goodFitSample} />
		<KpiTile label="Applications (sample)" value={$dashboard.data.applicationsTotalSample} />
		<KpiTile label="Sent" value={$dashboard.data.sentCount} />
	</div>
	<ActivityFeed items={$dashboard.data.recent} loading={false} error={null} />
{/if}
