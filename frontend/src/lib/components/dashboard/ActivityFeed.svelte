<script lang="ts">
	const {
		items,
		loading,
		error
	}: {
		items: { id: string; label: string; at: string }[];
		loading: boolean;
		error: string | null;
	} = $props();
</script>

<div class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm" aria-live="polite">
	<h2 class="mb-3 text-base font-semibold">Recent activity</h2>
	{#if loading}
		<p class="text-sm text-base-content/60">Loading…</p>
	{:else if error}
		<p class="text-sm text-error">{error}</p>
	{:else if items.length === 0}
		<p class="text-sm text-base-content/60">No recent applications yet.</p>
	{:else}
		<ul class="space-y-2">
			{#each items as row (row.id)}
				<li class="flex justify-between gap-3 rounded-xl bg-base-200 px-3 py-2 text-sm">
					<span class="font-medium">{row.label}</span>
					<time class="shrink-0 text-xs text-base-content/60" datetime={row.at}>
						{new Date(row.at).toLocaleString()}
					</time>
				</li>
			{/each}
		</ul>
	{/if}
</div>
