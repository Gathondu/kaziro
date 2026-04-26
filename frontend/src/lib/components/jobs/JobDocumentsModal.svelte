<script lang="ts">
	import Modal from '$lib/components/ui/Modal.svelte';
	import type { JobEvaluationApplicationDoc } from '$lib/types/jobs';

	type TabId = 'cover' | 'cv';

	let {
		open = $bindable(false),
		doc
	}: {
		open?: boolean;
		doc: JobEvaluationApplicationDoc;
	} = $props();

	let activeTab = $state<TabId>('cover');

	$effect(() => {
		if (open) {
			activeTab = 'cover';
		}
	});
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
