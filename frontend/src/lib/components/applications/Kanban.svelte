<script lang="ts">
	import { flip } from 'svelte/animate';
	import { dndzone } from 'svelte-dnd-action';
	import type { Application } from '$lib/types/applications';
	import type { ApplicationStatus } from '$lib/types/enums';
	import { canTransition } from '$lib/utils/applicationTransitions';

	type Col = { status: ApplicationStatus; items: Application[] };

	const {
		applications,
		onMove
	}: {
		applications: Application[];
		onMove: (
			applicationId: string,
			from: ApplicationStatus,
			to: ApplicationStatus
		) => Promise<void>;
	} = $props();

	const STATUSES: ApplicationStatus[] = [
		'DRAFT',
		'SENT',
		'INTERVIEWING',
		'OFFERED',
		'REJECTED'
	];

	let columns = $state<Col[]>([]);

	function rebuild(): void {
		columns = STATUSES.map((status) => ({
			status,
			items: applications.filter((a) => a.status === status)
		}));
	}

	$effect(() => {
		rebuild();
	});

	const flipDurationMs = 200;

	function consider(status: ApplicationStatus) {
		return (e: CustomEvent<{ items: Application[] }>) => {
			columns = columns.map((c) => (c.status === status ? { ...c, items: e.detail.items } : c));
		};
	}

	function finalize(status: ApplicationStatus) {
		return async (e: CustomEvent<{ items: Application[] }>) => {
			columns = columns.map((c) => (c.status === status ? { ...c, items: e.detail.items } : c));
			const wrongStatus = e.detail.items.filter((a) => a.status !== status);
			for (const app of wrongStatus) {
				if (!canTransition(app.status, status)) {
					rebuild();
					throw new Error('Illegal transition');
				}
				await onMove(app.id, app.status, status);
			}
		};
	}
</script>

<div
	class="scroll-region flex min-h-0 flex-1 gap-3 overflow-x-auto overflow-y-hidden pb-1"
>
	{#each columns as col (col.status)}
		<div
			class="flex h-full min-h-0 w-64 shrink-0 flex-col rounded-2xl border border-base-300 bg-base-200 p-2"
		>
			<h3 class="mb-2 shrink-0 px-1 text-xs font-semibold uppercase tracking-wide text-base-content/70">
				{col.status}
			</h3>
			<div
				class="min-h-0 flex-1 space-y-2 overflow-y-auto rounded-xl bg-base-100/60 p-2"
				use:dndzone={{ items: col.items, flipDurationMs, type: 'kanban' }}
				onconsider={consider(col.status)}
				onfinalize={finalize(col.status)}
			>
				{#each col.items as app (app.id)}
					<div
						animate:flip={{ duration: flipDurationMs }}
						class="rounded-xl border border-base-300 bg-base-100 p-3 shadow-sm"
					>
						<a
							href="/jobs/{app.job_posting_id}"
							draggable={false}
							class="block cursor-pointer text-inherit no-underline outline-offset-2 hover:opacity-90"
						>
							<p class="text-sm font-semibold">{app.job_posting?.title ?? 'Application'}</p>
							<p class="text-xs text-base-content/60">{app.job_posting?.company_name ?? ''}</p>
						</a>
					</div>
				{/each}
			</div>
		</div>
	{/each}
</div>
