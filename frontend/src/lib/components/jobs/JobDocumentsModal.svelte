<script lang="ts">
	import { get } from 'svelte/store';
	import Modal from '$lib/components/ui/Modal.svelte';
	import { signedJobCoverLetterPdfUrl, signedJobCvPdfUrl } from '$lib/api/jobs';
	import { ApiError } from '$lib/api/errors';
	import { useRegenerateJobDocuments } from '$lib/hooks/useJobs';
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

	const regenerateMutation = useRegenerateJobDocuments();

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

	async function refreshActiveDocument(): Promise<void> {
		const part = activeTab === 'cover' ? 'cover_letter' : 'cv';
		try {
			await get(regenerateMutation).mutateAsync({ jobId: jobPostingId, part });
			toast.info('Regeneration queued — you will get a toast when it is ready.');
		} catch (e) {
			toast.error(e instanceof ApiError ? e.message : 'Could not queue regeneration');
		}
	}
</script>

<Modal
	bind:open
	title="Application documents"
	boxClass="w-[calc(100vw-2rem)] max-w-lg sm:max-w-2xl lg:max-w-4xl xl:max-w-6xl"
>
	{#snippet children()}
		<div class="mb-3 flex justify-center">
			<div role="tablist" aria-label="Document type" class="tabs tabs-boxed shrink-0">
				<button
					type="button"
					role="tab"
					class="tab rounded-lg px-4"
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
					class="tab rounded-lg px-4"
					class:tab-active={activeTab === 'cv'}
					aria-selected={activeTab === 'cv'}
					onclick={() => {
						activeTab = 'cv';
					}}
				>
					Tailored CV
				</button>
			</div>
		</div>
		<div class="relative overflow-visible rounded-xl border border-base-300 bg-base-200/80 text-sm leading-relaxed text-base-content/90">
			<div
				class="absolute right-6 top-3 z-[80] flex gap-0.5 rounded-lg border border-base-300/60 bg-base-100/95 p-0.5 shadow-sm backdrop-blur-sm"
			>
				<div class="tooltip tooltip-bottom z-[90]" data-tip="copy to clipboard">
					<button
						type="button"
						class="btn btn-ghost btn-sm btn-square h-9 w-9 min-h-0 rounded-md text-base-content/80 hover:text-base-content"
						disabled={copyPending}
						aria-label="Copy to clipboard"
						onclick={() => void copyActive()}
					>
						{#if copyPending}
							<span class="loading loading-spinner loading-sm text-base-content/60" aria-hidden="true"
							></span>
						{:else}
							<svg
								class="h-5 w-5 shrink-0"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
							>
								<path
									d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"
								></path>
								<path
									d="M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v0a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v0z"
								></path>
							</svg>
						{/if}
					</button>
				</div>
				<div class="tooltip tooltip-bottom z-[90]" data-tip="download">
					<button
						type="button"
						class="btn btn-ghost btn-sm btn-square h-9 w-9 min-h-0 rounded-md text-base-content/80 hover:text-base-content disabled:opacity-40"
						disabled={!pdfAvailable || downloadPending}
						aria-label="Download"
						onclick={() => void downloadActivePdf()}
					>
						{#if downloadPending}
							<span class="loading loading-spinner loading-sm text-base-content/60" aria-hidden="true"
							></span>
						{:else}
							<svg
								class="h-5 w-5 shrink-0"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
							>
								<path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"></path>
								<path d="M12 4v12M8 12l4 4 4-4"></path>
							</svg>
						{/if}
					</button>
				</div>
				<div class="tooltip tooltip-bottom z-[90]" data-tip="regenerate">
					<button
						type="button"
						class="btn btn-ghost btn-sm btn-square h-9 w-9 min-h-0 rounded-md text-base-content/80 hover:text-base-content"
						disabled={$regenerateMutation.isPending}
						aria-label="Regenerate"
						onclick={() => void refreshActiveDocument()}
					>
						{#if $regenerateMutation.isPending}
							<span class="loading loading-spinner loading-sm text-base-content/60" aria-hidden="true"
							></span>
						{:else}
							<svg
								class="h-5 w-5 shrink-0"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
							>
								<path
									d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"
								></path>
								<path d="M3 3v5h5"></path>
								<path
									d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"
								></path>
								<path d="M16 16h5v5"></path>
							</svg>
						{/if}
					</button>
				</div>
			</div>
			<div class="max-h-96 overflow-y-auto px-4 pb-4 pt-12 pr-14">
				{#if activeTab === 'cover'}
					<div class="whitespace-pre-wrap">{doc.cover_letter_text}</div>
				{:else}
					<div class="whitespace-pre-wrap">{doc.tailored_cv_text}</div>
				{/if}
			</div>
		</div>
	{/snippet}
</Modal>
