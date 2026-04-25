<script lang="ts">
	import JobConfigActions from '$lib/components/settings/JobConfigActions.svelte';
	import { useJobConfigs } from '$lib/hooks/useJobConfig';

	const list = useJobConfigs(false);
</script>

<svelte:head>
	<title>Job configs — Kaziro</title>
</svelte:head>

{#if $list.isPending}
	<p class="text-sm text-base-content/60">Loading…</p>
{:else if $list.isError}
	<p class="text-sm text-error">Could not load configs.</p>
{:else if $list.data}
	<ul class="space-y-3">
		{#each $list.data as cfg (cfg.id)}
			<li
				class="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-base-300 bg-base-100 p-4 shadow-sm"
			>
				<div>
					<p class="font-semibold">{cfg.name ?? 'Untitled'}</p>
					<p class="text-xs text-base-content/60">
						{(cfg.keywords ?? []).join(', ')} · {cfg.is_active ? 'Active' : 'Disabled'}
					</p>
				</div>
				{#if cfg.is_active}
					<JobConfigActions configId={cfg.id} />
				{/if}
			</li>
		{/each}
	</ul>
{/if}
