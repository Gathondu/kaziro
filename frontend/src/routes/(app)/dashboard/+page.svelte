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
	<p class="text-base-content/60 text-sm" aria-live="polite">Loading dashboard…</p>
{:else if $dashboard.isError}
	<p class="text-error text-sm">Could not load dashboard.</p>
{:else if $dashboard.data}
	<div class="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
		<KpiTile label="Jobs" value={$dashboard.data.jobsTotal} href="/jobs" />
		<KpiTile
			label="Good fits"
			value={$dashboard.data.goodFitUninteracted}
			href="/jobs?fit=GOOD_FIT"
		/>
		<KpiTile label="Applications" value={$dashboard.data.applicationsDraft} href="/applications" />
		<KpiTile label="Sent" value={$dashboard.data.sentCount} href="/dashboard" />
	</div>
	<ActivityFeed items={$dashboard.data.recent} loading={false} error={null} />
{/if}
