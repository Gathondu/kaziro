<script lang="ts">
	import { page } from '$app/stores';
	import { get } from 'svelte/store';
	import Button from '$lib/components/ui/Button.svelte';
	import CoverLetterEditor from '$lib/components/applications/CoverLetterEditor.svelte';
	import PdfPreview from '$lib/components/applications/PdfPreview.svelte';
	import {
		useApplicationFromQueryParam,
		useMarkApplicationSent,
		useUpdateApplicationDocs
	} from '$lib/hooks/useApplication';
	import { signedCoverLetterUrl, signedCvUrl } from '$lib/api/applications';
	import { ApiError } from '$lib/api/errors';
	import { toast } from '$lib/stores/toast';

	const applicationId = $derived($page.url.searchParams.get('applicationId') ?? '');

	const appQ = useApplicationFromQueryParam('applicationId');
	const saveDocs = useUpdateApplicationDocs();
	const markSent = useMarkApplicationSent();

	let cover = $state('');
	let cvUrl = $state<string | null>(null);
	let clUrl = $state<string | null>(null);

	$effect(() => {
		const d = get(appQ).data?.application_doc;
		if (d) {
			cover = d.cover_letter_text ?? '';
		}
	});

	$effect(() => {
		const app = get(appQ).data;
		if (!app?.id || !app.application_doc?.cv_pdf_path) {
			cvUrl = null;
			clUrl = null;
			return;
		}
		let cancelled = false;
		void (async () => {
			try {
				const [cv, cl] = await Promise.all([signedCvUrl(app.id), signedCoverLetterUrl(app.id)]);
				if (!cancelled) {
					cvUrl = cv;
					clUrl = cl;
				}
			} catch {
				if (!cancelled) {
					cvUrl = null;
					clUrl = null;
				}
			}
		})();
		return () => {
			cancelled = true;
		};
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
			{#if cvUrl}
				<PdfPreview title="Tailored CV" url={cvUrl} />
			{/if}
			{#if clUrl}
				<PdfPreview title="Cover letter PDF" url={clUrl} />
			{/if}
		</div>
	</div>
{/if}
