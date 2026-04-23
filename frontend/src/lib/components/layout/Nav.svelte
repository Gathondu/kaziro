<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { signOutEverywhere } from '$lib/stores/auth';
	import { isNotificationsConnected, subscribeConnection } from '$lib/stores/notifications';

	let wsOk = $state(false);
	$effect(() =>
		subscribeConnection(() => {
			wsOk = isNotificationsConnected();
		})
	);

	const path = $derived($page.url.pathname);

	async function logout(): Promise<void> {
		await signOutEverywhere();
		await goto('/login');
	}

	const linkCls = (href: string) =>
		`rounded-xl px-3 py-2 text-sm font-medium tracking-nav transition-colors ${
			path === href || path.startsWith(href + '/')
				? 'bg-primary text-primary-content'
				: 'text-base-content hover:bg-base-200'
		}`;
</script>

<header
	class="sticky top-0 z-40 flex flex-wrap items-center justify-between gap-3 border-b border-base-300 bg-base-100 px-4 py-3"
>
	<a href="/dashboard" class="text-lg font-semibold text-primary">Kaziro</a>
	<nav class="flex flex-wrap items-center gap-1" aria-label="Main">
		<a class={linkCls('/dashboard')} href="/dashboard">Dashboard</a>
		<a class={linkCls('/jobs')} href="/jobs">Jobs</a>
		<a class={linkCls('/applications')} href="/applications">Applications</a>
		<a class={linkCls('/settings')} href="/settings">Settings</a>
		<a class={linkCls('/onboarding')} href="/onboarding/profile">Onboarding</a>
	</nav>
	<div class="flex items-center gap-2">
		<span
			class="badge rounded-lg font-medium {wsOk ? 'badge-success' : 'badge-ghost'}"
			title="Realtime connection"
		>
			{wsOk ? 'Live' : 'Offline'}
		</span>
		<button
			type="button"
			class="btn btn-ghost btn-sm rounded-xl font-medium"
			onclick={() => logout()}>Log out</button
		>
	</div>
</header>
