// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces.
import type { SupabaseClient } from '@supabase/supabase-js';

declare module '$env/dynamic/public' {
	export const env: {
		PUBLIC_API_URL?: string;
		PUBLIC_SUPABASE_URL?: string;
		PUBLIC_SUPABASE_ANON_KEY?: string;
		PUBLIC_SITE_URL?: string;
		[key: string]: string | undefined;
	};
}

declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			supabase: SupabaseClient;
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
