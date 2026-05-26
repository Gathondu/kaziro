<script lang="ts">
	import { get } from 'svelte/store';
	import { ExternalLink, FileUp, RefreshCw } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { ApiError } from '$lib/api/errors';
	import { useCvUpload, useProfile, useProfileCvPdfUrl } from '$lib/hooks/useProfile';
	import { toast } from '$lib/stores/toast';

	const MAX_CV_BYTES = 10 * 1024 * 1024;

	const profile = useProfile();
	const cvUrl = useProfileCvPdfUrl();
	const upload = useCvUpload();

	let selectedFile = $state<File | null>(null);
	let fileInputEl = $state<HTMLInputElement | null>(null);
	let fileError = $state('');
	let uploadError = $state('');

	const hasMasterCv = $derived(Boolean($profile.data?.has_master_cv));
	const selectedFileLabel = $derived(
		selectedFile
			? `${selectedFile.name} (${formatFileSize(selectedFile.size)})`
			: 'No file selected'
	);
	const canUpload = $derived(Boolean(selectedFile) && !fileError && !$upload.isPending);

	function formatFileSize(bytes: number): string {
		if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	function validateFile(file: File): string {
		if (file.type !== 'application/pdf') {
			return 'Choose a PDF file.';
		}
		if (file.size > MAX_CV_BYTES) {
			return 'PDF must be 10 MB or smaller.';
		}
		return '';
	}

	function onPick(e: Event): void {
		const input = e.currentTarget as HTMLInputElement;
		const nextFile = input.files?.[0] ?? null;
		uploadError = '';
		selectedFile = nextFile;
		fileError = nextFile ? validateFile(nextFile) : '';
	}

	function clearSelection(): void {
		selectedFile = null;
		fileError = '';
		uploadError = '';
		if (fileInputEl) {
			fileInputEl.value = '';
		}
	}

	async function submit(e: Event): Promise<void> {
		e.preventDefault();
		uploadError = '';
		if (!selectedFile) {
			fileError = 'Choose a PDF first.';
			return;
		}
		fileError = validateFile(selectedFile);
		if (fileError) return;
		try {
			await get(upload).mutateAsync(selectedFile);
			clearSelection();
			toast.success('CV updated.');
		} catch (err) {
			uploadError =
				err instanceof ApiError || err instanceof Error ? err.message : 'Upload failed.';
			toast.error(uploadError);
		}
	}
</script>

<section class="border-base-300 mt-6 space-y-4 border-t pt-6" aria-labelledby="master-cv-heading">
	<div class="flex flex-wrap items-start justify-between gap-3">
		<div>
			<h3 id="master-cv-heading" class="text-base-content text-sm font-semibold">Current CV</h3>
			<p class="text-base-content/70 text-sm">
				View the CV Kaziro uses for matching and replace it with a newer PDF.
			</p>
		</div>
		{#if $cvUrl.data}
			<a class="btn btn-outline rounded-xl" href={$cvUrl.data} target="_blank" rel="noreferrer">
				<ExternalLink class="size-4" aria-hidden="true" />
				Open CV
			</a>
		{/if}
	</div>

	{#if !hasMasterCv}
		<p class="bg-base-200 text-base-content/70 rounded-xl border border-dashed p-4 text-sm">
			No CV is uploaded yet.
		</p>
	{:else if $cvUrl.isPending}
		<p class="text-base-content/60 text-sm">Loading CV preview...</p>
	{:else if $cvUrl.isError}
		<p class="text-error text-sm">Could not load the current CV preview.</p>
	{:else if $cvUrl.data}
		<div class="border-base-300 bg-base-200 overflow-hidden rounded-xl border">
			<iframe
				title="Current uploaded CV"
				src={$cvUrl.data}
				width="100%"
				height="420"
				class="bg-base-100 min-h-80 w-full"
			></iframe>
		</div>
	{/if}

	<form class="space-y-3" aria-label="Replace current CV" onsubmit={submit}>
		<label class="block space-y-1.5" for="master-cv-file">
			<span class="text-sm font-medium">Replacement CV PDF</span>
			<input
				id="master-cv-file"
				bind:this={fileInputEl}
				class="file-input file-input-bordered bg-base-200 w-full rounded-xl"
				type="file"
				accept="application/pdf"
				onchange={onPick}
			/>
		</label>
		<p class="text-base-content/60 truncate text-sm" title={selectedFileLabel}>
			{selectedFileLabel}
		</p>
		{#if fileError}
			<p class="text-error text-sm">{fileError}</p>
		{/if}
		{#if uploadError}
			<p class="text-error text-sm">{uploadError}</p>
		{/if}
		<div class="flex flex-wrap gap-2">
			<Button type="submit" disabled={!canUpload}>
				{#if $upload.isPending}
					<RefreshCw class="size-4 animate-spin" aria-hidden="true" />
					Uploading...
				{:else}
					<FileUp class="size-4" aria-hidden="true" />
					{hasMasterCv ? 'Replace CV' : 'Upload CV'}
				{/if}
			</Button>
			{#if selectedFile}
				<Button type="button" variant="ghost" onclick={clearSelection}>Clear</Button>
			{/if}
		</div>
	</form>
</section>
