import { browser } from '$app/environment';
import { QueryClient } from '@tanstack/svelte-query';

export function createAppQueryClient(): QueryClient {
	return new QueryClient({
		defaultOptions: {
			queries: {
				staleTime: 60_000,
				retry: 1,
				refetchOnWindowFocus: true,
				enabled: browser
			}
		}
	});
}
