import { env } from '$env/dynamic/public';

/** API origin without trailing slash (defaults for CI / `pnpm build` without `.env`). */
export function getPublicApiUrl(): string {
	return normalizePublicApiUrl(env.PUBLIC_API_URL ?? 'http://localhost:8000');
}

export function normalizePublicApiUrl(value: string): string {
	return value.replace(/\/$/, '').replace(/\/api\/v1$/, '');
}

/** Optional websocket origin; falls back to PUBLIC_API_URL when unset. */
export function getPublicWsUrl(): string | undefined {
	const value = env.PUBLIC_WS_URL?.trim();
	return value ? value.replace(/\/$/, '') : undefined;
}

export function getPublicSupabaseUrl(): string {
	return env.PUBLIC_SUPABASE_URL ?? 'https://placeholder.supabase.co';
}

export function getPublicSupabaseAnonKey(): string {
	return env.PUBLIC_SUPABASE_ANON_KEY ?? 'placeholder-anon-key';
}

/** Canonical site origin for SEO (no trailing slash). Prefer over `url.origin` behind proxies. */
export function getPublicSiteUrl(): string | undefined {
	const raw = env.PUBLIC_SITE_URL?.trim();
	if (!raw) return undefined;
	return raw.replace(/\/$/, '');
}

/** Optional contact for GDPR / data-deletion requests (settings UI, etc.). */
export function getPublicSupportEmail(): string | undefined {
	const v = env.PUBLIC_SUPPORT_EMAIL?.trim();
	return v || undefined;
}
