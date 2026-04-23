import type { QueryClient } from '@tanstack/svelte-query';

let _client: QueryClient | null = null;

export function setQueryClient(c: QueryClient): void {
	_client = c;
}

export function getQueryClient(): QueryClient | null {
	return _client;
}
