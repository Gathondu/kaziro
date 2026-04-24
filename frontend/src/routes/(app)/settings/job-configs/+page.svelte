<script lang="ts">
	import { get } from 'svelte/store';
	import Button from '$lib/components/ui/Button.svelte';
	import { ApiError } from '$lib/api/errors';
	import { useDisableJobConfig, useJobConfigs, useRunJobConfigPipeline } from '$lib/hooks/useJobConfig';
	import { toast } from '$lib/stores/toast';

	const list = useJobConfigs(false);
	const disable = useDisableJobConfig();
	const runPipe = useRunJobConfigPipeline();

	let runTargetId = $state<string | null>(null);
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
					<div class="flex flex-wrap gap-2">
						<Button
							variant="outline"
							disabled={$runPipe.isPending || $disable.isPending}
							onclick={async () => {
								runTargetId = cfg.id;
								try {
									await get(runPipe).mutateAsync(cfg.id);
									toast.success('Pipeline run queued.');
								} catch (e) {
									toast.error(e instanceof ApiError ? e.message : 'Could not start run');
								} finally {
									runTargetId = null;
								}
							}}
						>
							{$runPipe.isPending && runTargetId === cfg.id ? 'Queuing…' : 'Run now'}
						</Button>
						<Button
							variant="outline"
							disabled={$disable.isPending || $runPipe.isPending}
							onclick={() => get(disable).mutateAsync(cfg.id)}
						>
							Disable
						</Button>
					</div>
				{/if}
			</li>
		{/each}
	</ul>
{/if}
