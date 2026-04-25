<script lang="ts">
	import { get } from 'svelte/store';
	import Button from '$lib/components/ui/Button.svelte';
	import { ApiError } from '$lib/api/errors';
	import { useDisableJobConfig, useRunJobConfigPipeline } from '$lib/hooks/useJobConfig';
	import { toast } from '$lib/stores/toast';

	const { configId }: { configId: string } = $props();

	const disable = useDisableJobConfig();
	const runPipe = useRunJobConfigPipeline();
</script>

<div class="flex flex-wrap gap-2">
	<Button
		variant="outline"
		disabled={$runPipe.isPending || $disable.isPending}
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
		disabled={$disable.isPending || $runPipe.isPending}
		onclick={() => get(disable).mutateAsync(configId)}
	>
		{$disable.isPending ? 'Disabling…' : 'Disable'}
	</Button>
</div>
