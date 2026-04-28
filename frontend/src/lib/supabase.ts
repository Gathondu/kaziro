import { createBrowserClient } from '@supabase/ssr';
import { getPublicSupabaseAnonKey, getPublicSupabaseUrl } from '$lib/env/public';

const QUERY_CACHE_KEY = 'kaziro-query-cache-v1';

function maybeDropCorruptJson(storageKey: string): void {
	if (typeof window === 'undefined') return;
	const raw = window.localStorage.getItem(storageKey);
	if (!raw) return;
	const trimmed = raw.trim();
	// Typical CloudFront/S3 fallback payload that can get accidentally persisted.
	if (trimmed.startsWith('<!doctype html') || trimmed.startsWith('<html')) {
		window.localStorage.removeItem(storageKey);
		return;
	}
	try {
		JSON.parse(raw);
	} catch {
		window.localStorage.removeItem(storageKey);
	}
}

function sanitizePersistedClientState(): void {
	if (typeof window === 'undefined') return;
	maybeDropCorruptJson(QUERY_CACHE_KEY);
	for (let i = 0; i < window.localStorage.length; i += 1) {
		const key = window.localStorage.key(i);
		if (!key) continue;
		if (key.startsWith('sb-') && key.endsWith('-auth-token')) {
			maybeDropCorruptJson(key);
		}
	}
}

sanitizePersistedClientState();

export const supabase = createBrowserClient(getPublicSupabaseUrl(), getPublicSupabaseAnonKey(), {
	auth: {
		autoRefreshToken: true,
		persistSession: true,
		detectSessionInUrl: true
	}
});
