<script lang="ts">
	import JobConfigActions from '$lib/components/settings/JobConfigActions.svelte';
	import { useJobConfigs } from '$lib/hooks/useJobConfig';
	import type { JobConfig } from '$lib/types/jobConfig';

	const {
		onEdit
	}: {
		onEdit: (cfg: JobConfig) => void;
	} = $props();

	const list = useJobConfigs(false);
</script>

{#if $list.isPending}
	<p class="text-sm text-base-content/60">Loading…</p>
{:else if $list.isError}
	<p class="text-sm text-error">Could not load configs.</p>
{:else if $list.data}
	{#if $list.data.length === 0}
		<p class="text-sm text-base-content/60">
			You have no job search configs yet. Use <strong class="font-medium text-base-content"
				>Create config</strong
			> above to add your first one.
		</p>
	{:else}
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
					<JobConfigActions configId={cfg.id} isActive={cfg.is_active} onEdit={() => onEdit(cfg)} />
				</li>
			{/each}
		</ul>
	{/if}
{/if}
