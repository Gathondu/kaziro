<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import AppHeader from '$lib/components/layout/AppHeader.svelte';
	import AppSidebar from '$lib/components/layout/AppSidebar.svelte';
	import { connectNotifications, disconnectNotifications } from '$lib/stores/notifications';
	import { getJwt, getUser, isAuthReady } from '$lib/stores/auth';

	const { children } = $props();

	$effect(() => {
		if (!browser || !isAuthReady()) return;
		if (!getUser()) {
			const next = encodeURIComponent($page.url.pathname + $page.url.search);
			void goto(`/login?next=${next}`);
			return;
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

<div class="flex h-screen flex-col overflow-hidden">
	<AppHeader />
	<div class="flex min-h-0 flex-1 overflow-hidden">
		<AppSidebar />
		<main class="mx-auto w-full min-w-0 max-w-6xl flex-1 min-h-0 overflow-hidden px-4 py-6">
			{@render children()}
		</main>
	</div>
</div>
