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

<div class="border-base-300 bg-base-100 rounded-2xl border p-5 shadow-sm" aria-live="polite">
	<h2 class="mb-3 text-base font-semibold">Recent activity</h2>
	{#if loading}
		<p class="text-base-content/60 text-sm">Loading…</p>
	{:else if error}
		<p class="text-error text-sm">{error}</p>
	{:else if items.length === 0}
		<p class="text-base-content/60 text-sm">No recent applications yet.</p>
	{:else}
		<ul class="space-y-2">
			{#each items as row (row.id)}
				<li class="bg-base-200 flex justify-between gap-3 rounded-xl px-3 py-2 text-sm">
					<span class="font-medium">{row.label}</span>
					<time class="text-base-content/60 shrink-0 text-xs" datetime={row.at}>
						{new Date(row.at).toLocaleString()}
					</time>
				</li>
			{/each}
		</ul>
	{/if}
</div>
