import { env } from '$env/dynamic/public';

/** API origin without trailing slash (defaults for CI / `pnpm build` without `.env`). */
export function getPublicApiUrl(): string {
	return (env.PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');
}

export function getPublicSupabaseUrl(): string {
	return env.PUBLIC_SUPABASE_URL ?? 'https://placeholder.supabase.co';
}

export function getPublicSupabaseAnonKey(): string {
	return env.PUBLIC_SUPABASE_ANON_KEY ?? 'placeholder-anon-key';
}

/** Optional contact for GDPR / data-deletion requests (settings UI, etc.). */
export function getPublicSupportEmail(): string | undefined {
	const v = env.PUBLIC_SUPPORT_EMAIL?.trim();
	return v || undefined;
}
