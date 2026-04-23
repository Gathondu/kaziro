<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import Nav from '$lib/components/layout/Nav.svelte';
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

<Nav />
<main class="mx-auto max-w-6xl px-4 py-6">{@render children()}</main>
