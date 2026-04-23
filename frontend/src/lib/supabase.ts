import { createClient } from '@supabase/supabase-js';
import { getPublicSupabaseAnonKey, getPublicSupabaseUrl } from '$lib/env/public';

export const supabase = createClient(getPublicSupabaseUrl(), getPublicSupabaseAnonKey(), {
	auth: {
		autoRefreshToken: true,
		persistSession: true,
		detectSessionInUrl: true
	}
});
