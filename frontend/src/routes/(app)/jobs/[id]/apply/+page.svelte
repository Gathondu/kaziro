<script lang="ts">
	import { page } from '$app/stores';
	import { get } from 'svelte/store';
	import Button from '$lib/components/ui/Button.svelte';
	import CoverLetterEditor from '$lib/components/applications/CoverLetterEditor.svelte';
	import PdfPreview from '$lib/components/applications/PdfPreview.svelte';
	import {
		useApplicationFromQueryParam,
		useApplicationPdfUrlsFromQueryParam,
		useMarkApplicationSent,
		useUpdateApplicationDocs
	} from '$lib/hooks/useApplication';
	import { ApiError } from '$lib/api/errors';
	import { toast } from '$lib/stores/toast';

	const applicationId = $derived($page.url.searchParams.get('applicationId') ?? '');

	const appQ = useApplicationFromQueryParam('applicationId');
	const pdfUrlsQ = useApplicationPdfUrlsFromQueryParam('applicationId');
	const saveDocs = useUpdateApplicationDocs();
	const markSent = useMarkApplicationSent();

	let cover = $state('');
	let syncedDocId = $state<string | null>(null);

	$effect(() => {
		const doc = $appQ.data?.application_doc;
		const docId = doc?.id ?? null;
		if (!docId || docId === syncedDocId) return;

		syncedDocId = docId;
		cover = doc?.cover_letter_text ?? '';
	});

	async function save(): Promise<void> {
		if (!applicationId) return;
		try {
			await get(saveDocs).mutateAsync({
				id: applicationId,
				body: { cover_letter_text: cover }
			});
			toast.success('Saved.');
		} catch (e) {
			toast.error(e instanceof ApiError ? e.message : 'Save failed');
		}
	}

	async function sent(): Promise<void> {
		if (!applicationId) return;
		try {
			await get(markSent).mutateAsync(applicationId);
			toast.success('Marked as sent.');
		} catch (e) {
			toast.error(e instanceof ApiError ? e.message : 'Could not mark sent');
		}
	}
</script>

<svelte:head>
	<title>Apply — Kaziro</title>
</svelte:head>

{#if !applicationId}
	<p class="text-sm text-error">Missing application. Open this page from the job detail action.</p>
{:else if $appQ.isPending}
	<p class="text-sm text-base-content/60">Loading application…</p>
{:else if $appQ.isError}
	<p class="text-sm text-error">Application not found.</p>
{:else if $appQ.data}
	<p class="mb-6 text-sm text-base-content/70">
		Job: <strong>{$appQ.data.job_posting?.title ?? ''}</strong>
	</p>
	<div class="grid gap-6 lg:grid-cols-2">
		<div class="space-y-4">
			<h2 class="text-sm font-semibold">Cover letter</h2>
			<CoverLetterEditor bind:value={cover} />
			<div class="flex flex-wrap gap-2">
				<Button onclick={() => save()} disabled={$saveDocs.isPending}>
					{$saveDocs.isPending ? 'Saving…' : 'Save'}
				</Button>
				<Button variant="secondary" onclick={() => sent()} disabled={$markSent.isPending}>
					{$markSent.isPending ? 'Updating…' : 'Mark as sent'}
				</Button>
			</div>
		</div>
		<div class="space-y-4">
			{#if $pdfUrlsQ.data?.cvUrl}
				<PdfPreview title="Tailored CV" url={$pdfUrlsQ.data.cvUrl} />
			{/if}
			{#if $pdfUrlsQ.data?.coverLetterUrl}
				<PdfPreview title="Cover letter PDF" url={$pdfUrlsQ.data.coverLetterUrl} />
			{/if}
		</div>
	</div>
{/if}
