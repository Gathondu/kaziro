<script lang="ts">
	import { page } from '$app/stores';
	import JobConfigsList from '$lib/components/settings/JobConfigsList.svelte';
	import ProfileSettingsForm from '$lib/components/settings/ProfileSettingsForm.svelte';

	type SettingsTab = 'job-configs' | 'profile';
	const activeTab = $derived.by<SettingsTab>(() => {
		const tab = $page.url.searchParams.get('tab');
		return tab === 'profile' ? 'profile' : 'job-configs';
	});
</script>

<svelte:head>
	<title>Settings — Kaziro</title>
</svelte:head>

<div class="tabs tabs-boxed mb-6 w-fit rounded-xl border border-base-300 bg-base-200 p-1">
	<a class="tab rounded-lg {activeTab === 'job-configs' ? 'tab-active' : ''}" href="/settings?tab=job-configs"
		>Job configs</a
	>
	<a class="tab rounded-lg {activeTab === 'profile' ? 'tab-active' : ''}" href="/settings?tab=profile"
		>Profile</a
	>
</div>

{#if activeTab === 'job-configs'}
	<JobConfigsList />
{:else}
	<ProfileSettingsForm />
{/if}
