<script lang="ts">
	import '../app.css';
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { browser } from '$app/environment';
	import { untrack, type Snippet } from 'svelte';
	import { createAppQueryClient } from '$lib/api/queryClient';
	import { setQueryClient } from '$lib/queryClientSingleton';
	import { initAppearance } from '$lib/stores/appearance.svelte';
	import { initAuthClient } from '$lib/stores/auth';
	import ToastHost from '$lib/components/ui/ToastHost.svelte';
	import type { LayoutData } from './$types';

	const { children, data }: { children: Snippet; data: LayoutData } = $props();

	const queryClient = createAppQueryClient();
	setQueryClient(queryClient);

	if (browser) {
		const initialAppearance = untrack(() => data.appearance);
		initAppearance(initialAppearance);
	}

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
