import { browser } from '$app/environment';

export type Appearance = 'light' | 'dark' | 'system';

/** Keep server/client appearance cookie usage in sync (same key). */
export const APPEARANCE_COOKIE_KEY = 'appearance';

const COOKIE_KEY = APPEARANCE_COOKIE_KEY;

export const appearance = $state<{ value: Appearance }>({ value: 'system' });

let mediaCleanup: (() => void) | null = null;
let started = false;

function isAppearance(value: string | null | undefined): value is Appearance {
	return value === 'light' || value === 'dark' || value === 'system';
}

export function readAppearanceCookie(): Appearance | null {
	if (!browser) return null;
	const cookiePrefix = `${COOKIE_KEY}=`;
	const cookies = document.cookie ? document.cookie.split(';') : [];
	for (const cookie of cookies) {
		const entry = cookie.trim();
		if (!entry.startsWith(cookiePrefix)) continue;
		const encodedValue = entry.slice(cookiePrefix.length);
		try {
			const decoded = decodeURIComponent(encodedValue);
			return isAppearance(decoded) ? decoded : null;
		} catch {
			return null;
		}
	}
	return null;
}

export function writeAppearanceCookie(value: Appearance): void {
	if (!browser) return;
	document.cookie = `${COOKIE_KEY}=${encodeURIComponent(value)}; path=/; max-age=31536000; samesite=lax`;
}

function daisyThemeFor(mode: Appearance): 'terracotta' | 'terracotta_dark' {
	if (mode === 'light') return 'terracotta';
	if (mode === 'dark') return 'terracotta_dark';
	if (!browser) return 'terracotta';
	return window.matchMedia('(prefers-color-scheme: dark)').matches
		? 'terracotta_dark'
		: 'terracotta';
}

function applyDomTheme(): void {
	if (!browser) return;
	document.documentElement.setAttribute('data-theme', daisyThemeFor(appearance.value));
}

function clearMediaListener(): void {
	if (mediaCleanup) {
		mediaCleanup();
		mediaCleanup = null;
	}
}

function attachMediaListener(): void {
	if (!browser || appearance.value !== 'system') return;
	const mql = window.matchMedia('(prefers-color-scheme: dark)');
	const handler = (): void => {
		applyDomTheme();
	};
	mql.addEventListener('change', handler);
	mediaCleanup = () => {
		mql.removeEventListener('change', handler);
	};
}

export function setAppearance(next: Appearance): void {
	appearance.value = next;
	clearMediaListener();
	if (browser) {
		writeAppearanceCookie(next);
	}
	applyDomTheme();
	attachMediaListener();
}

export function initAppearance(initial?: Appearance): void {
	if (!browser || started) return;
	started = true;
	let loaded: Appearance = 'system';
	if (isAppearance(initial)) {
		loaded = initial;
	} else {
		const cookieValue = readAppearanceCookie();
		if (cookieValue !== null) {
			loaded = cookieValue;
		}
	}
	appearance.value = loaded;
	clearMediaListener();
	applyDomTheme();
	attachMediaListener();
}
