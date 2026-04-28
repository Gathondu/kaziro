<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import Button from '$lib/components/ui/Button.svelte';
	import {
		clearOnboardingPendingCv,
		getOnboardingPendingCv,
		setOnboardingPendingCv
	} from '$lib/utils/onboarding-pending-cv';
	import {
		loadOnboardingDraft,
		resumeOnboardingPath,
		saveOnboardingDraft
	} from '$lib/utils/onboarding';
	import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist';
	import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
	import { get } from 'svelte/store';

	const PREVIEW_MIN_HEIGHT = 360;
	const PREVIEW_MAX_HEIGHT = 760;

	if (browser) {
		GlobalWorkerOptions.workerSrc = pdfWorkerUrl;
	}

	let file = $state<File | null>(null);
	let previewUrl = $state<string | null>(null);
	let err = $state<string | null>(null);
	let fileInputEl = $state<HTMLInputElement | null>(null);
	let previewContainerWidth = $state(0);
	let previewFrameWidth = $state<number | null>(null);
	let previewFrameHeight = $state(PREVIEW_MIN_HEIGHT);
	let allowHorizontalOverflow = $state(false);

	const previewSrc = $derived(previewUrl ? `${previewUrl}#page=1&view=FitH` : null);
	const selectedFileLabel = $derived(file ? file.name : 'No file chosen');

	$effect(() => {
		if (!browser) return;
		const path = get(page).url.pathname;
		const d = loadOnboardingDraft();
		const want = resumeOnboardingPath(d);
		if (want !== path) void goto(want);
	});

	/** Restore staged PDF after Back from config (not stored in sessionStorage). */
	$effect(() => {
		if (!browser) return;
		const pending = getOnboardingPendingCv();
		if (!pending || file) return;
		file = pending;
		previewUrl = URL.createObjectURL(pending);
	});

	$effect(() => {
		if (!file || file.type !== 'application/pdf' || previewContainerWidth <= 0) return;
		void updatePreviewLayout(file, previewContainerWidth);
	});

	async function updatePreviewLayout(pdfFile: File, containerWidth: number): Promise<void> {
		try {
			const bytes = await pdfFile.arrayBuffer();
			const task = getDocument({ data: bytes });
			const pdf = await task.promise;
			const firstPage = await pdf.getPage(1);
			const viewport = firstPage.getViewport({ scale: 1 });
			const ratio = viewport.width / viewport.height;
			const fittedHeight = containerWidth / ratio;
			const nextHeight = Math.round(
				Math.min(PREVIEW_MAX_HEIGHT, Math.max(PREVIEW_MIN_HEIGHT, fittedHeight))
			);
			const nextWidth = Math.round(nextHeight * ratio);

			previewFrameHeight = nextHeight;
			allowHorizontalOverflow = nextWidth > containerWidth;
			previewFrameWidth = nextWidth;
			await pdf.destroy();
		} catch {
			previewFrameHeight = PREVIEW_MIN_HEIGHT;
			previewFrameWidth = containerWidth;
			allowHorizontalOverflow = false;
		}
	}

	function resetPreviewLayout(): void {
		previewFrameHeight = PREVIEW_MIN_HEIGHT;
		previewFrameWidth = null;
		allowHorizontalOverflow = false;
	}

	function onPick(e: Event): void {
		const input = e.currentTarget as HTMLInputElement;
		const f = input.files?.[0];
		err = null;
		clearOnboardingPendingCv();
		resetPreviewLayout();
		if (previewUrl) {
			URL.revokeObjectURL(previewUrl);
			previewUrl = null;
		}
		file = f ?? null;
		if (file && file.type === 'application/pdf') {
			// Stage immediately so Back -> Skills -> Next preserves the selected CV.
			setOnboardingPendingCv(file);
			previewUrl = URL.createObjectURL(file);
			if (previewContainerWidth > 0) {
				void updatePreviewLayout(file, previewContainerWidth);
			}
		} else if (file) {
			err = 'Please choose a PDF file.';
		}
	}

	async function next(): Promise<void> {
		if (!file) {
			err = 'Select a PDF to continue.';
			return;
		}
		const d = loadOnboardingDraft();
		saveOnboardingDraft({
			step: 3,
			profile: d?.profile ?? {},
			...(d?.lastConfigId !== undefined ? { lastConfigId: d.lastConfigId } : {})
		});
		await goto('/onboarding/config');
	}
</script>

<svelte:head>
	<title>Onboarding — CV</title>
</svelte:head>

<h1 class="mb-2 text-xl font-semibold">Upload your CV</h1>
<p class="text-base-content/70 mb-6 text-sm">
	We extract text for embeddings and keep the PDF in secure storage.
</p>
<label class="mb-4 block space-y-1.5">
	<span class="text-sm font-medium">PDF file</span>
	<input
		bind:this={fileInputEl}
		class="hidden"
		type="file"
		accept="application/pdf"
		onchange={onPick}
	/>
	<div class="flex flex-wrap items-center gap-3">
		<Button type="button" variant="outline" onclick={() => fileInputEl?.click()}>Choose file</Button
		>
		<span class="text-base-content/70 min-w-0 flex-1 truncate text-sm" title={selectedFileLabel}
			>{selectedFileLabel}</span
		>
	</div>
</label>
{#if err}
	<p class="text-error mb-4 text-sm">{err}</p>
{/if}
{#if previewUrl}
	<div
		bind:clientWidth={previewContainerWidth}
		class={`border-base-300 bg-base-200 mb-6 rounded-2xl border ${allowHorizontalOverflow ? 'scroll-region overflow-x-auto overflow-y-hidden' : 'overflow-hidden'}`}
	>
		<iframe
			title="CV preview"
			src={previewSrc ?? previewUrl}
			width={allowHorizontalOverflow ? (previewFrameWidth ?? previewContainerWidth) : '100%'}
			height={previewFrameHeight}
			class={`min-h-72 ${allowHorizontalOverflow ? 'max-w-none' : 'w-full'}`}
		></iframe>
	</div>
{/if}
<Button type="button" class="h-11 w-full justify-center" disabled={!file} onclick={() => next()}
	>Next</Button
>
