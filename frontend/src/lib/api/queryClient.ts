import { browser } from '$app/environment';
import { QueryClient } from '@tanstack/svelte-query';
import { persistQueryClient } from '@tanstack/query-persist-client-core';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';

const QUERY_CACHE_KEY = 'kaziro-query-cache-v1';
const QUERY_CACHE_MAX_AGE_MS = 15 * 60_000;
const PERSISTED_QUERY_ROOT_KEYS = new Set([
	'dashboard',
	'jobs',
	'job',
	'applications',
	'application',
	'job-configs',
	'job-config'
]);

function shouldPersistQuery(queryKey: readonly unknown[]): boolean {
	const root = queryKey[0];
	return typeof root === 'string' && PERSISTED_QUERY_ROOT_KEYS.has(root);
}

export function createAppQueryClient(): QueryClient {
	const client = new QueryClient({
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

	if (browser) {
		const persister = createSyncStoragePersister({
			storage: window.localStorage,
			key: QUERY_CACHE_KEY
		});
		void persistQueryClient({
			queryClient: client,
			persister,
			maxAge: QUERY_CACHE_MAX_AGE_MS,
			dehydrateOptions: {
				shouldDehydrateQuery: (query) => shouldPersistQuery(query.queryKey)
			}
		});
	}

	return client;
}
