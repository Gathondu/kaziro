<script lang="ts">
	import { get } from 'svelte/store';
	import { Link } from 'lucide-svelte';
	import { ApiError } from '$lib/api/errors';
	import { useImportJobUrl } from '$lib/hooks/useJobs';
	import { toast } from '$lib/stores/toast';

	let url = $state('');
	let fieldError = $state('');
	const mutation = useImportJobUrl();

	function validate(value: string): string {
		const trimmed = value.trim();
		if (!trimmed) return 'Paste a job post URL first.';
		try {
			const parsed = new URL(trimmed);
			if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
				return 'Use an http or https URL.';
			}
		} catch {
			return 'Enter a valid job post URL.';
		}
		return '';
	}

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		fieldError = validate(url);
		if (fieldError) return;
		try {
			await get(mutation).mutateAsync(url.trim());
			toast.info('Job processing started.');
			url = '';
		} catch (error) {
			fieldError = error instanceof ApiError ? error.message : 'Could not start that job import.';
		}
	}
</script>

<form
	class="border-base-300 bg-base-100 mb-4 rounded-lg border p-4 shadow-sm"
	onsubmit={submit}
	aria-label="Import a job from URL"
>
	<div class="flex flex-col gap-3 lg:flex-row lg:items-end">
		<label class="block min-w-0 flex-1 space-y-1.5">
			<span class="text-sm font-medium">Job post URL</span>
			<input
				class="input input-bordered w-full rounded-lg"
				type="url"
				placeholder="https://company.example/jobs/role"
				bind:value={url}
				aria-invalid={fieldError ? 'true' : 'false'}
				aria-describedby={fieldError ? 'job-url-import-error' : undefined}
			/>
		</label>
		<button
			class="btn btn-primary gap-2 rounded-lg whitespace-nowrap"
			type="submit"
			disabled={$mutation.isPending}
		>
			<Link class="h-4 w-4" aria-hidden="true" />
			{$mutation.isPending ? 'Starting...' : 'Import job'}
		</button>
	</div>
	{#if fieldError}
		<p id="job-url-import-error" class="text-error mt-2 text-sm">{fieldError}</p>
	{:else}
		<p class="text-base-content/60 mt-2 text-sm" aria-live="polite">
			Kaziro will start parsing, evaluating, and researching the job right away.
		</p>
	{/if}
</form>
