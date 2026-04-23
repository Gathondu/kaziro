import type { Session, User } from '@supabase/supabase-js';
import { browser } from '$app/environment';
import { getPublicApiUrl } from '$lib/env/public';
import { supabase } from '$lib/supabase';

let session = $state<Session | null>(null);
let ready = $state(false);
let started = false;

export function initAuthClient(): void {
	if (!browser || started) return;
	started = true;
	void supabase.auth.getSession().then(({ data }) => {
		session = data.session;
		ready = true;
	});
	supabase.auth.onAuthStateChange((_event, newSession) => {
		session = newSession;
		ready = true;
	});
}

export function getSession(): Session | null {
	return session;
}

export function getUser(): User | null {
	return session?.user ?? null;
}

export function getJwt(): string | undefined {
	return session?.access_token;
}

export function isAuthReady(): boolean {
	return ready;
}

export async function signOutEverywhere(): Promise<void> {
	const token = getJwt();
	if (token) {
		try {
			const base = getPublicApiUrl();
			await fetch(`${base}/auth/logout`, {
				method: 'POST',
				headers: { Authorization: `Bearer ${token}` }
			});
		} catch {
			// best-effort revoke
		}
	}
	await supabase.auth.signOut();
	session = null;
}
