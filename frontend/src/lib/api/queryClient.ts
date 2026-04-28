import { browser } from '$app/environment';
import { QueryClient } from '@tanstack/svelte-query';
import { persistQueryClient } from '@tanstack/query-persist-client-core';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';

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
		const persister = createAsyncStoragePersister({
			storage: {
				getItem: async (key: string) => window.localStorage.getItem(key),
				setItem: async (key: string, value: string) => {
					window.localStorage.setItem(key, value);
				},
				removeItem: async (key: string) => {
					window.localStorage.removeItem(key);
				}
			},
			key: QUERY_CACHE_KEY
		});
		const [, restorePromise] = persistQueryClient({
			queryClient: client,
			persister,
			maxAge: QUERY_CACHE_MAX_AGE_MS,
			dehydrateOptions: {
				shouldDehydrateQuery: (query) => shouldPersistQuery(query.queryKey)
			}
		});
		void restorePromise.catch(() => {
			// If persisted payload is corrupted/non-JSON (e.g. HTML), recover by clearing it.
			window.localStorage.removeItem(QUERY_CACHE_KEY);
		});
	}

	return client;
}
