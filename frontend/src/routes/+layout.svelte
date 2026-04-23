<script lang="ts">
	import '../app.css';
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { browser } from '$app/environment';
	import { createAppQueryClient } from '$lib/api/queryClient';
	import { setQueryClient } from '$lib/queryClientSingleton';
	import { initAuthClient } from '$lib/stores/auth';
	import ToastHost from '$lib/components/ui/ToastHost.svelte';

	const { children } = $props();

	const queryClient = createAppQueryClient();
	setQueryClient(queryClient);

	$effect(() => {
		if (browser) {
			initAuthClient();
		}
	});
</script>

<QueryClientProvider client={queryClient}>
	<div class="min-h-screen">
		{@render children()}
	</div>
	<ToastHost />
</QueryClientProvider>
