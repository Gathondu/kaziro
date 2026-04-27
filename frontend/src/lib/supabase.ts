import { createBrowserClient } from '@supabase/ssr';
import { getPublicSupabaseAnonKey, getPublicSupabaseUrl } from '$lib/env/public';

export const supabase = createBrowserClient(getPublicSupabaseUrl(), getPublicSupabaseAnonKey(), {
	auth: {
		autoRefreshToken: true,
		persistSession: true,
		detectSessionInUrl: true
	}
});
