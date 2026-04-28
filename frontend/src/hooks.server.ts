import { createServerClient } from '@supabase/ssr';
import type { Handle } from '@sveltejs/kit';
import { getPublicSupabaseAnonKey, getPublicSupabaseUrl } from '$lib/env/public';

export const handle: Handle = async ({ event, resolve }) => {
	event.locals.supabase = createServerClient(getPublicSupabaseUrl(), getPublicSupabaseAnonKey(), {
		cookies: {
			getAll() {
				return event.cookies.getAll();
			},
			setAll(cookiesToSet, headers) {
				cookiesToSet.forEach(({ name, value, options }) => {
					event.cookies.set(name, value, { ...options, path: '/' });
				});
				if (Object.keys(headers).length > 0) {
					event.setHeaders(headers);
				}
			}
		}
	});

	await event.locals.supabase.auth.getSession();

	return resolve(event, {
		filterSerializedResponseHeaders(name) {
			return name === 'content-range' || name === 'x-supabase-api-version';
		}
	});
};
