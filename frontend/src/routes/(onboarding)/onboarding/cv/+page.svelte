<script lang="ts">
	import { goto } from '$app/navigation';
	import WizardProgress from '$lib/components/onboarding/WizardProgress.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { useCvUpload } from '$lib/hooks/useProfile';
	import { saveOnboardingDraft } from '$lib/utils/onboarding';
	import { get } from 'svelte/store';

	let file = $state<File | null>(null);
	let previewUrl = $state<string | null>(null);
	let err = $state<string | null>(null);

	const upload = useCvUpload();

	function onPick(e: Event): void {
		const input = e.currentTarget as HTMLInputElement;
		const f = input.files?.[0];
		err = null;
		if (previewUrl) {
			URL.revokeObjectURL(previewUrl);
			previewUrl = null;
		}
		file = f ?? null;
		if (file && file.type === 'application/pdf') {
			previewUrl = URL.createObjectURL(file);
		} else if (file) {
			err = 'Please choose a PDF file.';
		}
	}

	async function next(): Promise<void> {
		if (!file) {
			err = 'Select a PDF to continue.';
			return;
		}
		await get(upload).mutateAsync(file);
		saveOnboardingDraft({ step: 3 });
		await goto('/onboarding/config');
	}
</script>

<svelte:head>
	<title>Onboarding — CV</title>
</svelte:head>

<WizardProgress step={2} />
<h1 class="mb-2 text-xl font-semibold">Upload your CV</h1>
<p class="mb-6 text-sm text-base-content/70">
	We extract text for embeddings and keep the PDF in secure storage.
</p>
<label class="form-control mb-4">
	<span class="label-text font-medium">PDF file</span>
	<input
		class="file-input file-input-bordered rounded-xl border-base-300 bg-base-200"
		type="file"
		accept="application/pdf"
		onchange={onPick}
	/>
</label>
{#if err}
	<p class="mb-4 text-sm text-error">{err}</p>
{/if}
{#if previewUrl}
	<div class="mb-6 overflow-hidden rounded-2xl border border-base-300 bg-base-200">
		<iframe title="CV preview" src={previewUrl} width="100%" height="360" class="min-h-72 w-full"
		></iframe>
	</div>
{/if}
<div class="flex gap-3">
	<Button type="button" variant="outline" onclick={() => goto('/onboarding/profile')}>Back</Button>
	<Button type="button" disabled={$upload.isPending || !file} onclick={() => next()}>
		{$upload.isPending ? 'Uploading…' : 'Continue'}
	</Button>
</div>
