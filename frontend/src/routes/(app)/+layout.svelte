<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import AppHeader from '$lib/components/layout/AppHeader.svelte';
	import AppSidebar from '$lib/components/layout/AppSidebar.svelte';
	import { getMe } from '$lib/api/me';
	import { connectNotifications, disconnectNotifications } from '$lib/stores/notifications';
	import { getJwt, getUser, isAuthReady } from '$lib/stores/auth';

	const { children } = $props();

	let lastAppMeCheckUserId = $state<string | null>(null);

	$effect(() => {
		if (!browser || !isAuthReady()) return;
		if (!getUser()) {
			lastAppMeCheckUserId = null;
			const next = encodeURIComponent($page.url.pathname + $page.url.search);
			void goto(`/login?next=${next}`);
			return;
		}
		const uid = getUser()!.id;
		if (lastAppMeCheckUserId !== uid) {
			lastAppMeCheckUserId = uid;
			void getMe().catch(() => {
				/* 403 user_deactivated handled in api client (sign out + redirect) */
			});
		}
		const token = getJwt();
		if (token) {
			connectNotifications(token);
		}
		return () => {
			disconnectNotifications();
		};
	});
</script>

<svelte:head>
	<meta name="robots" content="noindex,nofollow" />
</svelte:head>

<div class="flex h-screen flex-col overflow-hidden">
	<AppHeader />
	<div class="flex min-h-0 flex-1 overflow-hidden">
		<AppSidebar />
		<main
			class="mx-auto flex min-h-0 w-full max-w-6xl min-w-0 flex-1 flex-col overflow-hidden px-4 py-6"
		>
			{@render children()}
		</main>
	</div>
</div>
