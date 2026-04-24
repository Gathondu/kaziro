import { browser } from '$app/environment';

export type Appearance = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'kaziro-appearance';

export const appearance = $state<{ value: Appearance }>({ value: 'system' });

let mediaCleanup: (() => void) | null = null;
let started = false;

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
	localStorage.setItem(STORAGE_KEY, next);
	applyDomTheme();
	attachMediaListener();
}

export function initAppearance(): void {
	if (!browser || started) return;
	started = true;
	let loaded: Appearance = 'system';
	const raw = localStorage.getItem(STORAGE_KEY);
	if (raw === 'light' || raw === 'dark' || raw === 'system') {
		loaded = raw;
	}
	appearance.value = loaded;
	clearMediaListener();
	applyDomTheme();
	attachMediaListener();
}
