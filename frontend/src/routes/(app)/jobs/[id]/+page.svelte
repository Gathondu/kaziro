<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import Button from '$lib/components/ui/Button.svelte';
	import CompanyBrief from '$lib/components/jobs/CompanyBrief.svelte';
	import EvaluationPanel from '$lib/components/jobs/EvaluationPanel.svelte';
	import JobDocumentsModal from '$lib/components/jobs/JobDocumentsModal.svelte';
	import { useCreateApplication, useMarkJobNotInterested } from '$lib/hooks/useApplication';
	import {
		useJobEvaluationFromRoute,
		useJobFromRoute,
		useTriggerEvaluation
	} from '$lib/hooks/useJobs';
	import { ApiError } from '$lib/api/errors';
	import { toast } from '$lib/stores/toast';

	const jobId = $derived($page.params.id);

	const jobQ = useJobFromRoute();
	const evQ = useJobEvaluationFromRoute();
	const triggerEv = useTriggerEvaluation();
	const createApp = useCreateApplication();
	const markNotInterested = useMarkJobNotInterested();
	let documentsModalOpen = $state(false);
	const backHref = $derived.by(() => {
		const requested = $page.url.searchParams.get('backTo');
		if (!requested) return '/jobs';
		return requested.startsWith('/jobs') ? requested : '/jobs';
	});

	async function reevaluate(): Promise<void> {
		if (!jobId) return;
		try {
			await get(triggerEv).mutateAsync(jobId);
			toast.info('Evaluation queued — you will get a toast when it completes.');
		} catch (e) {
			toast.error(e instanceof ApiError ? e.message : 'Could not queue evaluation');
		}
	}

	async function generateDocs(): Promise<void> {
		if (!jobId) return;
		try {
			const app = await get(createApp).mutateAsync(jobId);
			await goto(`/jobs/${jobId}/apply?applicationId=${app.id}`);
		} catch (e) {
			if (e instanceof ApiError && e.code === 'application_documents_generating') {
				toast.info(e.message);
				return;
			}
			toast.error(e instanceof ApiError ? e.message : 'Could not create application');
		}
	}

	async function notInterested(): Promise<void> {
		if (!jobId) return;
		try {
			await get(markNotInterested).mutateAsync(jobId);
			toast.success('Marked as not interested.');
			await goto('/jobs');
		} catch (e) {
			toast.error(e instanceof ApiError ? e.message : 'Could not update');
		}
	}
</script>

<svelte:head>
	<title>{$jobQ.data?.title ?? 'Job'} — Kaziro</title>
</svelte:head>

<div class="scroll-region h-full min-h-0 overflow-y-auto pr-1">
	{#if $jobQ.isPending || $evQ.isPending}
		<p class="text-sm text-base-content/60">Loading…</p>
	{:else if $jobQ.isError || $evQ.isError}
		<p class="text-sm text-error">Job or evaluation not found.</p>
	{:else if $jobQ.data && $evQ.data}
		<div class="sticky top-0 z-10 -mx-1 mb-6 bg-base-100/95 px-1 pb-3 pt-1 backdrop-blur">
			<div class="mb-3">
				<a
					href={backHref}
					class="btn btn-ghost btn-sm gap-2 rounded-xl text-base-content/80 hover:text-base-content"
					aria-label="Back to jobs list"
				>
					<svg viewBox="0 0 24 24" fill="none" class="h-4 w-4" aria-hidden="true">
						<path
							d="M15 18L9 12L15 6"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						></path>
					</svg>
					Back to jobs
				</a>
			</div>
			<div class="flex flex-wrap gap-2">
				<Button onclick={() => reevaluate()} disabled={$triggerEv.isPending}
					>Re-run evaluation</Button
				>
				{#if $evQ.data.application_doc}
					<Button variant="secondary" onclick={() => (documentsModalOpen = true)}>
						View documents
					</Button>
				{:else}
					<Button
						variant="secondary"
						onclick={() => generateDocs()}
						disabled={$createApp.isPending}
					>
						Generate documents
					</Button>
				{/if}
				{#if $evQ.data.final_classification !== 'REJECT'}
					<Button
						variant="outline"
						onclick={() => notInterested()}
						disabled={$markNotInterested.isPending}
					>
						{$markNotInterested.isPending ? 'Updating…' : 'Not interested'}
					</Button>
				{/if}
			</div>
		</div>
		<div class="grid gap-6 lg:grid-cols-2">
			<section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
				<h1 class="text-2xl font-semibold">{$jobQ.data.title}</h1>
				<p class="text-base-content/70">{$jobQ.data.company_name}</p>
				<a
					class="link link-primary mt-2 inline-block text-sm font-medium"
					href={$jobQ.data.application_url}
					target="_blank"
					rel="noopener noreferrer"
				>
					Apply on company site
				</a>
				<h2 class="mt-6 text-sm font-semibold">Description</h2>
				<div
					class="mt-2 max-w-none whitespace-pre-wrap text-sm leading-relaxed text-base-content/80"
				>
					{$jobQ.data.description}
				</div>
			</section>
			<div class="space-y-6">
				<EvaluationPanel evaluation={$evQ.data} />
				<CompanyBrief job={$jobQ.data} />
			</div>
		</div>
		{#if $evQ.data.application_doc && jobId}
			<JobDocumentsModal
				bind:open={documentsModalOpen}
				jobPostingId={jobId}
				applicationId={$evQ.data.application_id ?? ''}
				doc={$evQ.data.application_doc}
			/>
		{/if}
	{/if}
</div>
