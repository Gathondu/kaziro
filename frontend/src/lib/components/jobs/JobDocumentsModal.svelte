<script lang="ts">
	import { get } from 'svelte/store';
	import Modal from '$lib/components/ui/Modal.svelte';
	import { ApiError } from '$lib/api/errors';
	import { useUpdateApplicationDocs } from '$lib/hooks/useApplication';
	import { useRegenerateJobDocuments } from '$lib/hooks/useJobs';
	import { toast } from '$lib/stores/toast';
	import type { JobEvaluationApplicationDoc } from '$lib/types/jobs';
	import { copyTextToClipboard } from '$lib/utils/clipboard';
	import { downloadPlainTextAsPdf } from './job-documents-modal.functions';

	type TabId = 'cover' | 'cv';

	interface Props {
		open?: boolean;
		jobPostingId: string;
		/** Required for persisting edits; empty when no application row exists. */
		applicationId: string;
		doc: JobEvaluationApplicationDoc;
	}

	const AUTOSAVE_MS = 700;
	/** DaisyUI tooltip only — no `title` on children (avoids duplicate native tooltip). */
	const ICON_TOOLTIP_CLASS =
		'tooltip tooltip-bottom z-[90] before:px-1.5 before:py-0.5 before:text-[11px] before:leading-tight before:font-medium';

	let { open = $bindable(false), jobPostingId, applicationId, doc }: Props = $props();

	const regenerateMutation = useRegenerateJobDocuments();
	const updateDocsMutation = useUpdateApplicationDocs();

	let activeTab = $state<TabId>('cover');
	let copyPending = $state(false);
	let downloadPending = $state(false);
	let coverDraft = $state('');
	let cvDraft = $state('');
	let prevOpen = $state(false);

	const activeLabel = $derived(activeTab === 'cover' ? 'cover letter' : 'tailored CV');
	const activeDraft = $derived(activeTab === 'cover' ? coverDraft : cvDraft);
	const canDownload = $derived(activeDraft.trim().length > 0);
	const canPersist = $derived(Boolean(applicationId));
	const isDirty = $derived(
		coverDraft !== doc.cover_letter_text || cvDraft !== doc.tailored_cv_text
	);

	$effect(() => {
		const closing = prevOpen && !open;
		if (closing && canPersist && isDirty) {
			void persistDocs().catch((e: unknown) => {
				toast.error(e instanceof ApiError ? e.message : 'Could not save changes.');
			});
		}
		if (open && !prevOpen) {
			activeTab = 'cover';
			coverDraft = doc.cover_letter_text;
			cvDraft = doc.tailored_cv_text;
			copyPending = false;
			downloadPending = false;
		}
		prevOpen = open;
	});

	$effect(() => {
		if (!open || !canPersist || !isDirty) return;
		const t = setTimeout(() => {
			void persistDocs().catch((e: unknown) => {
				toast.error(e instanceof ApiError ? e.message : 'Could not save changes.');
			});
		}, AUTOSAVE_MS);
		return () => clearTimeout(t);
	});

	async function persistDocs(): Promise<void> {
		if (!applicationId) return;
		await get(updateDocsMutation).mutateAsync({
			id: applicationId,
			jobPostingId,
			body: { cover_letter_text: coverDraft, tailored_cv_text: cvDraft }
		});
	}

	async function copyActive(): Promise<void> {
		copyPending = true;
		try {
			await copyTextToClipboard(activeDraft);
			toast.success(`Copied ${activeLabel} to clipboard.`);
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Could not copy.');
		} finally {
			copyPending = false;
		}
	}

	async function downloadActive(): Promise<void> {
		if (!canDownload) return;
		downloadPending = true;
		try {
			const base = activeTab === 'cover' ? 'cover-letter' : 'tailored-cv';
			const heading = activeTab === 'cover' ? 'Cover letter' : 'Tailored CV — Kaziro';
			downloadPlainTextAsPdf({
				filename: `kaziro-${base}-${jobPostingId}.pdf`,
				heading,
				body: activeDraft
			});
			toast.success('PDF download started.');
		} catch (e) {
			toast.error(e instanceof Error ? e.message : 'Could not build PDF.');
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
	scrollBody={false}
	clipOverflow={false}
	boxClass="h-[min(90vh,calc(100vh-3.5rem))] min-h-[20rem] w-[calc(100vw-2rem)] max-w-lg sm:max-w-2xl lg:max-w-4xl xl:max-w-6xl"
>
	{#snippet children()}
		<div class="flex h-full min-h-0 w-full flex-1 flex-col">
			<div class="mb-3 flex shrink-0 justify-center">
				<div
					role="tablist"
					aria-label="Document type"
					class="border-base-300 bg-base-200 inline-flex shrink-0 gap-1 rounded-xl border p-1"
				>
					<button
						type="button"
						role="tab"
						class="rounded-lg px-4 py-2 text-sm font-medium transition-colors {activeTab === 'cover'
							? 'bg-base-100 text-base-content shadow-sm'
							: 'text-base-content/70 hover:bg-base-100/60 hover:text-base-content'}"
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
						class="rounded-lg px-4 py-2 text-sm font-medium transition-colors {activeTab === 'cv'
							? 'bg-base-100 text-base-content shadow-sm'
							: 'text-base-content/70 hover:bg-base-100/60 hover:text-base-content'}"
						aria-selected={activeTab === 'cv'}
						onclick={() => {
							activeTab = 'cv';
						}}
					>
						Tailored CV
					</button>
				</div>
			</div>
			<div
				class="text-base-content/90 relative flex min-h-0 flex-1 flex-col overflow-visible text-sm leading-relaxed"
			>
				<div class="flex min-h-0 flex-1 flex-col overflow-hidden p-2 sm:p-3">
					{#if activeTab === 'cover'}
						<label class="sr-only" for="job-doc-cover-draft">Cover letter</label>
						<textarea
							id="job-doc-cover-draft"
							bind:value={coverDraft}
							rows={1}
							class="text-base-content focus:ring-primary/40 box-border h-full min-h-0 w-full flex-1 resize-none overflow-y-auto border-0 bg-transparent pt-11 pr-10 pb-2.5 pl-3 font-sans text-sm leading-relaxed whitespace-pre-wrap shadow-none ring-0 transition-[box-shadow] outline-none focus:border-0 focus:ring-2 focus:outline-none sm:pr-44"
							spellcheck="true"
						></textarea>
					{:else}
						<label class="sr-only" for="job-doc-cv-draft">Tailored CV</label>
						<textarea
							id="job-doc-cv-draft"
							bind:value={cvDraft}
							rows={1}
							class="text-base-content focus:ring-primary/40 box-border h-full min-h-0 w-full flex-1 resize-none overflow-y-auto border-0 bg-transparent pt-11 pr-10 pb-2.5 pl-3 font-sans text-sm leading-relaxed whitespace-pre-wrap shadow-none ring-0 transition-[box-shadow] outline-none focus:border-0 focus:ring-2 focus:outline-none sm:pr-44"
							spellcheck="true"
						></textarea>
					{/if}
				</div>
				<div
					class="pointer-events-none absolute top-2 right-4 z-[80] flex max-w-[calc(100%-1rem)] items-start justify-end gap-2 sm:top-3 sm:right-8"
				>
					{#if !canPersist || $updateDocsMutation.isPending || isDirty}
						<div
							class="pointer-events-auto flex min-h-9 max-w-[min(100%,14rem)] items-center border-0 bg-transparent px-2 py-1.5 text-left text-xs leading-tight sm:max-w-[min(100%,20rem)]"
						>
							{#if canPersist && !isDirty && $updateDocsMutation.isPending}
								<p class="text-base-content/70" role="status">Saving…</p>
							{:else if canPersist && isDirty}
								<p class="text-base-content/60">Changes save automatically</p>
							{/if}
						</div>
					{/if}
					<div class="pointer-events-auto flex shrink-0 gap-0.5 border-0 bg-transparent p-0">
						<div class={ICON_TOOLTIP_CLASS} data-tip="Copy">
							<button
								type="button"
								class="btn btn-square btn-ghost btn-sm text-base-content/80 hover:text-base-content h-9 min-h-0 w-9 rounded-md"
								disabled={copyPending}
								aria-label="Copy to clipboard"
								onclick={() => void copyActive()}
							>
								{#if copyPending}
									<span
										class="loading loading-spinner loading-sm text-base-content/60"
										aria-hidden="true"
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
										<path d="M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v0a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2v0z"
										></path>
									</svg>
								{/if}
							</button>
						</div>
						<div class={ICON_TOOLTIP_CLASS} data-tip="PDF">
							<button
								type="button"
								class="btn btn-square btn-ghost btn-sm text-base-content/80 hover:text-base-content h-9 min-h-0 w-9 rounded-md disabled:opacity-40"
								disabled={!canDownload || downloadPending}
								aria-label="Download as PDF"
								onclick={() => void downloadActive()}
							>
								{#if downloadPending}
									<span
										class="loading loading-spinner loading-sm text-base-content/60"
										aria-hidden="true"
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
						<div class={ICON_TOOLTIP_CLASS} data-tip="Regenerate">
							<button
								type="button"
								class="btn btn-square btn-ghost btn-sm text-base-content/80 hover:text-base-content h-9 min-h-0 w-9 rounded-md"
								disabled={$regenerateMutation.isPending}
								aria-label="Regenerate document"
								onclick={() => void refreshActiveDocument()}
							>
								{#if $regenerateMutation.isPending}
									<span
										class="loading loading-spinner loading-sm text-base-content/60"
										aria-hidden="true"
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
										<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
										<path d="M3 3v5h5"></path>
										<path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
										<path d="M16 16h5v5"></path>
									</svg>
								{/if}
							</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	{/snippet}
</Modal>
