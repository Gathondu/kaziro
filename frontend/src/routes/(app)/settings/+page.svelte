<script lang="ts">
	import { page } from '$app/stores';
	import JobConfigsList from '$lib/components/settings/JobConfigsList.svelte';
	import JobConfigEditorModal from '$lib/components/settings/JobConfigEditorModal.svelte';
	import ProfileSettingsForm from '$lib/components/settings/ProfileSettingsForm.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import { useJobConfigs } from '$lib/hooks/useJobConfig';
	import type { JobConfig } from '$lib/types/jobConfig';

	type SettingsTab = 'job-configs' | 'profile';
	const activeTab = $derived.by<SettingsTab>(() => {
		const tab = $page.url.searchParams.get('tab');
		return tab === 'profile' ? 'profile' : 'job-configs';
	});

	const jobConfigsQuery = useJobConfigs(false);

	let editorOpen = $state(false);
	let editorMode = $state<'create' | 'edit'>('create');
	let editorConfig = $state<JobConfig | null>(null);

	function openCreateEditor(): void {
		editorMode = 'create';
		editorConfig = null;
		editorOpen = true;
	}

	function openEditEditor(cfg: JobConfig): void {
		editorMode = 'edit';
		editorConfig = cfg;
		editorOpen = true;
	}

	const addConfigLabel = $derived.by(() => {
		const q = $jobConfigsQuery;
		if (q.isPending || q.isError) return 'Add new';
		if (!q.data?.length) return 'Create config';
		return 'Add new';
	});
</script>

<svelte:head>
	<title>Settings — Kaziro</title>
</svelte:head>

<div class="scroll-region h-full min-h-0 overflow-y-auto pr-1">
	<div
		class="bg-base-100/95 sticky top-0 z-10 -mx-1 mb-6 flex flex-wrap items-center justify-between gap-3 px-1 py-1 backdrop-blur"
	>
		<div
			class="border-base-300 bg-base-200 inline-flex shrink-0 gap-1 rounded-xl border p-1"
			role="tablist"
			aria-label="Settings sections"
		>
			<a
				class="rounded-lg px-4 py-2 text-sm font-medium transition-colors {activeTab ===
				'job-configs'
					? 'bg-base-100 text-base-content shadow-sm'
					: 'text-base-content/70 hover:bg-base-100/60 hover:text-base-content'}"
				role="tab"
				aria-selected={activeTab === 'job-configs'}
				href="/settings?tab=job-configs">Job configs</a
			>
			<a
				class="rounded-lg px-4 py-2 text-sm font-medium transition-colors {activeTab === 'profile'
					? 'bg-base-100 text-base-content shadow-sm'
					: 'text-base-content/70 hover:bg-base-100/60 hover:text-base-content'}"
				role="tab"
				aria-selected={activeTab === 'profile'}
				href="/settings?tab=profile">Profile</a
			>
		</div>
		{#if activeTab === 'job-configs'}
			<Button variant="primary" class="shrink-0" onclick={openCreateEditor}>{addConfigLabel}</Button
			>
		{/if}
	</div>

	{#if activeTab === 'job-configs'}
		<JobConfigsList onEdit={openEditEditor} />
		<JobConfigEditorModal bind:open={editorOpen} mode={editorMode} config={editorConfig} />
	{:else}
		<ProfileSettingsForm />
	{/if}
</div>
