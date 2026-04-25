import { browser } from '$app/environment';
import { QueryClient } from '@tanstack/svelte-query';

export function createAppQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: {
				staleTime: 5 * 60_000,
				gcTime: 30 * 60_000,
				retry: 1,
				refetchOnWindowFocus: true,
				refetchOnMount: false,
				enabled: browser
			}
		}
	});
}
