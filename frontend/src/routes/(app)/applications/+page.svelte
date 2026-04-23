<script lang="ts">
	import { get } from 'svelte/store';
	import Kanban from '$lib/components/applications/Kanban.svelte';
	import { useApplicationsBoard, useUpdateApplicationStatus } from '$lib/hooks/useApplication';
	import { ApiError } from '$lib/api/errors';
	import { toast } from '$lib/stores/toast';
	import type { ApplicationStatus } from '$lib/types/enums';

	const board = useApplicationsBoard();
	const statusMu = useUpdateApplicationStatus();

	async function onMove(
		applicationId: string,
		from: ApplicationStatus,
		to: ApplicationStatus
	): Promise<void> {
		try {
			await get(statusMu).mutateAsync({ id: applicationId, status: to });
			toast.success('Status updated');
		} catch (e) {
			if (e instanceof ApiError && e.status === 409) {
				toast.warning('That move is not allowed for this application.');
			} else {
				toast.error(e instanceof ApiError ? e.message : 'Update failed');
			}
			throw e;
		}
	}
</script>

<svelte:head>
	<title>Applications — Kaziro</title>
</svelte:head>

<h1 class="mb-4 text-2xl font-semibold">Applications</h1>

{#if $board.isPending}
	<p class="text-sm text-base-content/60">Loading board…</p>
{:else if $board.isError}
	<p class="text-sm text-error">Could not load applications.</p>
{:else if $board.data}
	<Kanban applications={$board.data} {onMove} />
{/if}
