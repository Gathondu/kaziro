<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import Button from '$lib/components/ui/Button.svelte';
	import CompanyBrief from '$lib/components/jobs/CompanyBrief.svelte';
	import EvaluationPanel from '$lib/components/jobs/EvaluationPanel.svelte';
	import { useCreateApplication } from '$lib/hooks/useApplication';
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
			toast.error(e instanceof ApiError ? e.message : 'Could not create application');
		}
	}

	async function notInterested(): Promise<void> {
		if (!jobId) return;
		try {
			const {
				LIST_APPLICATIONS_MAX_LIMIT,
				listApplications,
				createApplication,
				updateApplicationStatus
			} = await import('$lib/api/applications');
			const { items } = await listApplications({ limit: LIST_APPLICATIONS_MAX_LIMIT });
			let app = items.find((a) => a.job_posting_id === jobId);
			if (!app) {
				app = await createApplication(jobId);
			}
			await updateApplicationStatus(app.id, 'WITHDRAWN');
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

{#if $jobQ.isPending || $evQ.isPending}
	<p class="text-sm text-base-content/60">Loading…</p>
{:else if $jobQ.isError || $evQ.isError}
	<p class="text-sm text-error">Job or evaluation not found.</p>
{:else if $jobQ.data && $evQ.data}
	<div class="mb-6 flex flex-wrap gap-2">
		<Button onclick={() => reevaluate()} disabled={$triggerEv.isPending}>Re-run evaluation</Button>
		<Button variant="secondary" onclick={() => generateDocs()} disabled={$createApp.isPending}>
			Generate documents
		</Button>
		<Button variant="outline" onclick={() => notInterested()}>Not interested</Button>
	</div>
	<div class="grid gap-6 lg:grid-cols-2">
		<section class="rounded-2xl border border-base-300 bg-base-100 p-5 shadow-sm">
			<h1 class="text-2xl font-semibold">{$jobQ.data.title}</h1>
			<p class="text-base-content/70">{$jobQ.data.company_name}</p>
			<a
				class="link link-primary mt-2 inline-block text-sm font-medium"
				href={$jobQ.data.application_url}
			>
				Apply on company site
			</a>
			<h2 class="mt-6 text-sm font-semibold">Description</h2>
			<div class="mt-2 max-w-none whitespace-pre-wrap text-sm leading-relaxed text-base-content/80">
				{$jobQ.data.description}
			</div>
		</section>
		<div class="space-y-6">
			<EvaluationPanel evaluation={$evQ.data} />
			<CompanyBrief job={$jobQ.data} />
		</div>
	</div>
{/if}
