import type { Session, User } from '@supabase/supabase-js';
import { browser } from '$app/environment';
import { getPublicApiUrl } from '$lib/env/public';
import { supabase } from '$lib/supabase';
import { SvelteSet } from 'svelte/reactivity';

let session = $state<Session | null>(null);
let ready = $state(false);
let started = false;
const readyWaiters = new SvelteSet<() => void>();

function isInvalidRefreshTokenError(error: { message?: string } | null): boolean {
	if (!error?.message) return false;
	const normalizedMessage = error.message.toLowerCase();
	return (
		normalizedMessage.includes('invalid refresh token') ||
		normalizedMessage.includes('refresh token not found') ||
		normalizedMessage.includes('missing refresh token')
	);
}

function markReady(nextSession: Session | null): void {
	session = nextSession;
	ready = true;
	for (const notify of readyWaiters) {
		notify();
	}
	readyWaiters.clear();
}

export function initAuthClient(): void {
	if (!browser || started) return;
	started = true;
	void supabase.auth.getSession().then(async ({ data, error }) => {
		if (isInvalidRefreshTokenError(error)) {
			try {
				await supabase.auth.signOut({ scope: 'local' });
			} catch {
				// best-effort cleanup for stale local auth state
			}
			markReady(null);
			return;
		}
		markReady(data.session);
	});
	supabase.auth.onAuthStateChange((_event, newSession) => {
		markReady(newSession);
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

export async function waitForAuthReady(timeoutMs = 3000): Promise<void> {
	if (!browser || ready) return;
	await new Promise<void>((resolve) => {
		let settled = false;
		const finish = () => {
			if (settled) return;
			settled = true;
			resolve();
		};
		let timer: ReturnType<typeof setTimeout> | null = null;
		const waiter = () => {
			if (timer) {
				clearTimeout(timer);
			}
			readyWaiters.delete(waiter);
			finish();
		};
		timer = setTimeout(() => {
			readyWaiters.delete(waiter);
			finish();
		}, timeoutMs);
		readyWaiters.add(waiter);
	});
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
