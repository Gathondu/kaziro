<script lang="ts">
	import { get } from 'svelte/store';
	import Button from '$lib/components/ui/Button.svelte';
	import { ApiError } from '$lib/api/errors';
	import {
		useDisableJobConfig,
		useRunJobConfigPipeline,
		useUpdateJobConfig
	} from '$lib/hooks/useJobConfig';
	import { toast } from '$lib/stores/toast';

	const {
		configId,
		isActive,
		onEdit
	}: {
		configId: string;
		isActive: boolean;
		onEdit: () => void;
	} = $props();

	const disable = useDisableJobConfig();
	const updateCfg = useUpdateJobConfig();
	const runPipe = useRunJobConfigPipeline();
</script>

<div class="flex flex-wrap gap-2">
	{#if isActive}
		<Button
			variant="outline"
			disabled={$runPipe.isPending || $disable.isPending || $updateCfg.isPending}
			onclick={async () => {
				try {
					await get(runPipe).mutateAsync(configId);
					toast.success('Pipeline run queued.');
				} catch (e) {
					toast.error(e instanceof ApiError ? e.message : 'Could not start run');
				}
			}}
		>
			{$runPipe.isPending ? 'Queuing…' : 'Run now'}
		</Button>
		<Button
			variant="outline"
			disabled={$disable.isPending || $runPipe.isPending || $updateCfg.isPending}
			onclick={async () => {
				try {
					await get(disable).mutateAsync(configId);
					toast.success('Config disabled.');
				} catch (e) {
					toast.error(e instanceof ApiError ? e.message : 'Could not disable');
				}
			}}
		>
			{$disable.isPending ? 'Disabling…' : 'Disable'}
		</Button>
	{:else}
		<Button
			variant="outline"
			disabled={$updateCfg.isPending || $disable.isPending}
			onclick={async () => {
				try {
					await get(updateCfg).mutateAsync({ id: configId, body: { is_active: true } });
					toast.success('Config enabled.');
				} catch (e) {
					toast.error(e instanceof ApiError ? e.message : 'Could not enable');
				}
			}}
		>
			{$updateCfg.isPending ? 'Enabling…' : 'Enable'}
		</Button>
	{/if}
	<Button variant="outline" disabled={$updateCfg.isPending || $disable.isPending} onclick={onEdit}>
		Edit
	</Button>
</div>
