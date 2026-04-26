<script lang="ts">
	import Button from '$lib/components/ui/Button.svelte';
	import Modal from '$lib/components/ui/Modal.svelte';
	import { signedJobCoverLetterPdfUrl, signedJobCvPdfUrl } from '$lib/api/jobs';
	import { ApiError } from '$lib/api/errors';
	import { toast } from '$lib/stores/toast';
	import type { JobEvaluationApplicationDoc } from '$lib/types/jobs';
	import { copyTextToClipboard } from '$lib/utils/clipboard';

	type TabId = 'cover' | 'cv';

	let {
		open = $bindable(false),
		jobPostingId,
		doc
	}: {
		open?: boolean;
		jobPostingId: string;
		doc: JobEvaluationApplicationDoc;
	} = $props();

	let activeTab = $state<TabId>('cover');
	let copyPending = $state(false);
	let downloadPending = $state(false);

	const activeLabel = $derived(activeTab === 'cover' ? 'cover letter' : 'tailored CV');
	const pdfAvailable = $derived(
		activeTab === 'cover'
			? doc.cover_letter_pdf_available === true
			: doc.cv_pdf_available === true
	);

	$effect(() => {
		if (open) {
			activeTab = 'cover';
			copyPending = false;
			downloadPending = false;
		}
	});

	async function copyActive(): Promise<void> {
		copyPending = true;
		try {
			const text = activeTab === 'cover' ? doc.cover_letter_text : doc.tailored_cv_text;
			await copyTextToClipboard(text);
			toast.success(`Copied ${activeLabel} to clipboard.`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Could not copy.');
		} finally {
			copyPending = false;
		}
	}

	async function downloadActivePdf(): Promise<void> {
		if (!pdfAvailable) return;
		downloadPending = true;
		try {
			const url =
				activeTab === 'cover'
					? await signedJobCoverLetterPdfUrl(jobPostingId)
					: await signedJobCvPdfUrl(jobPostingId);
			window.open(url, '_blank', 'noopener,noreferrer');
		} catch (e) {
			toast.error(e instanceof ApiError ? e.message : 'Could not start download.');
		} finally {
			downloadPending = false;
		}
	}
</script>

<Modal bind:open title="Application documents">
	{#snippet children()}
		<div role="tablist" aria-label="Document type" class="tabs tabs-boxed mb-3 w-full max-w-md">
			<button
				type="button"
				role="tab"
				class="tab flex-1 rounded-lg"
				class:tab-active={activeTab === 'cover'}
				aria-selected={activeTab === 'cover'}
				onclick={() => {
					activeTab = 'cover';
				}}
			>
				Cover letter
			</button>
			<button
				type="button"
				role="tab"
				class="tab flex-1 rounded-lg"
				class:tab-active={activeTab === 'cv'}
				aria-selected={activeTab === 'cv'}
				onclick={() => {
					activeTab = 'cv';
				}}
			>
				Tailored CV
			</button>
		</div>
		<div class="mb-3 flex flex-wrap gap-2">
			<Button
				variant="outline"
				disabled={copyPending}
				onclick={() => void copyActive()}
				class="btn-sm"
				ariaLabel="Copy current tab text to clipboard"
			>
				{copyPending ? 'Copying…' : 'Copy text'}
			</Button>
			<Button
				variant="outline"
				disabled={!pdfAvailable || downloadPending}
				onclick={() => void downloadActivePdf()}
				class="btn-sm"
				ariaLabel="Download current tab as PDF"
			>
				{downloadPending ? 'Opening…' : 'Download PDF'}
			</Button>
		</div>
		<div
			class="max-h-96 overflow-y-auto rounded-xl border border-base-300 bg-base-200/80 p-4 text-sm leading-relaxed text-base-content/90"
		>
			{#if activeTab === 'cover'}
				<div class="whitespace-pre-wrap">{doc.cover_letter_text}</div>
			{:else}
				<div class="whitespace-pre-wrap">{doc.tailored_cv_text}</div>
			{/if}
		</div>
	{/snippet}
</Modal>
